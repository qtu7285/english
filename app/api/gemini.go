package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"net/url"
	"strings"
	"time"
)

const GeminiAPIBase = "https://generativelanguage.googleapis.com/v1beta"

// Types for Gemini Request & Response
type GeminiContent struct {
	Role  string       `json:"role"`
	Parts []GeminiPart `json:"parts"`
}

type GeminiPart struct {
	Text             string                `json:"text,omitempty"`
	FunctionCall     *GeminiFunctionCall   `json:"functionCall,omitempty"`
	FunctionResponse *GeminiFunctionResult `json:"functionResponse,omitempty"`
}

type GeminiFunctionCall struct {
	Name string                 `json:"name"`
	Args map[string]interface{} `json:"args"`
}

type GeminiFunctionResult struct {
	Name     string                 `json:"name"`
	Response map[string]interface{} `json:"response"`
}

type GeminiToolDecl struct {
	FunctionDeclarations []FunctionDeclaration `json:"functionDeclarations"`
}

type FunctionDeclaration struct {
	Name        string                 `json:"name"`
	Description string                 `json:"description"`
	Parameters  map[string]interface{} `json:"parameters"`
}

type GenerationConfig struct {
	Temperature float64 `json:"temperature"`
	TopP        float64 `json:"topP"`
}

type GeminiSystemInstruction struct {
	Parts []GeminiPart `json:"parts"`
}

type GeminiRequest struct {
	Contents          []GeminiContent          `json:"contents"`
	SystemInstruction *GeminiSystemInstruction `json:"systemInstruction,omitempty"`
	Tools             []GeminiToolDecl         `json:"tools,omitempty"`
	GenerationConfig  GenerationConfig         `json:"generationConfig"`
}

type GeminiCandidate struct {
	Content GeminiContent `json:"content"`
}

type GeminiResponse struct {
	Candidates []GeminiCandidate      `json:"candidates"`
	Error      map[string]interface{} `json:"error,omitempty"`
}

type ToolExecutionLog struct {
	Tool   string                 `json:"tool"`
	Args   map[string]interface{} `json:"args"`
	Result interface{}            `json:"result"`
}

type ChatResult struct {
	Text     string             `json:"text"`
	ToolLogs []ToolExecutionLog `json:"tool_logs"`
}

var VaultToolDeclarations = []FunctionDeclaration{
	{
		Name:        "list_vault_files",
		Description: "List files and directories in the local workspace or learning vault (such as WORDS/, notes, etc.).",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"subpath": map[string]interface{}{
					"type":        "string",
					"description": "Optional subdirectory relative to vault root, e.g. 'WORDS' or '' for root.",
				},
			},
			"required": []string{},
		},
	},
	{
		Name:        "read_vault_file",
		Description: "Read the contents of a specific file in the vault (e.g. 'WORDS/urge.csv', 'AGENTS.md', markdown notes).",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"path": map[string]interface{}{
					"type":        "string",
					"description": "Relative path to the file inside the vault, e.g. 'WORDS/urge.csv'.",
				},
			},
			"required": []string{"path"},
		},
	},
	{
		Name:        "write_vault_file",
		Description: "Write or append content to a file in the vault (e.g. saving new vocabulary, notes, or quiz questions).",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"path": map[string]interface{}{
					"type":        "string",
					"description": "Relative path to the file to create or update.",
				},
				"content": map[string]interface{}{
					"type":        "string",
					"description": "Text content to write into the file.",
				},
				"append": map[string]interface{}{
					"type":        "boolean",
					"description": "True to append to existing content, False to overwrite.",
				},
			},
			"required": []string{"path", "content"},
		},
	},
	{
		Name:        "search_vault",
		Description: "Search for keywords across files (markdown, CSV, text) in the vault.",
		Parameters: map[string]interface{}{
			"type": "object",
			"properties": map[string]interface{}{
				"query": map[string]interface{}{
					"type":        "string",
					"description": "Search term, word, or collocation to find in files.",
				},
			},
			"required": []string{"query"},
		},
	},
}

type GeminiClient struct {
	APIKey     string
	OAuthToken string
	HTTPClient *http.Client
}

func NewGeminiClient(apiKey, oauthToken string) *GeminiClient {
	return &GeminiClient{
		APIKey:     strings.TrimSpace(apiKey),
		OAuthToken: strings.TrimSpace(oauthToken),
		HTTPClient: &http.Client{Timeout: 45 * time.Second},
	}
}

func (c *GeminiClient) makeRequest(model string, payload *GeminiRequest) (*GeminiResponse, error) {
	reqURL := fmt.Sprintf("%s/models/%s:generateContent", GeminiAPIBase, model)
	if c.APIKey != "" {
		reqURL += fmt.Sprintf("?key=%s", url.QueryEscape(c.APIKey))
	}

	bodyBytes, err := json.Marshal(payload)
	if err != nil {
		return nil, err
	}

	maxRetries := 3
	backoffSec := 2 * time.Second

	for attempt := 0; attempt < maxRetries; attempt++ {
		req, err := http.NewRequest("POST", reqURL, bytes.NewBuffer(bodyBytes))
		if err != nil {
			return nil, err
		}

		req.Header.Set("Content-Type", "application/json")
		if c.OAuthToken != "" {
			req.Header.Set("Authorization", fmt.Sprintf("Bearer %s", c.OAuthToken))
		}

		resp, err := c.HTTPClient.Do(req)
		if err != nil {
			if attempt < maxRetries-1 {
				time.Sleep(backoffSec * time.Duration(attempt+1))
				continue
			}
			return nil, fmt.Errorf("network error calling Gemini: %v", err)
		}

		respBytes, err := io.ReadAll(resp.Body)
		resp.Body.Close()
		if err != nil {
			return nil, err
		}

		// Handle retryable status codes (503 High demand, 429 Rate limit, 500 Server error)
		if resp.StatusCode == 503 || resp.StatusCode == 429 || resp.StatusCode == 500 {
			if attempt < maxRetries-1 {
				time.Sleep(backoffSec * time.Duration(attempt+1))
				continue
			}
		}

		if resp.StatusCode != http.StatusOK {
			var errObj struct {
				Error struct {
					Message string `json:"message"`
				} `json:"error"`
			}
			json.Unmarshal(respBytes, &errObj)
			msg := errObj.Error.Message
			if msg == "" {
				msg = string(respBytes)
			}
			log.Printf("[Gemini ERROR %d]: %s", resp.StatusCode, msg)
			return nil, fmt.Errorf("Gemini API Error (%d): %s", resp.StatusCode, msg)
		}

		var geminiResp GeminiResponse
		if err := json.Unmarshal(respBytes, &geminiResp); err != nil {
			return nil, err
		}
		return &geminiResp, nil
	}

	return nil, fmt.Errorf("Gemini request failed after %d retries", maxRetries)
}

