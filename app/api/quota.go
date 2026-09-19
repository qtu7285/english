package main

import (
	"bytes"
	"context"
	"net/http"
	"os/exec"
	"regexp"
	"sync"
	"time"
)

type QuotaInfo struct {
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
	q := GetCachedQuota()
	if q == nil {
		sendJSON(w, http.StatusOK, map[string]interface{}{
			"available": false,
		})
		return
	}
	sendJSON(w, http.StatusOK, map[string]interface{}{
		"available":   true,
		"gemini_5h":   q.Gemini5h,
		"gemini_week": q.GeminiWeek,
		"claude_5h":   q.Claude5h,
		"claude_week": q.ClaudeWeek,
		"updated_at":  q.UpdatedAt,
	})
}
