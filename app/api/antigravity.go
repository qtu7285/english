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

// RunAntigravityCLI executes a prompt via the local Antigravity CLI session (Termux Pro)
func RunAntigravityCLI(prompt string, workspaceDir string) (string, error) {
	agyBin := LocateAgyBinary()
	if agyBin == "" {
		return "", fmt.Errorf("không tìm thấy lệnh 'agy' trên Termux (~/.local/bin/agy)")
	}

	ctx, cancel := context.WithTimeout(context.Background(), 90*time.Second)
	defer cancel()

	cmd := exec.CommandContext(ctx, agyBin,
		"-p", prompt,
		"--output-format", "text",
		"--disable-slash-commands",
		"--dangerously-skip-permissions",
	)
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
