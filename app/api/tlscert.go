package main

import (
	"crypto/rand"
	"crypto/rsa"
	"crypto/x509"
	"crypto/x509/pkix"
	"encoding/pem"
	"fmt"
	"math/big"
	"net"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

// TLSPaths gom toàn bộ đường dẫn khoá và chứng chỉ dùng cho chế độ HTTPS cục bộ.
type TLSPaths struct {
	Dir        string
	CACert     string
	CAKey      string
	ServerCert string
	ServerKey  string
}

// defaultTLSPaths đặt khoá riêng ngoài repo để không bao giờ bị commit lên Git.
func defaultTLSPaths() TLSPaths {
	base := os.Getenv("ENGLISH_TLS_DIR")
	if base == "" {
		home, err := os.UserHomeDir()
		if err != nil || home == "" {
			home = "."
		}
		base = filepath.Join(home, ".local", "share", "english-tls")
	}
	return TLSPaths{
		Dir:        base,
		CACert:     filepath.Join(base, "ca.crt"),
		CAKey:      filepath.Join(base, "ca.key"),
		ServerCert: filepath.Join(base, "server.crt"),
		ServerKey:  filepath.Join(base, "server.key"),
	}
}

func fileExists(path string) bool {
	st, err := os.Stat(path)
	return err == nil && !st.IsDir()
}

// collectCertHosts dựng danh sách SAN: tên máy do người dùng chỉ định cộng với
// mọi địa chỉ IP đang hoạt động (gồm cả IP Tailscale 100.x và IP LAN).
func collectCertHosts(extra string) ([]string, []net.IP) {
	dnsSet := map[string]bool{"localhost": true}

	if hn, err := os.Hostname(); err == nil && hn != "" {
		dnsSet[hn] = true
	}
	for _, name := range strings.Split(extra, ",") {
		name = strings.TrimSpace(name)
		if name == "" {
			continue
		}
		dnsSet[name] = true
		if !strings.Contains(name, ".") {
			dnsSet[name+".local"] = true
		}
	}

	dnsNames := make([]string, 0, len(dnsSet))
	for name := range dnsSet {
		dnsNames = append(dnsNames, name)
	}
	sort.Strings(dnsNames)

	ips := []net.IP{net.ParseIP("127.0.0.1"), net.ParseIP("::1")}
	seen := map[string]bool{"127.0.0.1": true, "::1": true}

	if addrs, err := net.InterfaceAddrs(); err == nil {
		for _, addr := range addrs {
			ipNet, ok := addr.(*net.IPNet)
			if !ok || ipNet.IP == nil || ipNet.IP.IsLoopback() || ipNet.IP.IsLinkLocalUnicast() {
				continue
			}
			key := ipNet.IP.String()
			if seen[key] {
				continue
			}
			seen[key] = true
			ips = append(ips, ipNet.IP)
		}
	}

	return dnsNames, ips
}

func writePEM(path string, blockType string, der []byte, perm os.FileMode) error {
	buf := pem.EncodeToMemory(&pem.Block{Type: blockType, Bytes: der})
	if buf == nil {
		return fmt.Errorf("không mã hoá được PEM cho %s", path)
	}
	return os.WriteFile(path, buf, perm)
}

func randomSerial() (*big.Int, error) {
	limit := new(big.Int).Lsh(big.NewInt(1), 128)
	return rand.Int(rand.Reader, limit)
}

// loadOrCreateCA tái sử dụng CA cũ khi đã có, vì cài lại CA trên Android là
// bước thủ công tốn công nhất; chỉ cấp lại cert server là đủ khi IP thay đổi.
func loadOrCreateCA(p TLSPaths, force bool) (*x509.Certificate, *rsa.PrivateKey, bool, error) {
	if !force && fileExists(p.CACert) && fileExists(p.CAKey) {
		certPEM, err := os.ReadFile(p.CACert)
		if err != nil {
			return nil, nil, false, err
		}
		keyPEM, err := os.ReadFile(p.CAKey)
		if err != nil {
			return nil, nil, false, err
		}
		certBlock, _ := pem.Decode(certPEM)
		keyBlock, _ := pem.Decode(keyPEM)
		if certBlock == nil || keyBlock == nil {
			return nil, nil, false, fmt.Errorf("CA hiện có bị hỏng, chạy lại với --tls-force để tạo mới")
		}
		caCert, err := x509.ParseCertificate(certBlock.Bytes)
		if err != nil {
			return nil, nil, false, err
		}
		caKey, err := x509.ParsePKCS1PrivateKey(keyBlock.Bytes)
		if err != nil {
			return nil, nil, false, err
		}
		return caCert, caKey, false, nil
	}

	caKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return nil, nil, false, err
	}
	serial, err := randomSerial()
	if err != nil {
		return nil, nil, false, err
	}

	now := time.Now()
	tmpl := &x509.Certificate{
		SerialNumber: serial,
		Subject: pkix.Name{
			CommonName:   "English Tutor Local CA",
			Organization: []string{"English Tutor Local"},
		},
		NotBefore:             now.Add(-1 * time.Hour),
		NotAfter:              now.AddDate(10, 0, 0),
		IsCA:                  true,
		MaxPathLen:            0,
		MaxPathLenZero:        true,
		BasicConstraintsValid: true,
		KeyUsage:              x509.KeyUsageCertSign | x509.KeyUsageCRLSign | x509.KeyUsageDigitalSignature,
	}

	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, &caKey.PublicKey, caKey)
	if err != nil {
		return nil, nil, false, err
	}
	if err := writePEM(p.CAKey, "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(caKey), 0o600); err != nil {
		return nil, nil, false, err
	}
	if err := writePEM(p.CACert, "CERTIFICATE", der, 0o644); err != nil {
		return nil, nil, false, err
	}

	caCert, err := x509.ParseCertificate(der)
	if err != nil {
		return nil, nil, false, err
	}
	return caCert, caKey, true, nil
}