func (c *GeminiClient) ChatWithVault(
	vault *VaultManager,
	contents []GeminiContent,
	model string,
	systemInstruction string,
	enableVaultTools bool,
) (ChatResult, error) {
	if model == "" {
		model = "gemini-2.5-flash"
	}

	workingContents := make([]GeminiContent, len(contents))
	copy(workingContents, contents)

	var toolLogs []ToolExecutionLog

	payload := &GeminiRequest{
		Contents: workingContents,
		GenerationConfig: GenerationConfig{
			Temperature: 0.7,
			TopP:        0.95,
		},
	}

	if systemInstruction != "" {
		payload.SystemInstruction = &GeminiSystemInstruction{
			Parts: []GeminiPart{{Text: systemInstruction}},
		}
	}

	if enableVaultTools {
		payload.Tools = []GeminiToolDecl{
			{FunctionDeclarations: VaultToolDeclarations},
		}
	}

	maxToolHops := 5
	for hop := 0; hop < maxToolHops; hop++ {
		resp, err := c.makeRequest(model, payload)
		if err != nil {
			// If tools were enabled and we got a 400 Bad Request on the first hop, retry once without tools
			if enableVaultTools && hop == 0 && strings.Contains(err.Error(), "(400)") {
				log.Printf("[Gemini WARN] 400 error with tools; retrying without tools for model %s: %v", model, err)
				payload.Tools = nil
				resp, err = c.makeRequest(model, payload)
				if err != nil {
					return ChatResult{}, err
				}
			} else {
				return ChatResult{}, err
			}
		}

		if len(resp.Candidates) == 0 {
			return ChatResult{Text: "Không nhận được phản hồi từ AI.", ToolLogs: toolLogs}, nil
		}

		candidate := resp.Candidates[0]
		parts := candidate.Content.Parts

		// Check for function calls
		var functionCalls []*GeminiFunctionCall
		for i := range parts {
			if parts[i].FunctionCall != nil {
				functionCalls = append(functionCalls, parts[i].FunctionCall)
			}
		}

		if len(functionCalls) == 0 {
			// Answer is ready
			var textBuilder strings.Builder
			for _, p := range parts {
				if p.Text != "" {
					textBuilder.WriteString(p.Text)
				}
			}
			return ChatResult{Text: textBuilder.String(), ToolLogs: toolLogs}, nil
		}

		// Append model's tool request to contents
		workingContents = append(workingContents, candidate.Content)

		// Execute function calls
		var toolResponseParts []GeminiPart
		for _, fc := range functionCalls {
			resultMap := executeVaultTool(vault, fc.Name, fc.Args)
			toolLogs = append(toolLogs, ToolExecutionLog{
				Tool:   fc.Name,
				Args:   fc.Args,
				Result: resultMap,
			})
			toolResponseParts = append(toolResponseParts, GeminiPart{
				FunctionResponse: &GeminiFunctionResult{
					Name:     fc.Name,
					Response: resultMap,
				},
			})
		}

		workingContents = append(workingContents, GeminiContent{
			Role:  "user",
			Parts: toolResponseParts,
		})
		payload.Contents = workingContents
	}

	return ChatResult{
		Text:     "Đã hoàn thành các bước truy xuất file trong vault.",
		ToolLogs: toolLogs,
	}, nil
}

func executeVaultTool(vault *VaultManager, name string, args map[string]interface{}) map[string]interface{} {
	switch name {
	case "list_vault_files":
		subpath, _ := args["subpath"].(string)
		files, err := vault.ListFiles(subpath, 3)
		if err != nil {
			return map[string]interface{}{"error": err.Error()}
		}
		if len(files) > 50 {
			files = files[:50]
		}
		return map[string]interface{}{"files": files, "total": len(files)}

	case "read_vault_file":
		path, _ := args["path"].(string)
		res := vault.ReadFile(path, 100000)
		bytes, _ := json.Marshal(res)
		var out map[string]interface{}
		json.Unmarshal(bytes, &out)
		return out

	case "write_vault_file":
		path, _ := args["path"].(string)
		content, _ := args["content"].(string)
		appendMode, _ := args["append"].(bool)
		res := vault.WriteFile(path, content, appendMode)
		bytes, _ := json.Marshal(res)
		var out map[string]interface{}
		json.Unmarshal(bytes, &out)
		return out

	case "search_vault":
		query, _ := args["query"].(string)
		matches := vault.SearchVault(query, 15)
		return map[string]interface{}{"matches": matches, "count": len(matches)}

	default:
		return map[string]interface{}{"error": fmt.Sprintf("Unknown tool: %s", name)}
	}
}
