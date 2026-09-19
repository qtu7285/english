package main

import (
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"regexp"
	"strings"
	"sync"
	"time"
)

type QuotaInfo struct {
	Email      string `json:"email"`
	Gemini5h   string `json:"gemini_5h"`
	GeminiWeek string `json:"gemini_week"`
	Claude5h   string `json:"claude_5h"`
	ClaudeWeek string `json:"claude_week"`
	UpdatedAt  string `json:"updated_at"`
}

var (
	quotaCache   *QuotaInfo
	quotaCacheMu sync.RWMutex
	quotaTTL     = 3 * time.Minute
	lastFetch    time.Time
)

var (
	reGeminiWeek = regexp.MustCompile(`(?i)Gemini Models\s+Weekly Limit Remaining\s+([0-9]+%)`)
	reGemini5h   = regexp.MustCompile(`(?i)Gemini Models\s+Five Hour Limit Remaining\s+([0-9]+%)`)
	reClaudeWeek = regexp.MustCompile(`(?i)Claude and GPT models\s+Weekly Limit Remaining\s+([0-9]+%)`)
	reClaude5h   = regexp.MustCompile(`(?i)Claude and GPT models\s+Five Hour Limit Remaining\s+([0-9]+%)`)
)

// ExtractAgyEmail extracts the Google email associated with the local Antigravity CLI session
func ExtractAgyEmail() string {
	home, err := os.UserHomeDir()
	if err != nil {
		return ""
	}
	p := filepath.Join(home, ".gemini", "antigravity-cli", "antigravity-oauth-token")
	data, err := os.ReadFile(p)
	if err != nil {
		return ""
	}
	var tok struct {
		IDToken string `json:"id_token"`
	}
	if err := json.Unmarshal(data, &tok); err != nil || tok.IDToken == "" {
		return ""
	}
	parts := strings.Split(tok.IDToken, ".")
	if len(parts) < 2 {
		return ""
	}
	payloadSegment := parts[1]
	if rem := len(payloadSegment) % 4; rem != 0 {
		payloadSegment += strings.Repeat("=", 4-rem)
	}
	payloadBytes, err := base64.URLEncoding.DecodeString(payloadSegment)
	if err != nil {
		payloadBytes, err = base64.RawURLEncoding.DecodeString(parts[1])
		if err != nil {
			return ""
		}
	}
	var claims struct {
		Email string `json:"email"`
	}
	if err := json.Unmarshal(payloadBytes, &claims); err != nil {
		return ""
	}
	return claims.Email
}

func FetchQuotaFromCLI() (*QuotaInfo, error) {
	agyBin := LocateAgyBinary()
	if agyBin == "" {
		return nil, nil
	}

	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, agyBin,
		"-p", "/usage",
		"--output-format", "text",
	)

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	if err := cmd.Run(); err != nil {
		return nil, err
	}

	out := stdout.String()
	q := &QuotaInfo{
		Email:     ExtractAgyEmail(),
		UpdatedAt: time.Now().UTC().Format(time.RFC3339),
	}

	if m := reGemini5h.FindStringSubmatch(out); len(m) > 1 {
		q.Gemini5h = m[1]
	}
	if m := reGeminiWeek.FindStringSubmatch(out); len(m) > 1 {
		q.GeminiWeek = m[1]
	}
	if m := reClaude5h.FindStringSubmatch(out); len(m) > 1 {
		q.Claude5h = m[1]
	}
	if m := reClaudeWeek.FindStringSubmatch(out); len(m) > 1 {
		q.ClaudeWeek = m[1]
	}

	return q, nil
}

func GetCachedQuota() *QuotaInfo {
	quotaCacheMu.RLock()
	if quotaCache != nil && time.Since(lastFetch) < quotaTTL {
		q := quotaCache
		quotaCacheMu.RUnlock()
		return q
	}
	quotaCacheMu.RUnlock()

	q, err := FetchQuotaFromCLI()
	if err != nil || q == nil {
		quotaCacheMu.RLock()
		defer quotaCacheMu.RUnlock()
		return quotaCache
	}

	quotaCacheMu.Lock()
	quotaCache = q
	lastFetch = time.Now()
	quotaCacheMu.Unlock()

	return q
}

func (s *ServerApp) handleQuota(w http.ResponseWriter, r *http.Request) {
	username := strings.ToLower(strings.TrimSpace(r.URL.Query().Get("username")))
	if username == "" {
		username = "qtu"
	}
	if !s.CheckUserCanViewAIInfo(username) {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"available": false,
			"reason":    "permission_denied",
		})
		return
	}

	q := GetCachedQuota()
	if q == nil {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"available": false,
		})
		return
	}
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"available":   true,
		"email":       q.Email,
		"gemini_5h":   q.Gemini5h,
		"gemini_week": q.GeminiWeek,
		"claude_5h":   q.Claude5h,
		"claude_week": q.ClaudeWeek,
		"updated_at":  q.UpdatedAt,
	})
}
