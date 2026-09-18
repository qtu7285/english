/**
 * English Tutor & Vault AI - Frontend Application
 */

let initialModel = localStorage.getItem("gemini_model") || "gemini-3.6-flash";
if (initialModel === "gemini-2.5-flash" || initialModel === "gemini-1.5-flash" || initialModel === "gemini-2.0-flash") {
  initialModel = "gemini-3.6-flash";
  localStorage.setItem("gemini_model", "gemini-3.6-flash");
}

// State
const state = {
  engine: localStorage.getItem("ai_engine") || "antigravity",
  apiKey: localStorage.getItem("gemini_api_key") || "",
  model: initialModel,
  enableVaultTools: localStorage.getItem("enable_vault_tools") !== "false",
  ttsRate: parseFloat(localStorage.getItem("tts_rate") || "0.9"),
  conversation: [],
  currentVaultPath: "",
  selectedVaultFile: null
};

// DOM Elements
const chatViewport = document.getElementById("chatViewport");
const chatMessages = document.getElementById("chatMessages");
const chatForm = document.getElementById("chatForm");
const messageInput = document.getElementById("messageInput");
const sendBtn = document.getElementById("sendBtn");
const clearBtn = document.getElementById("clearBtn");

const settingsBtn = document.getElementById("settingsBtn");
const settingsModal = document.getElementById("settingsModal");
const closeSettingsBtn = document.getElementById("closeSettingsBtn");
const saveSettingsBtn = document.getElementById("saveSettingsBtn");
const engineSelect = document.getElementById("engineSelect");
const engineHint = document.getElementById("engineHint");
const apiKeyGroup = document.getElementById("apiKeyGroup");
const apiKeyInput = document.getElementById("apiKeyInput");
const modelGroup = document.getElementById("modelGroup");
const modelSelect = document.getElementById("modelSelect");
const customModelInput = document.getElementById("customModelInput");
const enableVaultToolsCheck = document.getElementById("enableVaultToolsCheck");
const ttsRate = document.getElementById("ttsRate");
const ttsRateVal = document.getElementById("ttsRateVal");

const vaultBtn = document.getElementById("vaultBtn");
const vaultModal = document.getElementById("vaultModal");
const closeVaultBtn = document.getElementById("closeVaultBtn");
const vaultSearchInput = document.getElementById("vaultSearchInput");
const refreshVaultBtn = document.getElementById("refreshVaultBtn");
const vaultFileList = document.getElementById("vaultFileList");
const vaultPreview = document.getElementById("vaultPreview");
const insertToChatBtn = document.getElementById("insertToChatBtn");

