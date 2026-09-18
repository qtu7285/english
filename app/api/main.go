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
	"time"
)

const DefaultSystemPrompt = `You are an English tutor. Explain in Vietnamese, briefly, naturally, and clearly.
Use ASCII bracketed status labels: [OK], [~], [X], [NEXT], [RETRY], [SAVE], [CONFIRM], [EN], and [VI]. Do not use emojis.

Rules:
1. Explaining a word/phrase (e.g. '.urge', 'inspire'):
   - Provide meaning in Vietnamese
   - Part of speech
   - Common usage/collocations
   - A short natural English example with Vietnamese meaning
   - End with: [NEXT] Nhập số câu để luyện (ví dụ 5), hoặc .từ_mới để chuyển từ.

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

func (s *ServerApp) handleChat(w http.ResponseWriter, r *http.Request) {
	var body struct {
		Engine            string                   `json:"engine"`
		Message           string                   `json:"message"`
		History           []map[string]interface{} `json:"history"`
		APIKey            string                   `json:"apiKey"`
		Model             string                   `json:"model"`
		SystemInstruction string                   `json:"systemInstruction"`
		EnableVaultTools  *bool                    `json:"enableVaultTools"`
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
	}

	if engine == "antigravity" {
		if !IsAgyAvailable() {
			sendError(w, http.StatusServiceUnavailable, "Lệnh Antigravity CLI ('agy') không tìm thấy trên hệ thống Termux.")
			return
		}
		log.Printf("[CHAT AGY] Xử lý qua Antigravity CLI Pro trên Termux (msg=%q)", msg)
		fullPrompt := BuildAgyPrompt(body.History, msg, sysPrompt)
		reply, err := RunAntigravityCLI(fullPrompt, s.Vault.RootDir)
		if err != nil {
			log.Printf("[CHAT AGY ERROR] %v", err)
			sendError(w, http.StatusInternalServerError, err.Error())
			return
		}
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"text":      reply,
			"tool_logs": []interface{}{},
			"engine":    "antigravity",
		})
		return
	}

	if apiKey == "" {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"text": "[~] Chưa cấu hình Google API Key hoặc Antigravity CLI.\n\nBạn có 2 lựa chọn trong Cài đặt (⚙):\n1. Chọn động cơ 'Antigravity CLI (Termux Pro)' để dùng trực tiếp tài khoản Pro trên máy Termux (không cần API Key).\n2. Hoặc nhập Google Gemini API Key (miễn phí tại https://aistudio.google.com/apikey).",
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

	sendJSON(w, http.StatusOK, result)
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

func main() {
	portFlag := flag.Int("port", 5000, "Port to listen on (default 5000)")
	hostFlag := flag.String("host", "0.0.0.0", "Host to bind on (default 0.0.0.0)")
	vaultFlag := flag.String("vault", "", "Custom vault root path")
	openFlag := flag.Bool("open", false, "Open browser via termux-open-url")
	flag.Parse()

	// Locate repo root and web dir
	exePath, _ := os.Executable()
	baseDir := filepath.Dir(filepath.Dir(exePath))

	// Fallback to working directory
	cwd, _ := os.Getwd()
	vaultRoot := cwd
	if *vaultFlag != "" {
		vaultRoot = *vaultFlag
	}

	webDir := filepath.Join(baseDir, "app", "web")
	if _, err := os.Stat(webDir); os.IsNotExist(err) {
		webDir = filepath.Join(cwd, "app", "web")
	}

	vault := NewVaultManager(vaultRoot)
	app := &ServerApp{
		Vault:  vault,
		WebDir: webDir,
		Port:   *portFlag,
		Host:   *hostFlag,
	}

	mux := http.NewServeMux()

	// API Handlers
	mux.HandleFunc("/api/status", app.handleStatus)
	mux.HandleFunc("/api/vault/list", app.handleVaultList)
	mux.HandleFunc("/api/vault/read", app.handleVaultRead)
	mux.HandleFunc("/api/vault/write", app.handleVaultWrite)
	mux.HandleFunc("/api/vault/search", app.handleVaultSearch)
	mux.HandleFunc("/api/chat", app.handleChat)

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
		fileServer.ServeHTTP(w, r)
	}))

	tsIP := getTailscaleIP()
	addr := fmt.Sprintf("%s:%d", app.Host, app.Port)

	fmt.Printf("\n=======================================================\n")
	fmt.Printf("  English Tutor Web App (Golang Engine)\n")
	fmt.Printf("=======================================================\n")
	fmt.Printf("[OK] Cục bộ (trên máy này):     http://localhost:%d\n", app.Port)
	fmt.Printf("[OK] Qua Tailscale (tên máy):   http://zf3:%d\n", app.Port)
	if tsIP != "" {
		fmt.Printf("[OK] Qua Tailscale (địa chỉ IP): http://%s:%d\n", tsIP, app.Port)
	}
	fmt.Printf("[*] Thư mục Vault: %s\n", app.Vault.RootDir)
	fmt.Printf("[*] Thư mục Web UI: %s\n", app.WebDir)
	fmt.Printf("[*] Bấm Ctrl+C để dừng server.\n\n")

	if *openFlag {
		go func() {
			time.Sleep(300 * time.Millisecond)
			exec.Command("termux-open-url", "http://localhost:"+strconv.Itoa(app.Port)).Start()
			fmt.Println("[OK] Đã mở trình duyệt Termux.")
		}()
	}

	server := &http.Server{
		Addr:         addr,
		Handler:      mux,
		ReadTimeout:  60 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		fmt.Fprintf(os.Stderr, "[X] Lỗi khởi động server: %v\n", err)
	}
}
