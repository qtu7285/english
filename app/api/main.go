package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strconv"
	"strings"
	"sync"
	"time"
)

const DefaultSystemPrompt = `You are an English tutor. Explain in Vietnamese, briefly, naturally, and clearly.
Use ASCII bracketed status labels: [OK], [~], [X], [NEXT], [RETRY], [SAVE], [CONFIRM], [EN], and [VI]. Do not use emojis.

Rules:
1. Explaining a word/phrase (e.g. '.urge', 'inspire'):
   - Provide meaning in Vietnamese
   - Part of speech
   - Common usage/collocations
   - A horizontal divider (---) to cleanly separate theory from practice
   - A short natural English example with Vietnamese meaning
   - End with: [NEXT] Nhập số câu để luyện (ví dụ 5), hoặc nhập từ mới để chuyển từ.

2. Explaining a sentence:
   - Natural Vietnamese meaning
   - Important grammar/structure
   - Correction if needed

3. Interactive Practice Round (CRITICAL - ONE QUESTION AT A TIME):
   When the learner enters a positive integer N (such as '3' or '5') after studying a word:
   - You MUST initiate an interactive practice round of N questions.
   - VERY IMPORTANT: Present ONLY ONE question at a time! NEVER output all questions at once.
   - For the initial turn, present ONLY "Câu 1/N":
     * Include difficulty label: [D1] (cơ bản), [D2] (trung bình), or [D3] (khó).
     * Provide a sentence with blank(s) ___ and a clear Vietnamese translation hint.
     * Provide 4 options (A, B, C, D) testing the target word and its collocations, or ask to fill in the blank.
     * Stop and wait for the learner to answer Câu 1/N.

4. Grading and Advancing Questions (ONE BY ONE):
   When the learner answers a question (e.g. typing "A", "urged", or the word):
   - Grade the answer immediately:
     * If correct: output [OK] with a brief explanation of why it fits and common collocation.
     * If incorrect: output [X], explain the mistake, and give the correct sentence.
   - If there are remaining questions in the round (e.g. Question K < N):
     * Immediately present the next single question: "Câu (K+1)/N [D2]" in the same response and wait for the answer.
     * Do NOT present more than 1 question at a time.
   - If it was the last question (Câu N/N):
     * Announce round completion: [OK] Hoàn thành N/N câu!
     * End with: [NEXT] Nhập số câu để luyện tiếp (ví dụ 5), hoặc .từ_mới để chuyển từ.

5. Commands:
   - '.s': Confirm learning progress is saved.
   - '.g': Git sync status.
   - '.help': Show available commands.

6. Pronunciation Placeholder (CRITICAL for Audio):
   Whenever presenting an English headword, phrase, example sentence, or test question, append an audio placeholder:
   [audio:Exact English text to speak]
   directly after the English text (before any Vietnamese translation in parentheses).
   Examples:
   - Headword: **urge** [audio:urge] /ɜːrdʒ/ (v): thúc giục
   - Collocation: **urge somebody to do something** [audio:urge somebody to do something]
   - Example sentence: She urged me to apply for the position. [audio:She urged me to apply for the position.] (Cô ấy đã giục tôi nộp đơn ứng tuyển.)
   - Test question with blanks:
     She _____ (urge) me to apply for the position. [audio:She urged me to apply for the position.] (Cô ấy đã giục tôi...)
   *IMPORTANT*: In test questions or sentences with blanks like '_____', the placeholder [audio:...] MUST contain the COMPLETE correct sentence (with the correct word filled in instead of blanks or underscores), so that the learner can hear the full correct pronunciation!

You have access to tools to read, search, list, and write files in the user's learning vault and vocabulary data. Use them when requested.`

type ServerApp struct {
	Vault   *VaultManager
	WebDir  string
	Port    int
	Host    string
}

// LiveReloader theo dõi thay đổi trong thư mục webDir và bắn tín hiệu SSE cho trình duyệt
type LiveReloader struct {
	webDir    string
	clients   map[chan struct{}]bool
	clientsMu sync.Mutex
}

func NewLiveReloader(webDir string) *LiveReloader {
	lr := &LiveReloader{
		webDir:  webDir,
		clients: make(map[chan struct{}]bool),
	}
	lr.startWatcher()
	return lr
}

func (lr *LiveReloader) startWatcher() {
	var lastMod time.Time
	filepath.Walk(lr.webDir, func(path string, info os.FileInfo, err error) error {
		if err == nil && !info.IsDir() {
			if info.ModTime().After(lastMod) {
				lastMod = info.ModTime()
			}
		}
		return nil
	})

	go func() {
		ticker := time.NewTicker(600 * time.Millisecond)
		defer ticker.Stop()
		for range ticker.C {
			var maxMod time.Time
			filepath.Walk(lr.webDir, func(path string, info os.FileInfo, err error) error {
				if err == nil && !info.IsDir() {
					if info.ModTime().After(maxMod) {
						maxMod = info.ModTime()
					}
				}
				return nil
			})

			if maxMod.After(lastMod) {
				lastMod = maxMod
				lr.broadcast()
			}
		}
	}()
}

