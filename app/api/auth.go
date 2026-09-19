package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"time"
)

type AccountInfo struct {
	Email    string `json:"email"`
	IsActive bool   `json:"is_active"`
}

var accountsMu sync.Mutex

// GetAccountsDir returns the directory used to store saved Google account tokens
func GetAccountsDir() (string, error) {
	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}
	dir := filepath.Join(home, ".gemini", "antigravity-cli", "accounts")
	if err := os.MkdirAll(dir, 0700); err != nil {
		return "", err
	}
	return dir, nil
}

// SyncCurrentAccount saves the currently active token into the accounts/ directory
func SyncCurrentAccount() string {
	accountsMu.Lock()
	defer accountsMu.Unlock()

	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	activeTokenPath := filepath.Join(home, ".gemini", "antigravity-cli", "antigravity-oauth-token")
	data, err := os.ReadFile(activeTokenPath)
	if err != nil || len(data) == 0 {
		return ""
	}

	email := ExtractAgyEmail()
	if email == "" {
		return ""
	}

	accDir, err := GetAccountsDir()
	if err != nil {
		return email
	}

	savePath := filepath.Join(accDir, email+".json")
	_ = os.WriteFile(savePath, data, 0600)
	return email
}

// ListSavedAccounts returns all saved accounts and marks the active one
func ListSavedAccounts() ([]AccountInfo, string) {
	accountsMu.Lock()
	defer accountsMu.Unlock()

	activeEmail := ExtractAgyEmail()
	accDir, err := GetAccountsDir()
	if err != nil {
		if activeEmail != "" {
			return []AccountInfo{{Email: activeEmail, IsActive: true}}, activeEmail
		}
		return []AccountInfo{}, ""
	}

	entries, err := os.ReadDir(accDir)
	if err != nil {
		if activeEmail != "" {
			return []AccountInfo{{Email: activeEmail, IsActive: true}}, activeEmail
		}
		return []AccountInfo{}, ""
	}

	var list []AccountInfo
	foundActive := false

	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".json") {
			continue
		}
		email := strings.TrimSuffix(e.Name(), ".json")
		isActive := (email == activeEmail)
		if isActive {
			foundActive = true
		}
		list = append(list, AccountInfo{
			Email:    email,
			IsActive: isActive,
		})
	}

	// If active token exists but wasn't in accounts yet, add it
	if activeEmail != "" && !foundActive {
		list = append([]AccountInfo{{Email: activeEmail, IsActive: true}}, list...)
	}

	return list, activeEmail
}

// SwitchAccount replaces the active token with the target account's saved token
func SwitchAccount(targetEmail string) error {
	accountsMu.Lock()
	defer accountsMu.Unlock()

	targetEmail = strings.TrimSpace(targetEmail)
	if targetEmail == "" {
		return fmt.Errorf("email không được để trống")
	}

	accDir, err := GetAccountsDir()
	if err != nil {
		return err
	}

	targetPath := filepath.Join(accDir, targetEmail+".json")
	data, err := os.ReadFile(targetPath)
	if err != nil {
		return fmt.Errorf("không tìm thấy token đã lưu cho tài khoản %s", targetEmail)
	}

	home, err := os.UserHomeDir()
	if err != nil {
		return err
	}

	activeTokenPath := filepath.Join(home, ".gemini", "antigravity-cli", "antigravity-oauth-token")
	if err := os.WriteFile(activeTokenPath, data, 0600); err != nil {
		return fmt.Errorf("lỗi khi ghi token kích hoạt: %w", err)
	}

	// Reset quota cache to immediately reflect the new account's quotas
	quotaCacheMu.Lock()
	quotaCache = nil
	lastFetch = time.Time{}
	quotaCacheMu.Unlock()

	return nil
}

func (s *ServerApp) handleAuthAccounts(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	caller := strings.ToLower(strings.TrimSpace(r.URL.Query().Get("username")))
	if caller == "" {
		caller = "qtu"
	}
	if !s.CheckUserCanViewAIInfo(caller) {
		sendError(w, http.StatusForbidden, "Chỉ quản trị viên mới có quyền xem danh sách tài khoản.")
		return
	}

	SyncCurrentAccount()
	accounts, activeEmail := ListSavedAccounts()

	sendJSON(w, http.StatusOK, map[string]interface{}{
		"active_email": activeEmail,
		"accounts":     accounts,
	})
}

func (s *ServerApp) handleAuthSwitch(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method != "POST" {
		sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
		return
	}

	var body struct {
		Username    string `json:"username"`
		TargetEmail string `json:"target_email"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid JSON payload")
		return
	}

	caller := strings.ToLower(strings.TrimSpace(body.Username))
	if caller == "" {
		caller = "qtu"
	}
	if !s.CheckUserCanViewAIInfo(caller) {
		sendError(w, http.StatusForbidden, "Chỉ quản trị viên mới có quyền chuyển đổi tài khoản.")
		return
	}

	if err := SwitchAccount(body.TargetEmail); err != nil {
		sendError(w, http.StatusInternalServerError, err.Error())
		return
	}

	sendJSON(w, http.StatusOK, map[string]interface{}{
		"success":      true,
		"active_email": body.TargetEmail,
	})
}
