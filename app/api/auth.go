package main

import (
	"crypto/rand"
	"encoding/base64"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

type AccountInfo struct {
	Email    string `json:"email"`
	IsActive bool   `json:"is_active"`
}

var accountsMu sync.Mutex

var (
	userSessionsMu  sync.RWMutex
	userSessionsMap = make(map[string]string) // token -> username
)

func generateSessionToken() string {
	b := make([]byte, 24)
	if _, err := rand.Read(b); err != nil {
		return fmt.Sprintf("sess_%d", time.Now().UnixNano())
	}
	return hex.EncodeToString(b)
}

// InitSessions nạp các phiên đăng nhập hợp lệ từ USERS/<username>/profile.json vào bộ nhớ
func (s *ServerApp) InitSessions() {
	userSessionsMu.Lock()
	defer userSessionsMu.Unlock()

	usersDir := filepath.Join(s.Vault.RootDir, "USERS")
	entries, err := os.ReadDir(usersDir)
	if err != nil {
		return
	}
	now := time.Now().UTC()
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		pPath := filepath.Join(usersDir, e.Name(), "profile.json")
		data, err := os.ReadFile(pPath)
		if err != nil {
			continue
		}
		var p UserProfile
		if err := json.Unmarshal(data, &p); err != nil {
			continue
		}
		for _, sess := range p.Sessions {
			exp, err := time.Parse(time.RFC3339, sess.ExpiresAt)
			if err == nil && exp.After(now) {
				userSessionsMap[sess.Token] = p.Username
			}
		}
	}
}

// GetUserFromToken tìm username từ session token
func (s *ServerApp) GetUserFromToken(token string) string {
	if token == "" {
		return ""
	}
	userSessionsMu.RLock()
	username, ok := userSessionsMap[token]
	userSessionsMu.RUnlock()
	if ok && username != "" {
		return username
	}
	return ""
}

// GetTokenFromRequest lấy session token từ Authorization header, cookie hoặc query param
func (s *ServerApp) GetTokenFromRequest(r *http.Request) string {
	authHeader := r.Header.Get("Authorization")
	if strings.HasPrefix(authHeader, "Bearer ") {
		return strings.TrimPrefix(authHeader, "Bearer ")
	}
	if cookie, err := r.Cookie("english_session"); err == nil && cookie.Value != "" {
		return cookie.Value
	}
	return r.URL.Query().Get("token")
}

// GetUserProfile đọc hồ sơ của người dùng từ USERS/<username>/profile.json
func (s *ServerApp) GetUserProfile(username string) (*UserProfile, error) {
	username = strings.ToLower(strings.TrimSpace(username))
	if !validUserRegex.MatchString(username) {
		return nil, fmt.Errorf("tên người dùng không hợp lệ")
	}
	pPath := filepath.Join(s.Vault.RootDir, "USERS", username, "profile.json")
	data, err := os.ReadFile(pPath)
	if err != nil {
		return nil, err
	}
	var prof UserProfile
	if err := json.Unmarshal(data, &prof); err != nil {
		return nil, err
	}
	return &prof, nil
}

// SaveUserProfile lưu hồ sơ người dùng vào USERS/<username>/profile.json
func (s *ServerApp) SaveUserProfile(prof *UserProfile) error {
	if prof == nil || prof.Username == "" {
		return fmt.Errorf("hồ sơ người dùng rỗng")
	}
	userDir := filepath.Join(s.Vault.RootDir, "USERS", prof.Username)
	if err := os.MkdirAll(userDir, 0755); err != nil {
		return err
	}
	prof.UpdatedAt = time.Now().UTC().Format(time.RFC3339)
	data, err := json.MarshalIndent(prof, "", "  ")
	if err != nil {
		return err
	}
	pPath := filepath.Join(userDir, "profile.json")
	return os.WriteFile(pPath, data, 0644)
}

