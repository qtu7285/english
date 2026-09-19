package main

import (
	"bytes"
	"context"
	"fmt"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"time"
)

// LocateAgyBinary returns the path to the agy binary on Termux
func LocateAgyBinary() string {
	home, err := os.UserHomeDir()
	if err == nil {
		p := filepath.Join(home, ".local", "bin", "agy")
		if info, err := os.Stat(p); err == nil && !info.IsDir() {
			return p
		}
	}
	if p, err := exec.LookPath("agy"); err == nil {
		return p
	}
	return ""
}

// IsAgyAvailable checks if the Antigravity CLI binary is callable on Termux
func IsAgyAvailable() bool {
	return LocateAgyBinary() != ""
}

// BuildAgyPrompt builds a comprehensive prompt including pedagogical system instruction and conversation history
func BuildAgyPrompt(history []map[string]interface{}, currentMsg string, sysPrompt string) string {
	var sb strings.Builder

	if sysPrompt != "" {
		sb.WriteString("HƯỚNG DẪN DẠY HỌC (SYSTEM INSTRUCTION):\n")
		sb.WriteString(sysPrompt)
		sb.WriteString("\n\n")
	}

	if len(history) > 0 {
		sb.WriteString("LỊCH SỬ BÀI HỌC VỪA QUA:\n")
		for _, turn := range history {
			role, _ := turn["role"].(string)
			text, _ := turn["text"].(string)
			text = strings.TrimSpace(text)
			if text == "" {
				continue
			}
			if role == "assistant" || role == "model" {
				sb.WriteString("Gia sư AI: ")
			} else {
				sb.WriteString("Người học: ")
			}
			sb.WriteString(text)
			sb.WriteString("\n")
		}
		sb.WriteString("\n")
	}

	sb.WriteString("CÂU TRẢ LỜI / YÊU CẦU MỚI NHẤT CỦA NGƯỜI HỌC:\n")
	sb.WriteString(currentMsg)

	return sb.String()
}

// ResolveAgyModel maps friendly model names to Antigravity CLI supported model identifiers
func ResolveAgyModel(model string) string {
	m := strings.TrimSpace(strings.ToLower(model))
	switch {
	case strings.Contains(m, "3.8") || strings.Contains(m, "flash-3.8"):
		return "gemini-3.8-flash-high"
	case strings.Contains(m, "3.7") || strings.Contains(m, "flash-3.7"):
		return "gemini-3.7-flash-high"
	case strings.Contains(m, "3.6") || strings.Contains(m, "flash-3.6"):
		return "gemini-3.6-flash-high"
	case strings.Contains(m, "pro") || strings.Contains(m, "3.1"):
		return "gemini-3.1-pro-high"
	case strings.Contains(m, "sonnet"):
		return "claude-sonnet-4-6"
	case strings.Contains(m, "opus"):
		return "claude-opus-4-6-thinking"
	case strings.Contains(m, "gpt") || strings.Contains(m, "oss"):
		return "gpt-oss-120b-medium"
	default:
		if m != "" && !strings.HasPrefix(m, "antigravity") {
			return m
		}
		return ""
	}
}

// RunAntigravityCLI executes a prompt via the local Antigravity CLI session (Termux Pro)
func RunAntigravityCLI(prompt string, workspaceDir string, model string) (string, error) {
	agyBin := LocateAgyBinary()
	if agyBin == "" {
		return "", fmt.Errorf("không tìm thấy lệnh 'agy' trên Termux (~/.local/bin/agy)")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	args := []string{
		"-p", prompt,
		"--output-format", "text",
		"--disable-slash-commands",
		"--dangerously-skip-permissions",
	}

	agyModel := ResolveAgyModel(model)
	if agyModel != "" {
		args = append(args, "--model", agyModel)
	}

	cmd := exec.CommandContext(ctx, agyBin, args...)
	if workspaceDir != "" {
		cmd.Dir = workspaceDir
	}

	var stdout, stderr bytes.Buffer
	cmd.Stdout = &stdout
	cmd.Stderr = &stderr

	err := cmd.Run()
	outStr := strings.TrimSpace(stdout.String())
	if err != nil {
		errStr := strings.TrimSpace(stderr.String())
		if errStr == "" {
			errStr = err.Error()
		}
		if ctx.Err() == context.DeadlineExceeded {
			return "", fmt.Errorf("Antigravity CLI quá thời gian chờ (90s)")
		}
		return outStr, fmt.Errorf("Antigravity CLI: %s", errStr)
	}

	if outStr == "" {
		return "Không nhận được phản hồi từ Antigravity CLI.", nil
	}

	return outStr, nil
}
