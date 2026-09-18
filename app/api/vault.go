package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strings"
)

type FileInfo struct {
	Name       string `json:"name"`
	Path       string `json:"path"`
	Size       int64  `json:"size"`
	Modified   int64  `json:"modified"`
	Type       string `json:"type"`
	IsMarkdown bool   `json:"is_markdown"`
	IsCSV      bool   `json:"is_csv"`
}

type FileResult struct {
	Path    string `json:"path,omitempty"`
	Name    string `json:"name,omitempty"`
	Content string `json:"content,omitempty"`
	Size    int64  `json:"size,omitempty"`
	Error   string `json:"error,omitempty"`
}

type WriteResult struct {
	Success      bool   `json:"success"`
	Path         string `json:"path,omitempty"`
	BytesWritten int    `json:"bytes_written,omitempty"`
	Mode         string `json:"mode,omitempty"`
	Error        string `json:"error,omitempty"`
}

type SearchResult struct {
	Path      string `json:"path"`
	MatchType string `json:"match_type"`
	Line      int    `json:"line,omitempty"`
	Snippet   string `json:"snippet"`
}

type VaultManager struct {
	RootDir string
}

func NewVaultManager(rootDir string) *VaultManager {
	abs, err := filepath.Abs(rootDir)
	if err != nil {
		abs = rootDir
	}
	return &VaultManager{RootDir: abs}
}

func (v *VaultManager) resolveSafePath(relPath string) (string, error) {
	clean := strings.TrimLeft(filepath.Clean(relPath), "/\\.")
	target := filepath.Join(v.RootDir, clean)
	absTarget, err := filepath.Abs(target)
	if err != nil {
		return "", err
	}

	if !strings.HasPrefix(absTarget, v.RootDir) {
		return "", errors.New("access denied: path is outside vault root")
	}
	return absTarget, nil
}

func (v *VaultManager) ListFiles(subpath string, maxDepth int) ([]FileInfo, error) {
	targetDir, err := v.resolveSafePath(subpath)
	if err != nil {
		return nil, err
	}

	var results []FileInfo
	baseParts := len(strings.Split(filepath.ToSlash(targetDir), "/"))

	err = filepath.Walk(targetDir, func(p string, info os.FileInfo, err error) error {
		if err != nil {
			return nil
		}

		parts := len(strings.Split(filepath.ToSlash(p), "/"))
		if parts-baseParts > maxDepth {
			if info.IsDir() {
				return filepath.SkipDir
			}
			return nil
		}

		name := info.Name()
		if info.IsDir() {
			if strings.HasPrefix(name, ".") || name == "__pycache__" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}

		if strings.HasPrefix(name, ".") {
			return nil
		}

		rel, err := filepath.Rel(v.RootDir, p)
		if err != nil {
			return nil
		}

		ext := strings.ToLower(filepath.Ext(p))
		results = append(results, FileInfo{
			Name:       name,
			Path:       filepath.ToSlash(rel),
			Size:       info.Size(),
			Modified:   info.ModTime().Unix(),
			Type:       strings.TrimPrefix(ext, "."),
			IsMarkdown: ext == ".md",
			IsCSV:      ext == ".csv",
		})
		return nil
	})

	return results, err
}

func (v *VaultManager) ReadFile(relPath string, maxBytes int) FileResult {
	target, err := v.resolveSafePath(relPath)
	if err != nil {
		return FileResult{Error: err.Error()}
	}

	info, err := os.Stat(target)
	if err != nil {
		return FileResult{Error: fmt.Sprintf("File '%s' does not exist.", relPath)}
	}
	if info.IsDir() {
		return FileResult{Error: fmt.Sprintf("'%s' is a directory, not a file.", relPath)}
	}

	file, err := os.Open(target)
	if err != nil {
		return FileResult{Error: err.Error()}
	}
	defer file.Close()

	if maxBytes <= 0 {
		maxBytes = 100000
	}

	buf := make([]byte, maxBytes)
	n, err := io.ReadFull(file, buf)
	if err != nil && err != io.EOF && err != io.ErrUnexpectedEOF {
		return FileResult{Error: err.Error()}
	}

	content := string(buf[:n])
	if int64(n) < info.Size() {
		content += fmt.Sprintf("\n\n... [Content truncated, total %d bytes] ...", info.Size())
	}

	return FileResult{
		Path:    filepath.ToSlash(relPath),
		Name:    info.Name(),
		Content: content,
		Size:    info.Size(),
	}
}

func (v *VaultManager) WriteFile(relPath string, content string, appendMode bool) WriteResult {
	target, err := v.resolveSafePath(relPath)
	if err != nil {
		return WriteResult{Success: false, Error: err.Error()}
	}

	if err := os.MkdirAll(filepath.Dir(target), 0755); err != nil {
		return WriteResult{Success: false, Error: err.Error()}
	}

	flag := os.O_CREATE | os.O_WRONLY
	modeStr := "overwrite"
	if appendMode {
		flag |= os.O_APPEND
		modeStr = "append"
	} else {
		flag |= os.O_TRUNC
	}

	f, err := os.OpenFile(target, flag, 0644)
	if err != nil {
		return WriteResult{Success: false, Error: err.Error()}
	}
	defer f.Close()

	n, err := f.WriteString(content)
	if err != nil {
		return WriteResult{Success: false, Error: err.Error()}
	}

	return WriteResult{
		Success:      true,
		Path:         filepath.ToSlash(relPath),
		BytesWritten: n,
		Mode:         modeStr,
	}
}

func (v *VaultManager) SearchVault(query string, maxResults int) []SearchResult {
	if maxResults <= 0 {
		maxResults = 15
	}
	queryLower := strings.ToLower(query)
	var results []SearchResult

	allowedExts := map[string]bool{
		".md":   true,
		".csv":  true,
		".txt":  true,
		".json": true,
	}

	filepath.Walk(v.RootDir, func(p string, info os.FileInfo, err error) error {
		if err != nil || len(results) >= maxResults {
			return nil
		}

		name := info.Name()
		if info.IsDir() {
			if strings.HasPrefix(name, ".") || name == "__pycache__" || name == "node_modules" {
				return filepath.SkipDir
			}
			return nil
		}

		ext := strings.ToLower(filepath.Ext(p))
		if !allowedExts[ext] {
			return nil
		}

		rel, err := filepath.Rel(v.RootDir, p)
		if err != nil {
			return nil
		}
		relSlash := filepath.ToSlash(rel)

		// Match filename
		if strings.Contains(strings.ToLower(name), queryLower) {
			results = append(results, SearchResult{
				Path:      relSlash,
				MatchType: "filename",
				Snippet:   fmt.Sprintf("Filename matches '%s'", query),
			})
			if len(results) >= maxResults {
				return filepath.SkipDir
			}
			return nil
		}

		// Match file content
		f, err := os.Open(p)
		if err != nil {
			return nil
		}
		defer f.Close()

		scanner := bufio.NewScanner(f)
		lineNum := 0
		for scanner.Scan() {
			lineNum++
			line := scanner.Text()
			if strings.Contains(strings.ToLower(line), queryLower) {
				snippet := strings.TrimSpace(line)
				if len(snippet) > 160 {
					snippet = snippet[:160] + "..."
				}
				results = append(results, SearchResult{
					Path:      relSlash,
					MatchType: "content",
					Line:      lineNum,
					Snippet:   snippet,
				})
				if len(results) >= maxResults {
					return filepath.SkipDir
				}
				break
			}
		}

		return nil
	})

	return results
}