// handleAuthLogin xử lý đăng nhập bằng tài khoản và mật khẩu
func (s *ServerApp) handleAuthLogin(w http.ResponseWriter, r *http.Request) {
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

	var req struct {
		Username string `json:"username"`
		Password string `json:"password"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Dữ liệu JSON không hợp lệ")
		return
	}

	username := strings.ToLower(strings.TrimSpace(req.Username))
	password := strings.TrimSpace(req.Password)

	prof, err := s.GetUserProfile(username)
	if err != nil {
		sendError(w, http.StatusUnauthorized, "Tài khoản hoặc mật khẩu không chính xác")
		return
	}

	expectedPass := prof.Password
	if expectedPass == "" {
		if username == "qtu" {
			expectedPass = "111"
		} else if username == "gty" {
			expectedPass = "777"
		}
	}

	if password != expectedPass {
		sendError(w, http.StatusUnauthorized, "Mật khẩu không chính xác")
		return
	}

	token := generateSessionToken()
	now := time.Now().UTC()
	expiresAt := now.Add(30 * 24 * time.Hour).Format(time.RFC3339)

	sess := UserSession{
		Token:     token,
		CreatedAt: now.Format(time.RFC3339),
		ExpiresAt: expiresAt,
	}

	if len(prof.Sessions) >= 10 {
		prof.Sessions = prof.Sessions[len(prof.Sessions)-9:]
	}
	prof.Sessions = append(prof.Sessions, sess)
	_ = s.SaveUserProfile(prof)

	userSessionsMu.Lock()
	userSessionsMap[token] = prof.Username
	userSessionsMu.Unlock()

	http.SetCookie(w, &http.Cookie{
		Name:     "english_session",
		Value:    token,
		Path:     "/",
		MaxAge:   30 * 24 * 3600,
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})

	safeProf := *prof
	safeProf.Password = ""
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"token":   token,
		"user":    safeProf,
	})
}

// handleAuthSocialLogin xử lý đăng nhập bằng Google hoặc Facebook
func (s *ServerApp) handleAuthSocialLogin(w http.ResponseWriter, r *http.Request) {
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

	var req struct {
		Provider   string `json:"provider"` // "google", "facebook"
		Credential string `json:"credential"` // ID Token
		Email      string `json:"email"`
		Name       string `json:"name"`
		ID         string `json:"id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendError(w, http.StatusBadRequest, "Dữ liệu JSON không hợp lệ")
		return
	}

	email := strings.ToLower(strings.TrimSpace(req.Email))
	name := strings.TrimSpace(req.Name)
	if email == "" && req.Credential != "" {
		parts := strings.Split(req.Credential, ".")
		if len(parts) >= 2 {
			payloadBytes, err := base64.RawURLEncoding.DecodeString(parts[1])
			if err == nil {
				var claims struct {
					Email string `json:"email"`
					Name  string `json:"name"`
					Sub   string `json:"sub"`
				}
				if json.Unmarshal(payloadBytes, &claims) == nil {
					if claims.Email != "" {
						email = strings.ToLower(claims.Email)
					}
					if claims.Name != "" && name == "" {
						name = claims.Name
					}
					if req.ID == "" {
						req.ID = claims.Sub
					}
				}
			}
		}
	}

	if email == "" {
		sendError(w, http.StatusBadRequest, "Không lấy được email từ tài khoản mạng xã hội.")
		return
	}

	targetUsername := ""
	if strings.HasPrefix(email, "qtu") || email == "qtu@gmail.com" {
		targetUsername = "qtu"
	} else {
		prefix := strings.Split(email, "@")[0]
		prefix = strings.ToLower(prefix)
		reg := regexp.MustCompile(`[^a-z0-9_-]`)
		targetUsername = reg.ReplaceAllString(prefix, "")
		if targetUsername == "" {
			targetUsername = "user_" + fmt.Sprintf("%d", time.Now().Unix()%10000)
		}
	}

	prof, err := s.GetUserProfile(targetUsername)
	if err != nil {
		role := "user"
		f := false
		if targetUsername == "qtu" {
			role = "admin"
			t := true
			prof = &UserProfile{
				Username:      targetUsername,
				DisplayName:   name,
				Email:         email,
				Role:          role,
				CanViewAIInfo: &t,
				AvatarUser:    "🧑‍🎓",
				AvatarAI:      "🤖",
				AvatarTarget:  "🎯",
				AIEngine:      "antigravity",
				GeminiModel:   "gemini-3.6-flash",
				TTSRate:       0.9,
			}
		} else {
			prof = &UserProfile{
				Username:      targetUsername,
				DisplayName:   name,
				Email:         email,
				Role:          role,
				CanViewAIInfo: &f,
				AvatarUser:    "🧑‍🎓",
				AvatarAI:      "🤖",
				AvatarTarget:  "🎯",
				AIEngine:      "antigravity",
				GeminiModel:   "gemini-3.6-flash",
				TTSRate:       0.9,
			}
		}
	}

	if prof.DisplayName == "" && name != "" {
		prof.DisplayName = name
	}
	if prof.Email == "" {
		prof.Email = email
	}

	token := generateSessionToken()
	now := time.Now().UTC()
	expiresAt := now.Add(30 * 24 * time.Hour).Format(time.RFC3339)

	sess := UserSession{
		Token:     token,
		CreatedAt: now.Format(time.RFC3339),
		ExpiresAt: expiresAt,
	}

	if len(prof.Sessions) >= 10 {
		prof.Sessions = prof.Sessions[len(prof.Sessions)-9:]
	}
	prof.Sessions = append(prof.Sessions, sess)
	_ = s.SaveUserProfile(prof)

	userSessionsMu.Lock()
	userSessionsMap[token] = prof.Username
	userSessionsMu.Unlock()

	http.SetCookie(w, &http.Cookie{
		Name:     "english_session",
		Value:    token,
		Path:     "/",
		MaxAge:   30 * 24 * 3600,
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})

	safeProf := *prof
	safeProf.Password = ""
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
		"token":   token,
		"user":    safeProf,
	})
}