func (lr *LiveReloader) broadcast() {
	lr.clientsMu.Lock()
	defer lr.clientsMu.Unlock()
	for ch := range lr.clients {
		select {
		case ch <- struct{}{}:
		default:
		}
	}
}

func (lr *LiveReloader) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	w.Header().Set("Access-Control-Allow-Origin", "*")

	flusher, ok := w.(http.Flusher)
	if !ok {
		http.Error(w, "Streaming unsupported", http.StatusInternalServerError)
		return
	}

	ch := make(chan struct{}, 1)
	lr.clientsMu.Lock()
	lr.clients[ch] = true
	lr.clientsMu.Unlock()

	defer func() {
		lr.clientsMu.Lock()
		delete(lr.clients, ch)
		lr.clientsMu.Unlock()
	}()

	fmt.Fprintf(w, "data: connected\n\n")
	flusher.Flush()

	ctx := r.Context()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ch:
			fmt.Fprintf(w, "data: reload\n\n")
			flusher.Flush()
		}
	}
}

func sendJSON(w http.ResponseWriter, status int, data interface{}) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(data)
}

func sendError(w http.ResponseWriter, status int, msg string) {
	sendJSON(w, status, map[string]string{"error": msg})
}

func (s *ServerApp) handleStatus(w http.ResponseWriter, r *http.Request) {
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"status":                "ok",
		"engine":                "golang",
		"antigravity_available": IsAgyAvailable(),
		"vault_root":            s.Vault.RootDir,
		"web_dir":               s.WebDir,
	})
}

type UserSession struct {
	Token     string `json:"token"`
	CreatedAt string `json:"created_at"`
	ExpiresAt string `json:"expires_at"`
}

type UserProfile struct {
	Username        string                 `json:"username"`
	DisplayName     string                 `json:"display_name"`
	Password        string                 `json:"password,omitempty"`
	Email           string                 `json:"email,omitempty"`
	AvatarUser      string                 `json:"avatar_user"`
	AvatarAI        string                 `json:"avatar_ai"`
	AvatarTarget    string                 `json:"avatar_target,omitempty"`
	ShowChatAvatars *bool                  `json:"show_chat_avatars,omitempty"`
	Role            string                 `json:"role,omitempty"`
	CanViewAIInfo   *bool                  `json:"can_view_ai_info,omitempty"`
	AIEngine        string                 `json:"ai_engine,omitempty"`
	GeminiModel     string                 `json:"gemini_model,omitempty"`
	TTSRate         float64                `json:"tts_rate,omitempty"`
	AuthProviders   map[string]interface{} `json:"auth_providers,omitempty"`
	Sessions        []UserSession          `json:"sessions,omitempty"`
	UpdatedAt       string                 `json:"updated_at,omitempty"`
}

var validUserRegex = regexp.MustCompile(`^[a-z0-9][a-z0-9_-]*$`)

// CheckUserIsAdmin kiểm tra xem user có quyền quản trị hay không
func (s *ServerApp) CheckUserIsAdmin(username string) bool {
	username = strings.ToLower(strings.TrimSpace(username))
	if username == "" || username == "qtu" {
		return true
	}
	prof, err := s.GetUserProfile(username)
	if err != nil {
		return false
	}
	return prof.Role == "admin"
}

// CheckUserCanViewAIInfo checks if a username has permission to view AI quota and email
func (s *ServerApp) CheckUserCanViewAIInfo(username string) bool {
	username = strings.ToLower(strings.TrimSpace(username))
	if username == "" || username == "qtu" {
		return true
	}
	userDir := filepath.Join(s.Vault.RootDir, "USERS", username)
	profilePath := filepath.Join(userDir, "profile.json")
	data, err := os.ReadFile(profilePath)
	if err != nil {
		return false
	}
	var prof UserProfile
	if err := json.Unmarshal(data, &prof); err != nil {
		return false
	}
	if prof.Role == "admin" {
		return true
	}
	if prof.CanViewAIInfo != nil && *prof.CanViewAIInfo {
		return true
	}
	return false
}