function stripHtmlAndEntities(str) {
  if (!str) return "";
  return str
    .replace(/<[^>]+>/g, " ")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/\s+/g, " ")
    .trim();
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function escapeAttr(str) {
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function makeAudioButton(text) {
  const clean = stripHtmlAndEntities(text)
    .replace(/\[.*?\]/g, "")
    .replace(/[*#`"“”]/g, "")
    .trim();
  if (!clean) return "";
  const attr = escapeAttr(clean);
  return `<button type="button" class="inline-audio-btn" data-text="${attr}" title="Phát âm câu này">🔊</button>`;
}

// Vietnamese diacritics detection
const VIETNAMESE_REGEX = /[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]/i;

function extractEnglishElements(text) {
  if (!text) return { word: "", sentences: [] };
  const lines = text.split('\n');
  const sentences = [];
  let targetWord = "";

  // 0. Explicit audio placeholders: [audio:text] or [🔊:text] or [speak:text]
  const audioPlaceholders = text.match(/\[(?:audio|speak|play|sound|🔊):\s*([^\]]+)\]/gi);
  if (audioPlaceholders) {
    audioPlaceholders.forEach(ph => {
      const m = ph.match(/\[(?:audio|speak|play|sound|🔊):\s*([^\]]+)\]/i);
      if (m && m[1]) {
        const val = stripHtmlAndEntities(m[1]).replace(/[*#`"“”]/g, "").trim();
        if (val && !VIETNAMESE_REGEX.test(val)) {
          if (val.split(/\s+/).length <= 2 && !targetWord) {
            targetWord = val;
          } else if (val.split(/\s+/).length > 2 && !sentences.includes(val)) {
            sentences.push(val);
          }
        }
      }
    });
  }

  // 1. Look for bold words or target headwords at the start of response
  const boldMatches = text.match(/\*\*([a-zA-Z\s\-]{2,30})\*\*/g);
  if (boldMatches) {
    for (const b of boldMatches) {
      const w = b.replace(/\*\*/g, "").trim();
      if (!VIETNAMESE_REGEX.test(w) && w.split(/\s+/).length <= 3) {
        if (!targetWord) targetWord = w;
        break;
      }
    }
  }
  if (!targetWord) {
    const dotMatch = text.match(/\.([a-zA-Z]{2,30})/);
    if (dotMatch) targetWord = dotMatch[1].trim();
  }

  // 2. Look for quoted English sentences
  const quotes = text.match(/["“]([A-Za-z0-9\s,.'’!?\-_]{5,})["”]/g);
  if (quotes) {
    quotes.forEach(q => {
      const cleanQ = q.replace(/["“”]/g, "").trim();
      if (!VIETNAMESE_REGEX.test(cleanQ) && cleanQ.length > 5) {
        if (!sentences.includes(cleanQ)) sentences.push(cleanQ);
      }
    });
  }

  // 3. Scan lines for English sentences followed by Vietnamese translations in parens
  lines.forEach(line => {
    let clean = line
      .replace(/\[.*?\]/g, "")
      .replace(/^[\s*\-#\d.]+/, "")
      .replace(/`.*?`/g, "")
      .trim();

    const parenIdx = clean.search(/\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\)/i);
    if (parenIdx > 0) {
      clean = clean.substring(0, parenIdx).replace(/[*#`"“”]/g, "").trim();
      if (clean && !VIETNAMESE_REGEX.test(clean) && clean.split(/\s+/).length >= 3) {
        if (!sentences.includes(clean)) sentences.push(clean);
      }
    }
  });

  return { word: targetWord, sentences };
}

// Extract Multiple Choice Options dynamically (A, B, C, D, E, True/False, etc.)
function extractChoiceOptions(text) {
  if (!text) return [];
  const lines = text.split('\n');
  const choices = [];

  for (const rawLine of lines) {
    const line = rawLine.replace(/[*_`]/g, "").trim();

    // Match choices: "A. xxx", "A) xxx", "- A. xxx", "* A. xxx"
    const letterMatch = line.match(/^[-*•]?\s*([A-Fa-f])[\.\)]\s+(.+)$/);
    if (letterMatch) {
      const key = letterMatch[1].toUpperCase();
      const optionText = letterMatch[2].trim();
      if (!choices.some(c => c.key === key)) {
        choices.push({
          key: key,
          text: optionText,
          label: `${key}. ${optionText}`,
          send: key
        });
      }
      continue;
    }

    // Match True / False or Đúng / Sai
    const tfMatch = line.match(/^[-*•]?\s*(True|False|Đúng|Sai)[\.\:]?\s*(.*)$/i);
    if (tfMatch && !line.includes("?")) {
      const key = tfMatch[1].trim();
      if (!choices.some(c => c.key.toLowerCase() === key.toLowerCase())) {
        choices.push({
          key: key,
          text: tfMatch[2].trim() || key,
          label: key,
          send: key
        });
      }
    }
  }

  return choices.length >= 2 ? choices : [];
}

// Update the dynamic choice chips in the Quick Chips bar
function updateDynamicChoices(choices) {
  const container = document.getElementById("dynamicChoiceChips");
  if (!container) return;
  container.innerHTML = "";

  if (!choices || choices.length === 0) return;

  choices.forEach(c => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip chip-choice";
    btn.setAttribute("data-send", c.send);
    btn.innerText = c.key;
    btn.title = `${c.key}: ${c.text}`;
    container.appendChild(btn);
  });
}

function processLineForAudio(line) {
  if (!line || line.includes("inline-audio-btn") || line.includes("<pre>") || line.includes("<code>")) return line;

  // Pattern 1: Target Headword, e.g. <strong>capable</strong> or <h3>capable</h3>
  const boldHeadword = line.match(/^[\s\-]*(?:<h[1-3]>)?\s*<strong>([A-Za-z][A-Za-z\s\-]{1,29})<\/strong>/);
  if (boldHeadword) {
    const word = stripHtmlAndEntities(boldHeadword[1]);
    if (word && !VIETNAMESE_REGEX.test(word)) {
      const btn = makeAudioButton(word);
      if (btn) return line.replace(boldHeadword[0], boldHeadword[0] + ' ' + btn);
    }
  }

  // Pattern 2: English sentence followed by Vietnamese in parentheses
  const parenIdx = line.search(/\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\)/i);
  if (parenIdx > 0) {
    const leftPart = line.substring(0, parenIdx);
    const rightPart = line.substring(parenIdx);
    const cleanLeft = stripHtmlAndEntities(leftPart)
      .replace(/^[*\s\-_•\d.]+/, "")
      .replace(/[*#`"“”]/g, "")
      .trim();
    if (cleanLeft && !VIETNAMESE_REGEX.test(cleanLeft) && cleanLeft.split(/\s+/).length >= 2) {
      const btn = makeAudioButton(cleanLeft);
      if (btn) return leftPart.trimEnd() + ' ' + btn + ' ' + rightPart;
    }
  }

  // Pattern 3: Explicit quoted English sentence anywhere in the line
  const quoteMatch = line.match(/(?:&quot;|["“])([^"“”&<]{4,})(?:&quot;|["”])/);
  if (quoteMatch) {
    const cleanQuote = stripHtmlAndEntities(quoteMatch[1]).replace(/[*#`]/g, "").trim();
    if (cleanQuote && !VIETNAMESE_REGEX.test(cleanQuote) && cleanQuote.split(/\s+/).length >= 2) {
      const btn = makeAudioButton(cleanQuote);
      if (btn) return line.replace(quoteMatch[0], quoteMatch[0] + ' ' + btn);
    }
  }

  return line;
}

// Markdown & Status Tag Renderer
function renderMarkdown(text) {
  if (!text) return "";

  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks
  html = html.replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre><code>$2</code></pre>');
  // Inline code
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');

  // Convert explicit audio placeholders: [audio:Text] or [🔊:Text] or [speak:Text]
  html = html.replace(/\[(?:audio|speak|play|sound|🔊):\s*([^\]]+)\]/gi, (match, toSpeak) => {
    const clean = stripHtmlAndEntities(toSpeak)
      .replace(/[*#`"“”]/g, "")
      .trim();
    if (!clean) return "";
    const attr = escapeAttr(clean);
    return `<button type="button" class="inline-audio-btn" data-text="${attr}" title="Phát âm: ${attr}">🔊</button>`;
  });

  // Bold & Italic
  html = html.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*([^*]+)\*/g, '<em>$1</em>');

  // Headers
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
  html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');

  // Status Badges
  html = html.replace(/\[OK\]/g, '<span class="badge badge-tool">[OK]</span>');
  html = html.replace(/\[EN\]/g, '<span class="badge badge-en">[EN]</span>');
  html = html.replace(/\[VI\]/g, '<span class="badge badge-vi">[VI]</span>');
  html = html.replace(/\[NEXT\]/g, '<strong style="color: #fbbf24;">[NEXT]</strong>');
  html = html.replace(/\[CONFIRM\]/g, '<strong style="color: #38bdf8;">[CONFIRM]</strong>');
  html = html.replace(/\[D([1-3])\]/g, '<span class="badge badge-tool">[D$1]</span>');

  // Place audio icon at the END of lines containing target words or example sentences
  const rawLines = html.split('\n');
  const processedLines = rawLines.map(line => processLineForAudio(line));
  html = processedLines.join('\n');

  // Newlines to breaks
  html = html.replace(/\n\n+/g, '</p><p>');
  html = html.replace(/\n/g, '<br>');

  return `<p>${html}</p>`;
}

// Speech Synthesis (Audio Pronunciation) with Android Chrome fix
function speakText(explicitText) {
  if (!("speechSynthesis" in window)) {
    alert("Trình duyệt không hỗ trợ Web Speech API.");
    return;
  }

  let toSpeak = explicitText;
  if (!toSpeak || typeof toSpeak !== "string" || !toSpeak.trim()) {
    const selected = window.getSelection().toString().trim();
    if (selected && !VIETNAMESE_REGEX.test(selected)) {
      toSpeak = selected;
    }
  }

  if (!toSpeak) return;

  // Clean HTML tags, Vietnamese parens, markdown, blanks
  let clean = stripHtmlAndEntities(toSpeak);
  clean = clean.replace(/\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\)/gi, "");
  clean = clean
    .replace(/\[.*?\]/g, "")
    .replace(/(_+\s*)+/g, ", ")
    .replace(/[*#`"“”]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!clean) return;

  // Chrome Android audio engine fix: resume if paused, cancel, and start after short 50ms delay
  try {
    if (window.speechSynthesis.paused) {
      window.speechSynthesis.resume();
    }
    window.speechSynthesis.cancel();
  } catch (err) {}

  setTimeout(() => {
    const utterance = new SpeechSynthesisUtterance(clean);
    utterance.lang = "en-US";
    utterance.rate = state.ttsRate || 0.9;

    // Pick English voice
    const voices = window.speechSynthesis.getVoices();
    const enVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.default));
    if (enVoice) utterance.voice = enVoice;

    window.speechSynthesis.speak(utterance);
  }, 50);
}

// Copy to Clipboard (Safe for non-HTTPS / LAN IP and older browsers)
async function copyToClipboard(text, btnElement) {
  if (!text) return false;
  const clean = stripHtmlAndEntities(text)
    .replace(/\[.*?\]/g, "")
    .replace(/[*#`]/g, "")
    .trim();
  if (!clean) return false;

  let copied = false;

  // Method 1: Modern navigator.clipboard API (requires secure context HTTPS or localhost)
  if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(clean);
      copied = true;
    } catch (err) {
      copied = false;
    }
  }

  // Method 2: Fallback textarea + execCommand('copy') (works on HTTP, LAN IP, older webviews)
  if (!copied) {
    try {
      const textArea = document.createElement("textarea");
      textArea.value = clean;
      textArea.style.position = "fixed";
      textArea.style.left = "-9999px";
      textArea.style.top = "0";
      textArea.setAttribute("readonly", "");
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();
      copied = document.execCommand("copy");
      document.body.removeChild(textArea);
    } catch (err) {
      copied = false;
    }
  }

  // UI feedback if triggered by a button click
  if (btnElement) {
    if (copied) {
      const orig = btnElement.innerText;
      btnElement.innerText = "✓ Đã chép câu";
      setTimeout(() => { btnElement.innerText = orig; }, 1800);
    } else {
      const orig = btnElement.innerText;
      btnElement.innerText = "Chép thủ công";
      setTimeout(() => { btnElement.innerText = orig; }, 1800);
    }
  }

  return copied;
}

// Append message to UI
function appendMessage(role, text, toolLogs = []) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.innerText = role === "user" ? "YOU" : "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const content = document.createElement("div");
  content.className = "bubble-content";
  content.innerHTML = renderMarkdown(text);

  bubble.appendChild(content);

  // Bottom action bar for assistant messages: reliable, large, easy-to-tap buttons
  if (role === "assistant") {
    // 1. Dynamic multiple-choice buttons inside the question bubble
    const choices = extractChoiceOptions(text);
    if (choices.length > 0) {
      const choiceGroup = document.createElement("div");
      choiceGroup.className = "bubble-choices";
      choices.forEach(c => {
        const choiceBtn = document.createElement("button");
        choiceBtn.type = "button";
        choiceBtn.className = "btn-bubble-choice";
        choiceBtn.innerHTML = `<span class="choice-badge">${escapeHtml(c.key)}</span><span class="choice-text">${escapeHtml(c.text)}</span>`;
        choiceBtn.onclick = () => {
          choiceGroup.querySelectorAll(".btn-bubble-choice").forEach(b => {
            b.disabled = true;
            b.classList.remove("selected");
          });
          choiceBtn.classList.add("selected");
          handleSendMessage(c.send);
          updateDynamicChoices([]);
        };
        choiceGroup.appendChild(choiceBtn);
      });
      bubble.appendChild(choiceGroup);
      updateDynamicChoices(choices);
    } else {
      updateDynamicChoices([]);
    }

    // 2. Audio & Copy action buttons
    const extracted = extractEnglishElements(text);
    if (extracted.word || extracted.sentences.length > 0) {
      const actions = document.createElement("div");
      actions.className = "bubble-actions";

      // 1. Target word button
      if (extracted.word) {
        const wordBtn = document.createElement("button");
        wordBtn.type = "button";
        wordBtn.className = "btn-action speak-btn";
        wordBtn.setAttribute("data-text", extracted.word);
        wordBtn.innerHTML = `🔊 Từ: <strong>${escapeHtml(extracted.word)}</strong>`;
        actions.appendChild(wordBtn);
      }

      // 2. Main sentence button
      if (extracted.sentences.length > 0) {
        const mainSentence = extracted.sentences[0];
        const sentBtn = document.createElement("button");
        sentBtn.type = "button";
        sentBtn.className = "btn-action speak-btn";
        sentBtn.setAttribute("data-text", mainSentence);
        sentBtn.innerHTML = `🔊 Nghe câu`;
        actions.appendChild(sentBtn);

        const copyBtn = document.createElement("button");
        copyBtn.type = "button";
        copyBtn.className = "btn-action copy-btn";
        copyBtn.setAttribute("data-text", mainSentence);
        copyBtn.innerHTML = `📋 Chép câu`;
        actions.appendChild(copyBtn);
      }

      bubble.appendChild(actions);
    }
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatMessages.appendChild(row);

  chatViewport.scrollTop = chatViewport.scrollHeight;
  return row;
}

// Global click delegation for inline audio and copy buttons
chatMessages.addEventListener("click", (e) => {
  const audioBtn = e.target.closest(".inline-audio-btn, .speak-btn");
  if (audioBtn) {
    e.preventDefault();
    e.stopPropagation();
    const textToSpeak = audioBtn.getAttribute("data-text");
    if (textToSpeak) {
      speakText(textToSpeak);
      audioBtn.classList.add("playing");
      setTimeout(() => audioBtn.classList.remove("playing"), 1500);
    }
    return;
  }

  const copyBtn = e.target.closest(".inline-copy-btn, .copy-btn");
  if (copyBtn) {
    e.preventDefault();
    e.stopPropagation();
    const textToCopy = copyBtn.getAttribute("data-text");
    if (textToCopy) {
      copyToClipboard(textToCopy, copyBtn);
    }
    return;
  }
});

// Lively Loading Indicator with gentle status transitions
function createLoadingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row assistant loading-row";

  const avatar = document.createElement("div");
  avatar.className = "avatar avatar-thinking";
  avatar.innerText = "AI";

  const bubble = document.createElement("div");
  bubble.className = "bubble bubble-loading";

  bubble.innerHTML = `
    <div class="thinking-container">
      <div class="typing-wave">
        <span class="wave-dot"></span>
        <span class="wave-dot"></span>
        <span class="wave-dot"></span>
      </div>
      <div class="thinking-status">
        <span class="thinking-label">Đang suy nghĩ...</span>
      </div>
    </div>
  `;

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatMessages.appendChild(row);
  chatViewport.scrollTop = chatViewport.scrollHeight;

  // Gentle, friendly status transitions (no internal technical or Termux narration)
  const phases = [
    "Đang suy nghĩ...",
    "Đang chuẩn bị câu trả lời...",
    "Đang phân tích cấu trúc...",
    "Đang hoàn thiện ví dụ tự nhiên..."
  ];
  let phaseIdx = 0;
  const labelEl = bubble.querySelector(".thinking-label");
  const timer = setInterval(() => {
    phaseIdx = (phaseIdx + 1) % phases.length;
    if (labelEl) {
      labelEl.classList.add("fade-out");
      setTimeout(() => {
        labelEl.innerText = phases[phaseIdx];
        labelEl.classList.remove("fade-out");
      }, 250);
    }
  }, 3500);

  return {
    remove: () => {
      clearInterval(timer);
      row.remove();
    }
  };
}

// Send Message Handler
async function handleSendMessage(msgText) {
  const text = (msgText || messageInput.value).trim();
  if (!text) return;

  messageInput.value = "";
  messageInput.style.height = "auto";
  updateDynamicChoices([]);

  // Prior history (before this current turn)
  const priorHistory = state.conversation.slice(-10);

  // Add user bubble in UI
  appendMessage("user", text);

  // Show lively loading indicator (no technical/Termux narration)
  const loadingIndicator = createLoadingIndicator();
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        engine: state.engine,
        message: text,
        history: priorHistory,
        apiKey: state.apiKey,
        model: state.model,
        enableVaultTools: state.enableVaultTools
      })
    });

    const data = await res.json();
    loadingIndicator.remove();

    if (data.error) {
      appendMessage("assistant", `[X] Lỗi: ${data.error}`);
    } else {
      state.conversation.push({ role: "user", text });
      state.conversation.push({ role: "assistant", text: data.text });
      appendMessage("assistant", data.text, data.tool_logs);

      // Automatic sentence clipboard (per AGENTS.md rule for Tap to Translate)
      const extracted = extractEnglishElements(data.text);
      if (extracted.sentences && extracted.sentences.length > 0) {
        copyToClipboard(extracted.sentences[0]);
      }
    }
  } catch (err) {
    loadingIndicator.remove();
    appendMessage("assistant", `[X] Lỗi kết nối: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

// Vault Explorer
async function loadVaultFiles(subpath = "") {
  vaultFileList.innerHTML = '<div class="vault-loading-box"><span class="vault-spinner"></span></div>';
  try {
    const res = await fetch(`/api/vault/list?subpath=${encodeURIComponent(subpath)}`);
    const data = await res.json();
    renderVaultFiles(data.files || []);
  } catch (err) {
    vaultFileList.innerHTML = `<div style="color:red; padding:10px;">Lỗi: ${err.message}</div>`;
  }
}

function renderVaultFiles(files) {
  vaultFileList.innerHTML = "";
  if (files.length === 0) {
    vaultFileList.innerHTML = '<div style="padding:10px; color:#94a3b8;">Không tìm thấy file nào.</div>';
    return;
  }

  files.forEach(f => {
    const item = document.createElement("div");
    item.className = "vault-item";
    item.innerHTML = `
      <span class="file-name">${f.name}</span>
      <span class="file-badge">${f.type}</span>
    `;
    item.onclick = () => selectVaultFile(f, item);
    vaultFileList.appendChild(item);
  });
}

async function selectVaultFile(file, element) {
  document.querySelectorAll(".vault-item").forEach(el => el.classList.remove("selected"));
  element.classList.add("selected");
  state.selectedVaultFile = file;
  insertToChatBtn.disabled = false;

  vaultPreview.innerHTML = "Đang tải...";
  try {
    const res = await fetch(`/api/vault/read?path=${encodeURIComponent(file.path)}`);
    const data = await res.json();
    if (data.content !== undefined) {
      vaultPreview.innerText = data.content;
    } else {
      vaultPreview.innerText = data.error || "Không thể đọc file.";
    }
  } catch (err) {
    vaultPreview.innerText = "Lỗi khi đọc file: " + err.message;
  }
}

// Event Listeners
chatForm.onsubmit = (e) => {
  e.preventDefault();
  handleSendMessage();
};

messageInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSendMessage();
  }
});

// Auto-expand textarea
messageInput.addEventListener("input", () => {
  messageInput.style.height = "auto";
  messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + "px";
});

// Quick Chips Event Delegation
const quickChipsBar = document.getElementById("quickChipsBar");
if (quickChipsBar) {
  quickChipsBar.addEventListener("click", (e) => {
    const chip = e.target.closest(".chip");
    if (chip) {
      const sendVal = chip.getAttribute("data-send");
      if (sendVal) {
        handleSendMessage(sendVal);
      }
    }
  });
}

// Clear Chat
clearBtn.onclick = () => {
  if (confirm("Bạn có muốn xóa toàn bộ lịch sử trò chuyện hiện tại không?")) {
    chatMessages.innerHTML = "";
    state.conversation = [];
  }
};

// Settings Modal Handlers
function updateEngineUI() {
  if (engineSelect.value === "antigravity") {
    engineHint.innerText = "Sử dụng trực tiếp tài khoản Pro đã đăng nhập trên Termux, không lo hết hạn ngạch.";
    apiKeyInput.placeholder = "Tùy chọn nếu dùng Antigravity Pro...";
  } else {
    engineHint.innerText = "Gọi trực tiếp đến Google Gemini REST API qua API Key của bạn (phản hồi siêu nhanh ~1s).";
    apiKeyInput.placeholder = "AIzaSy... (Bắt buộc với Gemini REST API)";
  }
}

engineSelect.onchange = updateEngineUI;

modelSelect.onchange = () => {
  if (modelSelect.value === "custom") {
    customModelInput.style.display = "block";
    customModelInput.focus();
  } else {
    customModelInput.style.display = "none";
  }
};

settingsBtn.onclick = () => {
  engineSelect.value = state.engine;
  updateEngineUI();
  apiKeyInput.value = state.apiKey;

  const optionExists = Array.from(modelSelect.options).some(opt => opt.value === state.model);
  if (optionExists) {
    modelSelect.value = state.model;
    customModelInput.style.display = "none";
  } else {
    modelSelect.value = "custom";
    customModelInput.value = state.model;
    customModelInput.style.display = "block";
  }

  enableVaultToolsCheck.checked = state.enableVaultTools;
  ttsRate.value = state.ttsRate;
  ttsRateVal.innerText = state.ttsRate + "x";
  settingsModal.classList.remove("hidden");
};

closeSettingsBtn.onclick = () => settingsModal.classList.add("hidden");

saveSettingsBtn.onclick = () => {
  state.engine = engineSelect.value;
  state.apiKey = apiKeyInput.value.trim();

  if (modelSelect.value === "custom") {
    state.model = customModelInput.value.trim() || "gemini-3.6-flash";
  } else {
    state.model = modelSelect.value;
  }

  state.enableVaultTools = enableVaultToolsCheck.checked;
  state.ttsRate = parseFloat(ttsRate.value);

  localStorage.setItem("ai_engine", state.engine);
  localStorage.setItem("gemini_api_key", state.apiKey);
  localStorage.setItem("gemini_model", state.model);
  localStorage.setItem("enable_vault_tools", state.enableVaultTools);
  localStorage.setItem("tts_rate", state.ttsRate);

  settingsModal.classList.add("hidden");
  const engineDesc = state.engine === "antigravity" ? "Antigravity CLI (Termux Pro)" : `Gemini REST API (${state.model})`;
  appendMessage("assistant", `[OK] Đã lưu cài đặt thành công (Động cơ: ${engineDesc}).`);
};

ttsRate.oninput = () => {
  ttsRateVal.innerText = ttsRate.value + "x";
};

// Purge OAuth credentials left in localStorage by earlier versions
["gemini_oauth_token", "oauth_client_id", "oauth_client_secret"].forEach(k => localStorage.removeItem(k));

// Vault Modal Handlers
vaultBtn.onclick = () => {
  vaultModal.classList.remove("hidden");
  loadVaultFiles();
};

closeVaultBtn.onclick = () => vaultModal.classList.add("hidden");
refreshVaultBtn.onclick = () => loadVaultFiles();

vaultSearchInput.oninput = async (e) => {
  const q = e.target.value.trim();
  if (!q) {
    loadVaultFiles();
    return;
  }
  try {
    const res = await fetch(`/api/vault/search?q=${encodeURIComponent(q)}`);
    const data = await res.json();
    renderVaultFiles((data.matches || []).map(m => ({
      name: m.path.split("/").pop(),
      path: m.path,
      type: m.match_type === "filename" ? "file" : `line ${m.line}`
    })));
  } catch (err) {}
};

insertToChatBtn.onclick = () => {
  if (state.selectedVaultFile && vaultPreview.innerText) {
    messageInput.value = `Hãy phân tích nội dung file ${state.selectedVaultFile.path}:\n\n` + vaultPreview.innerText.slice(0, 1000);
    vaultModal.classList.add("hidden");
    messageInput.focus();
  }
};

// Close modal on click outside
window.onclick = (e) => {
  if (e.target === settingsModal) settingsModal.classList.add("hidden");
  if (e.target === vaultModal) vaultModal.classList.add("hidden");
};

// PWA Install Prompt Handler
let deferredPrompt = null;
const installPwaBtn = document.getElementById("installPwaBtn");

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  if (installPwaBtn) {
    installPwaBtn.style.display = "inline-flex";
  }
});

if (installPwaBtn) {
  installPwaBtn.onclick = async () => {
    if (deferredPrompt) {
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === "accepted") {
        installPwaBtn.style.display = "none";
      } else {
        alert("Gợi ý: Do server đang chạy cục bộ trên Termux (localhost), máy chủ Google không thể đóng gói WebAPK tự động. Bạn chỉ cần bấm Menu 3 chấm của Chrome -> chọn 'Tạo lối tắt' (hoặc 'Thêm vào màn hình chính') là sẽ ghim được icon ứng dụng ra màn hình chính!");
      }
      deferredPrompt = null;
    } else {
      alert("Để ghim ứng dụng ra màn hình chính: Bấm Menu 3 chấm của Chrome -> chọn 'Tạo lối tắt' (hoặc 'Thêm vào màn hình chính').");
    }
  };
}

window.addEventListener("appinstalled", () => {
  if (installPwaBtn) installPwaBtn.style.display = "none";
  deferredPrompt = null;
});

// Register PWA Service Worker
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        reg.onupdatefound = () => {
          const installingWorker = reg.installing;
          if (installingWorker) {
            installingWorker.onstatechange = () => {
              if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('[PWA] Đã cập nhật phiên bản mới.');
              }
            };
          }
        };
      })
      .catch((err) => {
        console.warn('[PWA] Service Worker registration skipped:', err);
      });
  });
}