// handleAuthMe kiểm tra phiên đăng nhập hiện tại
func (s *ServerApp) handleAuthMe(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	token := s.GetTokenFromRequest(r)
	username := s.GetUserFromToken(token)
	if username == "" {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"logged_in": false,
		})
		return
	}

	prof, err := s.GetUserProfile(username)
	if err != nil {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"logged_in": false,
		})
		return
	}

	safeProf := *prof
	safeProf.Password = ""
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"logged_in": true,
		"user":      safeProf,
	})
}

// handleAuthLogout xử lý đăng xuất
func (s *ServerApp) handleAuthLogout(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	token := s.GetTokenFromRequest(r)
	if token != "" {
		userSessionsMu.Lock()
		username := userSessionsMap[token]
		delete(userSessionsMap, token)
		userSessionsMu.Unlock()

		if username != "" {
			if prof, err := s.GetUserProfile(username); err == nil {
				var remaining []UserSession
				for _, sess := range prof.Sessions {
					if sess.Token != token {
						remaining = append(remaining, sess)
					}
				}
				prof.Sessions = remaining
				_ = s.SaveUserProfile(prof)
			}
		}
	}

	http.SetCookie(w, &http.Cookie{
		Name:     "english_session",
		Value:    "",
		Path:     "/",
		MaxAge:   -1,
		HttpOnly: true,
		SameSite: http.SameSiteLaxMode,
	})

	sendJSON(w, http.StatusOK, map[string]interface{}{
		"success": true,
	})
}

// handleOAuthConfig trả về client ID công khai của Google và Facebook
func (s *ServerApp) handleOAuthConfig(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	cfgPath := filepath.Join(s.Vault.RootDir, "app", "data", "oauth_config.json")
	googleID := os.Getenv("GOOGLE_CLIENT_ID")
	facebookID := os.Getenv("FACEBOOK_APP_ID")

	if data, err := os.ReadFile(cfgPath); err == nil {
		var cfg struct {
			GoogleClientID string `json:"google_client_id"`
			FacebookAppID  string `json:"facebook_app_id"`
		}
		if json.Unmarshal(data, &cfg) == nil {
			if cfg.GoogleClientID != "" {
				googleID = cfg.GoogleClientID
			}
			if cfg.FacebookAppID != "" {
				facebookID = cfg.FacebookAppID
			}
		}
	}

	sendJSON(w, http.StatusOK, map[string]interface{}{
		"google_client_id": googleID,
		"facebook_app_id":  facebookID,
	})
}

// --- Antigravity CLI Account Management ---

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