func (s *ServerApp) handleUserProfile(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	if r.Method == "GET" {
		username := strings.ToLower(strings.TrimSpace(r.URL.Query().Get("username")))
		if username == "" {
			username = "qtu"
		}
		if !validUserRegex.MatchString(username) {
			sendError(w, http.StatusBadRequest, "Invalid username format. Must match ^[a-z0-9][a-z0-9_-]*$")
			return
		}

		userDir := filepath.Join(s.Vault.RootDir, "USERS", username)
		profilePath := filepath.Join(userDir, "profile.json")

		data, err := os.ReadFile(profilePath)
		if err != nil {
			f := false
			t := true
			role := "learner"
			canView := &f
			if username == "qtu" {
				role = "admin"
				canView = &t
			}
			defaultProf := UserProfile{
				Username:        username,
				DisplayName:     username,
				AvatarUser:      "🧑‍🎓",
				AvatarAI:        "🤖",
				AvatarTarget:    "🎯",
				ShowChatAvatars: &f,
				Role:            role,
				CanViewAIInfo:   canView,
				AIEngine:        "antigravity",
				GeminiModel:     "gemini-3.6-flash",
				TTSRate:         0.9,
				UpdatedAt:       time.Now().UTC().Format(time.RFC3339),
			}
			sendJSON(w, http.StatusOK, defaultProf)
			return
		}

		var prof UserProfile
		if err := json.Unmarshal(data, &prof); err != nil {
			sendError(w, http.StatusInternalServerError, "Malformed profile.json: "+err.Error())
			return
		}
		if prof.AvatarTarget == "" {
			prof.AvatarTarget = "🎯"
		}
		if prof.Username == "qtu" {
			prof.Role = "admin"
			t := true
			prof.CanViewAIInfo = &t
		} else {
			if prof.Role == "" {
				prof.Role = "learner"
			}
			if prof.CanViewAIInfo == nil {
				f := false
				prof.CanViewAIInfo = &f
			}
		}
		safeProf := prof
		safeProf.Password = ""
		sendJSON(w, http.StatusOK, safeProf)
		return
	}

	if r.Method == "POST" {
		var prof UserProfile
		if err := json.NewDecoder(r.Body).Decode(&prof); err != nil {
			sendError(w, http.StatusBadRequest, "Invalid JSON payload: "+err.Error())
			return
		}

		prof.Username = strings.ToLower(strings.TrimSpace(prof.Username))
		if prof.Username == "" {
			prof.Username = "qtu"
		}
		if !validUserRegex.MatchString(prof.Username) {
			sendError(w, http.StatusBadRequest, "Invalid username format. Must match ^[a-z0-9][a-z0-9_-]*$")
			return
		}

		if prof.DisplayName == "" {
			prof.DisplayName = prof.Username
		}
		if prof.AvatarUser == "" {
			prof.AvatarUser = "🧑‍🎓"
		}
		if prof.AvatarAI == "" {
			prof.AvatarAI = "🤖"
		}
		if prof.AvatarTarget == "" {
			prof.AvatarTarget = "🎯"
		}
		if prof.TTSRate == 0 {
			prof.TTSRate = 0.9
		}
		if prof.Username == "qtu" {
			prof.Role = "admin"
			t := true
			prof.CanViewAIInfo = &t
		}
		prof.UpdatedAt = time.Now().UTC().Format(time.RFC3339)

		userDir := filepath.Join(s.Vault.RootDir, "USERS", prof.Username)
		if err := os.MkdirAll(userDir, 0755); err != nil {
			sendError(w, http.StatusInternalServerError, "Failed to create user directory: "+err.Error())
			return
		}

		profilePath := filepath.Join(userDir, "profile.json")
		if existingData, err := os.ReadFile(profilePath); err == nil {
			var existingProf UserProfile
			if json.Unmarshal(existingData, &existingProf) == nil {
				if prof.Password == "" {
					prof.Password = existingProf.Password
				}
				if prof.Sessions == nil {
					prof.Sessions = existingProf.Sessions
				}
				if prof.AuthProviders == nil {
					prof.AuthProviders = existingProf.AuthProviders
				}
			}
		}

		data, err := json.MarshalIndent(prof, "", "  ")
		if err != nil {
			sendError(w, http.StatusInternalServerError, "Failed to serialize profile: "+err.Error())
			return
		}

		if err := os.WriteFile(profilePath, data, 0644); err != nil {
			sendError(w, http.StatusInternalServerError, "Failed to write profile.json: "+err.Error())
			return
		}

		safeProf := prof
		safeProf.Password = ""
		sendJSON(w, http.StatusOK, safeProf)
		return
	}

	sendError(w, http.StatusMethodNotAllowed, "Method not allowed")
}