// GenerateTLSAssets tạo (hoặc làm mới) cert server ký bởi CA cục bộ.
func GenerateTLSAssets(p TLSPaths, extraHosts string, force bool) (bool, []string, []net.IP, error) {
	if err := os.MkdirAll(p.Dir, 0o700); err != nil {
		return false, nil, nil, err
	}

	caCert, caKey, caCreated, err := loadOrCreateCA(p, force)
	if err != nil {
		return false, nil, nil, err
	}

	dnsNames, ips := collectCertHosts(extraHosts)

	serverKey, err := rsa.GenerateKey(rand.Reader, 2048)
	if err != nil {
		return caCreated, nil, nil, err
	}
	serial, err := randomSerial()
	if err != nil {
		return caCreated, nil, nil, err
	}

	now := time.Now()
	tmpl := &x509.Certificate{
		SerialNumber: serial,
		Subject: pkix.Name{
			CommonName:   "English Tutor Local Server",
			Organization: []string{"English Tutor Local"},
		},
		NotBefore: now.Add(-1 * time.Hour),
		// Giữ dưới 398 ngày để Chrome không từ chối vì cert quá hạn dài.
		NotAfter:              now.AddDate(0, 0, 365),
		KeyUsage:              x509.KeyUsageDigitalSignature | x509.KeyUsageKeyEncipherment,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth},
		BasicConstraintsValid: true,
		DNSNames:              dnsNames,
		IPAddresses:           ips,
	}

	der, err := x509.CreateCertificate(rand.Reader, tmpl, caCert, &serverKey.PublicKey, caKey)
	if err != nil {
		return caCreated, nil, nil, err
	}
	if err := writePEM(p.ServerKey, "RSA PRIVATE KEY", x509.MarshalPKCS1PrivateKey(serverKey), 0o600); err != nil {
		return caCreated, nil, nil, err
	}
	if err := writePEM(p.ServerCert, "CERTIFICATE", der, 0o644); err != nil {
		return caCreated, nil, nil, err
	}

	return caCreated, dnsNames, ips, nil
}

// ExportCACert sao CA sang thư mục mà trình cài chứng chỉ của Android đọc được.
func ExportCACert(p TLSPaths) string {
	data, err := os.ReadFile(p.CACert)
	if err != nil {
		return ""
	}

	candidates := []string{}
	if home, err := os.UserHomeDir(); err == nil && home != "" {
		candidates = append(candidates, filepath.Join(home, "storage", "downloads"))
	}
	candidates = append(candidates,
		"/sdcard/Download",
		"/storage/emulated/0/Download",
	)

	for _, dir := range candidates {
		if st, err := os.Stat(dir); err != nil || !st.IsDir() {
			continue
		}
		dest := filepath.Join(dir, "english-ca.crt")
		if err := os.WriteFile(dest, data, 0o644); err == nil {
			return dest
		}
	}
	return ""
}

// PrintTLSSetupGuide in hướng dẫn cài CA, chỉ gồm các bước người dùng phải tự làm.
func PrintTLSSetupGuide(p TLSPaths, exported string, dnsNames []string, ips []net.IP, port int) {
	ipStrings := make([]string, 0, len(ips))
	for _, ip := range ips {
		ipStrings = append(ipStrings, ip.String())
	}

	fmt.Printf("\n=======================================================\n")
	fmt.Printf("  Chứng chỉ HTTPS cục bộ đã sẵn sàng\n")
	fmt.Printf("=======================================================\n")
	fmt.Printf("[*] Thư mục khoá:  %s\n", p.Dir)
	fmt.Printf("[*] CA cần cài:    %s\n", p.CACert)
	if exported != "" {
		fmt.Printf("[OK] Đã sao CA ra:  %s\n", exported)
	} else {
		fmt.Printf("[~] Chưa sao được CA ra thư mục Download. Chạy termux-setup-storage rồi tạo lại,\n")
		fmt.Printf("    hoặc tự copy file CA ở trên vào /sdcard/Download.\n")
	}
	fmt.Printf("[*] Tên hợp lệ:    %s\n", strings.Join(dnsNames, ", "))
	fmt.Printf("[*] IP hợp lệ:     %s\n", strings.Join(ipStrings, ", "))
	fmt.Printf("\nCài CA trên Android (làm một lần):\n")
	fmt.Printf("  1. Đặt khoá màn hình (PIN/mật khẩu) nếu chưa có - Android bắt buộc.\n")
	fmt.Printf("  2. Cài đặt -> Bảo mật -> Thông tin xác thực -> Cài chứng chỉ -> Chứng chỉ CA.\n")
	fmt.Printf("  3. Bấm 'Vẫn cài đặt', chọn file english-ca.crt trong Download.\n")
	fmt.Printf("  4. Mở https://<tên máy>:%d và tải lại trang.\n\n", port)
}