func (s *ServerApp) handleUsersList(w http.ResponseWriter, r *http.Request) {
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
		sendError(w, http.StatusForbidden, "Chỉ quản trị viên mới có quyền xem danh sách người học.")
		return
	}

	usersDir := filepath.Join(s.Vault.RootDir, "USERS")
	entries, err := os.ReadDir(usersDir)
	if err != nil {
		sendError(w, http.StatusInternalServerError, "Không thể đọc thư mục USERS: "+err.Error())
		return
	}

	var users []UserProfile
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		uName := strings.ToLower(e.Name())
		pPath := filepath.Join(usersDir, uName, "profile.json")
		data, err := os.ReadFile(pPath)
		if err != nil {
			continue
		}
		var p UserProfile
		if err := json.Unmarshal(data, &p); err == nil {
			users = append(users, p)
		}
	}

	sendJSON(w, http.StatusOK, map[string]interface{}{
		"users": users,
	})
}

func (s *ServerApp) handleVaultList(w http.ResponseWriter, r *http.Request) {
	subpath := r.URL.Query().Get("subpath")
	files, err := s.Vault.ListFiles(subpath, 3)
	if err != nil {
		sendError(w, http.StatusInternalServerError, err.Error())
		return
	}
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"files":      files,
		"vault_root": s.Vault.RootDir,
	})
}

func (s *ServerApp) handleVaultRead(w http.ResponseWriter, r *http.Request) {
	filePath := r.URL.Query().Get("path")
	if filePath == "" {
		sendError(w, http.StatusBadRequest, "Parameter 'path' is required.")
		return
	}
	res := s.Vault.ReadFile(filePath, 100000)
	if res.Error != "" {
		sendError(w, http.StatusNotFound, res.Error)
		return
	}
	sendJSON(w, http.StatusOK, res)
}

func (s *ServerApp) handleVaultWrite(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Path    string `json:"path"`
		Content string `json:"content"`
		Append  bool   `json:"append"`
	}
	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}
	if body.Path == "" {
		sendError(w, http.StatusBadRequest, "Parameter 'path' is required.")
		return
	}
	res := s.Vault.WriteFile(body.Path, body.Content, body.Append)
	if !res.Success {
		sendError(w, http.StatusInternalServerError, res.Error)
		return
	}
	sendJSON(w, http.StatusOK, res)
}

func (s *ServerApp) handleVaultSearch(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query().Get("q")
	if q == "" {
		sendError(w, http.StatusBadRequest, "Parameter 'q' is required.")
		return
	}
	matches := s.Vault.SearchVault(q, 15)
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"matches": matches,
		"query":   q,
	})
}

var (
	reAudioPlaceholder = regexp.MustCompile(`(?i)\[(?:audio|speak|play|sound|🔊):\s*([^\]]+)\]`)
	reVietnameseChars   = regexp.MustCompile(`[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]`)
	reQuotedSentence    = regexp.MustCompile(`["“]([A-Za-z0-9\s,.'’!?\-_]{5,})["”]`)
	reHTMLTags          = regexp.MustCompile(`<[^>]+>`)
	reMultipleSpaces    = regexp.MustCompile(`\s+`)
)

func cleanAudioText(s string) string {
	s = strings.TrimSpace(s)
	s = reHTMLTags.ReplaceAllString(s, " ")
	s = strings.ReplaceAll(s, "&quot;", "\"")
	s = strings.ReplaceAll(s, "&#39;", "'")
	s = strings.ReplaceAll(s, "&apos;", "'")
	s = strings.ReplaceAll(s, "&amp;", "&")
	s = strings.ReplaceAll(s, "&lt;", "<")
	s = strings.ReplaceAll(s, "&gt;", ">")
	s = regexp.MustCompile(`[*#` + "`" + `"“”]`).ReplaceAllString(s, "")
	s = reMultipleSpaces.ReplaceAllString(s, " ")
	return strings.TrimSpace(s)
}

// ExtractAudioSentence bóc tách câu tiếng Anh chuẩn từ nội dung phản hồi
func ExtractAudioSentence(text string) string {
	// 1. Kiểm tra placeholder [audio:...]
	matches := reAudioPlaceholder.FindAllStringSubmatch(text, -1)
	var fallback string
	for _, m := range matches {
		if len(m) > 1 {
			clean := cleanAudioText(m[1])
			if clean != "" && !reVietnameseChars.MatchString(clean) {
				words := strings.Fields(clean)
				if len(words) > 2 {
					return clean
				}
				if fallback == "" {
					fallback = clean
				}
			}
		}
	}

	// 2. Kiểm tra câu tiếng Anh đặt trong dấu ngoặc kép
	quoteMatches := reQuotedSentence.FindAllStringSubmatch(text, -1)
	for _, q := range quoteMatches {
		if len(q) > 1 {
			clean := cleanAudioText(q[1])
			if clean != "" && !reVietnameseChars.MatchString(clean) && len(strings.Fields(clean)) >= 3 {
				return clean
			}
		}
	}

	// 3. Kiểm tra câu tiếng Anh đứng trước phần dịch tiếng Việt trong dấu ngoặc đơn
	lines := strings.Split(text, "\n")
	for _, line := range lines {
		cleanLine := cleanAudioText(line)
		parenIdx := strings.Index(cleanLine, "(")
		if parenIdx > 0 {
			left := strings.TrimSpace(cleanLine[:parenIdx])
			right := cleanLine[parenIdx:]
			if reVietnameseChars.MatchString(right) && !reVietnameseChars.MatchString(left) && len(strings.Fields(left)) >= 3 {
				return left
			}
		}
	}

	return fallback
}

func ClassifyResponse(text string, userMsg string) (string, string, string) {
	cleanMsg := strings.TrimSpace(userMsg)
	audioSent := ExtractAudioSentence(text)

	// 1. Test question: Câu 1/5, Câu 2/N, [D1], [D2], [D3] with blanks
	if (regexp.MustCompile(`(?i)Câu\s+\d+/\d+`).MatchString(text) || regexp.MustCompile(`\[D[1-3]\]`).MatchString(text) || strings.Contains(text, "___")) && !regexp.MustCompile(`(?i)Hoàn thành \d+/\d+ câu`).MatchString(text) {
		return "test_question", "", audioSent
	}

	// 2. Round completed
	if regexp.MustCompile(`(?i)Hoàn thành \d+/\d+ câu`).MatchString(text) {
		return "round_completed", "", audioSent
	}

	// 3. Word explanation: has [NEXT] Nhập số câu... or starts with headword pattern
	if regexp.MustCompile(`(?i)\[NEXT\]\s*Nhập số câu|số câu để luyện`).MatchString(text) {
		targetWord := ""
		if strings.HasPrefix(cleanMsg, ".") && len(cleanMsg) > 1 {
			targetWord = strings.TrimPrefix(cleanMsg, ".")
		}
		if targetWord == "" {
			m := regexp.MustCompile(`(?m)^\s*(?:\*\*)?([A-Za-z][A-Za-z\s\-]{1,29})(?:\*\*)?\s*(?:/|\[audio:)`).FindStringSubmatch(text)
			if len(m) > 1 {
				targetWord = strings.TrimSpace(m[1])
			}
		}
		return "word_explanation", targetWord, audioSent
	}

	// 4. Test evaluation: [OK], [X], [~]
	if regexp.MustCompile(`\[OK\]|\[X\]|\[~\]|\[RETRY\]`).MatchString(text) {
		return "test_evaluation", "", audioSent
	}

	return "chat", "", audioSent
}

func (s *ServerApp) handleChat(w http.ResponseWriter, r *http.Request) {
	if r.Method == "OPTIONS" {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		w.WriteHeader(http.StatusOK)
		return
	}

	var body struct {
		Engine            string                   `json:"engine"`
		Message           string                   `json:"message"`
		History           []map[string]interface{} `json:"history"`
		APIKey            string                   `json:"apiKey"`
		Model             string                   `json:"model"`
		SystemInstruction string                   `json:"systemInstruction"`
		EnableVaultTools  *bool                    `json:"enableVaultTools"`
		Username          string                   `json:"username"`
	}

	if err := json.NewDecoder(r.Body).Decode(&body); err != nil {
		sendError(w, http.StatusBadRequest, "Invalid JSON body")
		return
	}

	msg := strings.TrimSpace(body.Message)
	if msg == "" {
		sendError(w, http.StatusBadRequest, "Message cannot be empty.")
		return
	}

	// Kiểm tra quyền quản trị cho các lệnh can thiệp hệ thống (.b5, .b6, .g)
	callerToken := s.GetTokenFromRequest(r)
	callerUsername := s.GetUserFromToken(callerToken)
	if callerUsername == "" {
		callerUsername = strings.ToLower(strings.TrimSpace(body.Username))
	}
	if callerUsername == "" {
		callerUsername = "qtu"
	}

	trimmedMsg := strings.ToLower(msg)
	if (trimmedMsg == ".b5" || trimmedMsg == ".b6" || trimmedMsg == ".g") && !s.CheckUserIsAdmin(callerUsername) {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"type":      "chat",
			"text":      fmt.Sprintf("[X] Lệnh '%s' chỉ khả dụng cho tài khoản Quản trị viên (qtu).", msg),
			"tool_logs": []interface{}{},
		})
		return
	}

	apiKey := strings.TrimSpace(body.APIKey)
	sysPrompt := body.SystemInstruction
	if strings.TrimSpace(sysPrompt) == "" {
		sysPrompt = DefaultSystemPrompt
	}

	engine := strings.TrimSpace(body.Engine)
	if engine == "" {
		if apiKey != "" {
			engine = "gemini"
		} else if IsAgyAvailable() {
			engine = "antigravity"
		}
	} else if engine == "gemini" && apiKey == "" && IsAgyAvailable() {
		engine = "antigravity"
	}

	if engine == "antigravity" {
		if !IsAgyAvailable() {
			sendError(w, http.StatusServiceUnavailable, "Lệnh Antigravity CLI ('agy') không tìm thấy trên hệ thống Termux.")
			return
		}
		model := strings.TrimSpace(body.Model)
		log.Printf("[CHAT AGY] Xử lý qua Antigravity CLI Pro trên Termux (model=%s, msg=%q)", model, msg)
		fullPrompt := BuildAgyPrompt(body.History, msg, sysPrompt)
		reply, err := RunAntigravityCLI(fullPrompt, s.Vault.RootDir, model)
		if err != nil {
			log.Printf("[CHAT AGY ERROR] %v", err)
			sendError(w, http.StatusInternalServerError, err.Error())
			return
		}
		resType, targetWord, audioSent := ClassifyResponse(reply, msg)
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"type":           resType,
			"target_word":    targetWord,
			"audio_sentence": audioSent,
			"text":           reply,
			"tool_logs":      []interface{}{},
			"engine":         "antigravity",
		})
		return
	}

	if apiKey == "" {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"type":      "chat",
			"text":      "[~] Chưa cấu hình Google API Key hoặc Antigravity CLI.\n\nBạn có 2 lựa chọn trong Cài đặt (⚙):\n1. Chọn động cơ 'Antigravity CLI (Termux Pro)' để dùng trực tiếp tài khoản Pro trên máy Termux (không cần API Key).\n2. Hoặc nhập Google Gemini API Key (miễn phí tại https://aistudio.google.com/apikey).",
			"tool_logs": []interface{}{},
		})
		return
	}

	model := strings.TrimSpace(body.Model)
	if model == "" || model == "gemini-2.5-flash" {
		model = "gemini-3.6-flash"
	}

	enableTools := true
	if body.EnableVaultTools != nil {
		enableTools = *body.EnableVaultTools
	}

	// Build contents with strictly alternating user and model turns
	var contents []GeminiContent
	var lastRole string

	for _, turn := range body.History {
		text, _ := turn["text"].(string)
		text = strings.TrimSpace(text)
		if text == "" {
			continue
		}
		role := "user"
		if r, ok := turn["role"].(string); ok && (r == "assistant" || r == "model") {
			role = "model"
		}

		if role == lastRole && len(contents) > 0 {
			contents[len(contents)-1].Parts = append(contents[len(contents)-1].Parts, GeminiPart{Text: text})
		} else {
			contents = append(contents, GeminiContent{
				Role:  role,
				Parts: []GeminiPart{{Text: text}},
			})
			lastRole = role
		}
	}

	// Ensure the first content turn is ALWAYS 'user' (Gemini requirement)
	for len(contents) > 0 && contents[0].Role != "user" {
		contents = contents[1:]
	}

	// Append current user message
	if len(contents) > 0 && contents[len(contents)-1].Role == "user" {
		contents[len(contents)-1].Parts = append(contents[len(contents)-1].Parts, GeminiPart{Text: msg})
	} else {
		contents = append(contents, GeminiContent{
			Role:  "user",
			Parts: []GeminiPart{{Text: msg}},
		})
	}

	log.Printf("[CHAT] model=%s msg=%q historyLen=%d enableTools=%v", model, msg, len(body.History), enableTools)

	client := NewGeminiClient(apiKey)
	result, err := client.ChatWithVault(s.Vault, contents, model, sysPrompt, enableTools)
	if err != nil {
		log.Printf("[CHAT ERROR] %v", err)
		sendError(w, http.StatusInternalServerError, err.Error())
		return
	}

	resType, targetWord, audioSent := ClassifyResponse(result.Text, msg)
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"type":           resType,
		"target_word":    targetWord,
		"audio_sentence": audioSent,
		"text":           result.Text,
		"tool_logs":      result.ToolLogs,
		"engine":         "gemini",
	})
}

func getTailscaleIP() string {
	cmd := exec.Command("ifconfig")
	out, err := cmd.Output()
	if err != nil {
		return ""
	}
	re := regexp.MustCompile(`inet (100\.\d{1,3}\.\d{1,3}\.\d{1,3})`)
	match := re.FindStringSubmatch(string(out))
	if len(match) > 1 {
		return match[1]
	}
	return ""
}

func withCORS(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
		if r.Method == "OPTIONS" {
			log.Printf("[REQ] OPTIONS %s (preflight từ %s)", r.URL.Path, r.RemoteAddr)
			w.WriteHeader(http.StatusOK)
			return
		}
		log.Printf("[REQ] %s %s (từ %s)", r.Method, r.URL.Path, r.RemoteAddr)
		next.ServeHTTP(w, r)
	})
}

func main() {
	portFlag := flag.Int("port", 5000, "Port to listen on (default 5000)")
	hostFlag := flag.String("host", "0.0.0.0", "Host to bind on (default 0.0.0.0)")
	vaultFlag := flag.String("vault", "", "Custom vault root path")
	openFlag := flag.Bool("open", false, "Open browser via termux-open-url")
	tlsFlag := flag.Bool("tls", false, "Serve over HTTPS using the local CA (required for PWA install over Tailscale/LAN)")
	genCertFlag := flag.Bool("gen-cert", false, "Generate the local CA + server certificate, print the install guide, then exit")
	tlsHostsFlag := flag.String("tls-hosts", "zf3", "Comma-separated hostnames to include in the certificate SAN")
	tlsCertFlag := flag.String("tls-cert", "", "Custom server certificate path (PEM)")
	tlsKeyFlag := flag.String("tls-key", "", "Custom server private key path (PEM)")
	tlsForceFlag := flag.Bool("tls-force", false, "Recreate the CA as well, not only the server certificate")
	exportCAFlag := flag.Bool("export-ca", false, "Copy the existing CA certificate to the Download folder, then exit")
	flag.Parse()

	tlsPaths := defaultTLSPaths()
	if *tlsCertFlag != "" {
		tlsPaths.ServerCert = *tlsCertFlag
	}
	if *tlsKeyFlag != "" {
		tlsPaths.ServerKey = *tlsKeyFlag
	}

	if *exportCAFlag {
		if !fileExists(tlsPaths.CACert) {
			fmt.Fprintf(os.Stderr, "[X] Chưa có CA tại %s. Chạy trước: bash app/run.sh gen-cert\n", tlsPaths.CACert)
			os.Exit(1)
		}
		dest := ExportCACert(tlsPaths)
		if dest == "" {
			fmt.Fprintf(os.Stderr, "[X] Không ghi được vào thư mục Download. Chạy termux-setup-storage rồi thử lại.\n")
			os.Exit(1)
		}
		fmt.Printf("[OK] Đã chép CA ra: %s\n", dest)
		fmt.Printf("[*] Máy khác tải trực tiếp tại: https://%s:%d/ca.crt\n",
			strings.TrimSpace(strings.Split(*tlsHostsFlag, ",")[0]), *portFlag)
		return
	}

	if *genCertFlag {
		_, dnsNames, ips, err := GenerateTLSAssets(tlsPaths, *tlsHostsFlag, *tlsForceFlag)
		if err != nil {
			fmt.Fprintf(os.Stderr, "[X] Không tạo được chứng chỉ: %v\n", err)
			os.Exit(1)
		}
		PrintTLSSetupGuide(tlsPaths, ExportCACert(tlsPaths), dnsNames, ips, *portFlag)
		return
	}

	// Locate repo root and web dir
	exePath, _ := os.Executable()
	baseDir := filepath.Dir(filepath.Dir(exePath))

	// Fallback to working directory
	cwd, _ := os.Getwd()
	vaultRoot := cwd
	if *vaultFlag != "" {
		vaultRoot = *vaultFlag
	}

	webDir := filepath.Join(vaultRoot, "app", "web")
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		webDir = filepath.Join(cwd, "app", "web")
		if _, err := os.Stat(webDir); os.IsNotExist(err) {
			webDir = filepath.Join(baseDir, "app", "web")
		}
	}

	vault := NewVaultManager(vaultRoot)
	app := &ServerApp{
		Vault:  vault,
		WebDir: webDir,
		Port:   *portFlag,
		Host:   *hostFlag,
	}
	app.InitSessions()

	mux := http.NewServeMux()

	// Live Reloader cho moi truong phat trien (SSE tu dong reload khi sua file web)
	reloader := NewLiveReloader(webDir)
	mux.Handle("/api/live-reload", reloader)

	// API Handlers
	mux.HandleFunc("/api/status", app.handleStatus)
	mux.HandleFunc("/api/quota", app.handleQuota)
	mux.HandleFunc("/api/vault/list", app.handleVaultList)
	mux.HandleFunc("/api/vault/read", app.handleVaultRead)
	mux.HandleFunc("/api/vault/write", app.handleVaultWrite)
	mux.HandleFunc("/api/vault/search", app.handleVaultSearch)
	mux.HandleFunc("/api/chat", app.handleChat)
	mux.HandleFunc("/api/user/profile", app.handleUserProfile)
	mux.HandleFunc("/api/users/list", app.handleUsersList)
	mux.HandleFunc("/api/auth/login", app.handleAuthLogin)
	mux.HandleFunc("/api/auth/social-login", app.handleAuthSocialLogin)
	mux.HandleFunc("/api/auth/me", app.handleAuthMe)
	mux.HandleFunc("/api/auth/logout", app.handleAuthLogout)
	mux.HandleFunc("/api/auth/oauth-config", app.handleOAuthConfig)
	mux.HandleFunc("/api/auth/accounts", app.handleAuthAccounts)
	mux.HandleFunc("/api/auth/switch", app.handleAuthSwitch)

	// Cho thiết bị khác trong tailnet tải CA về cài, khỏi phải copy file thủ công.
	mux.HandleFunc("/ca.crt", func(w http.ResponseWriter, r *http.Request) {
		data, err := os.ReadFile(tlsPaths.CACert)
		if err != nil {
			http.Error(w, "Chua tao CA. Chay: bash app/run.sh gen-cert", http.StatusNotFound)
			return
		}
		w.Header().Set("Content-Type", "application/x-x509-ca-cert")
		w.Header().Set("Content-Disposition", `attachment; filename="english-ca.crt"`)
		w.Write(data)
	})

	// Static Web Server
	fileServer := http.FileServer(http.Dir(webDir))
	mux.Handle("/", http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Method == "OPTIONS" {
			w.Header().Set("Access-Control-Allow-Origin", "*")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
			w.WriteHeader(http.StatusOK)
			return
		}
		if strings.HasSuffix(r.URL.Path, ".html") || r.URL.Path == "/" || strings.HasSuffix(r.URL.Path, ".css") || strings.HasSuffix(r.URL.Path, ".js") {
			w.Header().Set("Cache-Control", "no-cache, must-revalidate")
		}
		fileServer.ServeHTTP(w, r)
	}))

	tsIP := getTailscaleIP()
	addr := fmt.Sprintf("%s:%d", app.Host, app.Port)

	// Chế độ HTTPS: tự cấp chứng chỉ khi còn thiếu để lần chạy đầu không bị chặn.
	scheme := "http"
	if *tlsFlag {
		scheme = "https"
		if !fileExists(tlsPaths.ServerCert) || !fileExists(tlsPaths.ServerKey) {
			caCreated, dnsNames, ips, err := GenerateTLSAssets(tlsPaths, *tlsHostsFlag, false)
			if err != nil {
				fmt.Fprintf(os.Stderr, "[X] Không tạo được chứng chỉ: %v\n", err)
				os.Exit(1)
			}
			if caCreated {
				PrintTLSSetupGuide(tlsPaths, ExportCACert(tlsPaths), dnsNames, ips, app.Port)
			}
		}
	}

	primaryHost := "localhost"
	tailscaleName := strings.TrimSpace(strings.Split(*tlsHostsFlag, ",")[0])
	if tailscaleName == "" {
		tailscaleName = "zf3"
	}

	fmt.Printf("\n=======================================================\n")
	fmt.Printf("  English Tutor Web App (Golang Engine)\n")
	fmt.Printf("=======================================================\n")
	fmt.Printf("[OK] Cục bộ (trên máy này):     %s://%s:%d\n", scheme, primaryHost, app.Port)
	fmt.Printf("[OK] Qua Tailscale (tên máy):   %s://%s:%d\n", scheme, tailscaleName, app.Port)
	if tsIP != "" {
		fmt.Printf("[OK] Qua Tailscale (địa chỉ IP): %s://%s:%d\n", scheme, tsIP, app.Port)
	}
	if *tlsFlag {
		fmt.Printf("[*] HTTPS bật - cài PWA được trên mọi thiết bị đã cài CA: %s\n", tlsPaths.CACert)
	} else {
		fmt.Printf("[~] HTTPS tắt - chỉ cài PWA được qua localhost. Thêm --tls để bật.\n")
	}
	fmt.Printf("[*] Thư mục Vault: %s\n", app.Vault.RootDir)
	fmt.Printf("[*] Thư mục Web UI: %s\n", app.WebDir)
	fmt.Printf("[*] Bấm Ctrl+C để dừng server.\n\n")

	if *openFlag {
		go func() {
			time.Sleep(300 * time.Millisecond)
			exec.Command("termux-open-url", scheme+"://"+primaryHost+":"+strconv.Itoa(app.Port)).Start()
			fmt.Println("[OK] Đã mở trình duyệt Termux.")
		}()
	}

	server := &http.Server{
		Addr:         addr,
		Handler:      withCORS(mux),
		ReadTimeout:  120 * time.Second,
		WriteTimeout: 120 * time.Second,
	}

	var serveErr error
	if *tlsFlag {
		serveErr = server.ListenAndServeTLS(tlsPaths.ServerCert, tlsPaths.ServerKey)
	} else {
		serveErr = server.ListenAndServe()
	}
	if serveErr != nil && serveErr != http.ErrServerClosed {
		fmt.Fprintf(os.Stderr, "[X] Lỗi khởi động server: %v\n", serveErr)
	}
}
