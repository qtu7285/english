/**
 * English Tutor & Vault AI - Frontend Application
 */

let initialModel = localStorage.getItem("gemini_model") || "gemini-2.5-flash";
if (initialModel === "gemini-1.5-flash" || initialModel === "gemini-2.0-flash") {
  initialModel = "gemini-2.5-flash";
  localStorage.setItem("gemini_model", "gemini-2.5-flash");
}

// State
const state = {
  apiKey: localStorage.getItem("gemini_api_key") || "",
  oauthToken: localStorage.getItem("gemini_oauth_token") || "",
  oauthClientId: localStorage.getItem("oauth_client_id") || "",
  oauthClientSecret: localStorage.getItem("oauth_client_secret") || "",
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
const apiKeyInput = document.getElementById("apiKeyInput");
const oauthClientId = document.getElementById("oauthClientId");
const oauthClientSecret = document.getElementById("oauthClientSecret");
const loginGoogleBtn = document.getElementById("loginGoogleBtn");
const oauthStatus = document.getElementById("oauthStatus");
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

function escapeAttr(str) {
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function makeAudioButton(text) {
  const clean = text.trim();
  const attr = escapeAttr(clean);
  return `<button type="button" class="inline-audio-btn" data-text="${attr}" title="Phát âm câu này">🔊</button>`;
}

function processLineForAudio(line) {
  if (!line || line.includes("inline-audio-btn")) return line;

  // Case 1: Quoted English sentence in this line
  // e.g. - "She urged him to apply for the job." (Cô ấy thúc giục...)
  const quoteMatch = line.match(/(&quot;|["“])([A-Za-z0-9\s,.'’!?\-_]{4,})(&quot;|["”])/);
  if (quoteMatch) {
    const enText = quoteMatch[2].trim();
    if (!VIETNAMESE_REGEX.test(enText) && enText.split(/\s+/).length >= 2) {
      return line + ' ' + makeAudioButton(enText);
    }
  }

  // Case 2: Target headword line: e.g. **urge** (verb) /ɜːrdʒ/
  const boldWord = line.match(/^[\s*\-#]*\*\*([A-Za-z\s\-]{2,30})\*\*(.*)$/);
  if (boldWord && !VIETNAMESE_REGEX.test(boldWord[1])) {
    const word = boldWord[1].trim();
    return line + ' ' + makeAudioButton(word);
  }

  // Case 3: Unquoted English sentence preceding Vietnamese explanation in parens
  // e.g. - She urged him to reconsider. (Cô ấy khuyên...)
  const parenMatch = line.match(/([A-Z][A-Za-z0-9\s,.'’!?\-_]{6,}[.!?])\s*(\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\))/);
  if (parenMatch) {
    const enText = parenMatch[1].trim();
    if (!VIETNAMESE_REGEX.test(enText) && enText.split(/\s+/).length >= 3) {
      return line + ' ' + makeAudioButton(enText);
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

// Vietnamese diacritics detection
const VIETNAMESE_REGEX = /[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]/i;

// Speech Synthesis (Audio Pronunciation)
function speakText(explicitText) {
  if (!("speechSynthesis" in window)) {
    alert("Trình duyệt không hỗ trợ Web Speech API.");
    return;
  }

  // Use explicitText when passed; ONLY fallback to selection if explicitText is missing
  let toSpeak = explicitText;
  if (!toSpeak || typeof toSpeak !== "string" || !toSpeak.trim()) {
    const selected = window.getSelection().toString().trim();
    if (selected && !VIETNAMESE_REGEX.test(selected)) {
      toSpeak = selected;
    }
  }

  if (!toSpeak) return;

  window.speechSynthesis.cancel();

  // Strip Vietnamese in parens if any sneaked in
  toSpeak = toSpeak.replace(/\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\)/gi, "");

  // Clean brackets, blanks, quotes
  let clean = toSpeak
    .replace(/\[.*?\]/g, "")
    .replace(/_+/g, "blank")
    .replace(/[*#`"“”]/g, "")
    .trim();

  if (!clean) return;

  const utterance = new SpeechSynthesisUtterance(clean);
  utterance.lang = "en-US";
  utterance.rate = state.ttsRate;

  // Try to find native English voice
  const voices = window.speechSynthesis.getVoices();
  const enVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.default));
  if (enVoice) utterance.voice = enVoice;

  window.speechSynthesis.speak(utterance);
}

// Copy to Clipboard
async function copyToClipboard(text, btnElement) {
  const clean = text.replace(/\[.*?\]/g, "").replace(/[*#`]/g, "").trim();
  try {
    await navigator.clipboard.writeText(clean);
    if (btnElement) {
      const orig = btnElement.innerText;
      btnElement.innerText = "✓ Đã chép câu";
      setTimeout(() => { btnElement.innerText = orig; }, 1800);
    }
  } catch (err) {
    alert("Không thể sao chép: " + err);
  }
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

  // If tool calls were executed, show small disclosure
  if (toolLogs && toolLogs.length > 0) {
    const toolBox = document.createElement("div");
    toolBox.style.marginTop = "8px";
    toolBox.style.fontSize = "11px";
    toolBox.style.color = "#94a3b8";
    toolBox.innerHTML = toolLogs.map(t =>
      `<div>🛠️ <code>${t.tool}</code> (${JSON.stringify(t.args)})</div>`
    ).join("");
    content.appendChild(toolBox);
  }

  bubble.appendChild(content);

  row.appendChild(avatar);
  row.appendChild(bubble);
  chatMessages.appendChild(row);

  chatViewport.scrollTop = chatViewport.scrollHeight;
  return row;
}

// Global click delegation for inline audio and copy buttons
chatMessages.addEventListener("click", (e) => {
  const audioBtn = e.target.closest(".inline-audio-btn");
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

  const copyBtn = e.target.closest(".inline-copy-btn");
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

// Send Message Handler
async function handleSendMessage(msgText) {
  const text = (msgText || messageInput.value).trim();
  if (!text) return;

  messageInput.value = "";
  messageInput.style.height = "auto";

  // Prior history (before this current turn)
  const priorHistory = state.conversation.slice(-10);

  // Add user bubble in UI
  appendMessage("user", text);

  // Show loading indicator
  const loadingRow = appendMessage("assistant", "Đang xử lý...");
  sendBtn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: priorHistory,
        apiKey: state.apiKey,
        oauthToken: state.oauthToken,
        model: state.model,
        enableVaultTools: state.enableVaultTools
      })
    });

    const data = await res.json();
    loadingRow.remove();

    if (data.error) {
      appendMessage("assistant", `[X] Lỗi: ${data.error}`);
    } else {
      state.conversation.push({ role: "user", text });
      state.conversation.push({ role: "assistant", text: data.text });
      appendMessage("assistant", data.text, data.tool_logs);
    }
  } catch (err) {
    loadingRow.remove();
    appendMessage("assistant", `[X] Lỗi kết nối mạng: ${err.message}`);
  } finally {
    sendBtn.disabled = false;
  }
}

// Vault Explorer
async function loadVaultFiles(subpath = "") {
  vaultFileList.innerHTML = '<div class="loading-state">Đang nạp file...</div>';
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

// Quick Chips
document.querySelectorAll(".chip").forEach(chip => {
  chip.onclick = () => {
    const sendVal = chip.getAttribute("data-send");
    handleSendMessage(sendVal);
  };
});

// Clear Chat
clearBtn.onclick = () => {
  if (confirm("Bạn có muốn xóa toàn bộ lịch sử trò chuyện hiện tại không?")) {
    chatMessages.innerHTML = "";
    state.conversation = [];
  }
};

// Settings Modal Handlers
modelSelect.onchange = () => {
  if (modelSelect.value === "custom") {
    customModelInput.style.display = "block";
    customModelInput.focus();
  } else {
    customModelInput.style.display = "none";
  }
};

settingsBtn.onclick = () => {
  apiKeyInput.value = state.apiKey;
  oauthClientId.value = state.oauthClientId;
  oauthClientSecret.value = state.oauthClientSecret;

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
  state.apiKey = apiKeyInput.value.trim();
  state.oauthClientId = oauthClientId.value.trim();
  state.oauthClientSecret = oauthClientSecret.value.trim();

  if (modelSelect.value === "custom") {
    state.model = customModelInput.value.trim() || "gemini-3.6-flash";
  } else {
    state.model = modelSelect.value;
  }

  state.enableVaultTools = enableVaultToolsCheck.checked;
  state.ttsRate = parseFloat(ttsRate.value);

  localStorage.setItem("gemini_api_key", state.apiKey);
  localStorage.setItem("oauth_client_id", state.oauthClientId);
  localStorage.setItem("oauth_client_secret", state.oauthClientSecret);
  localStorage.setItem("gemini_model", state.model);
  localStorage.setItem("enable_vault_tools", state.enableVaultTools);
  localStorage.setItem("tts_rate", state.ttsRate);

  settingsModal.classList.add("hidden");
  appendMessage("assistant", `[OK] Đã lưu cấu hình cài đặt thành công (Mô hình: ${state.model}).`);
};

ttsRate.oninput = () => {
  ttsRateVal.innerText = ttsRate.value + "x";
};

// Tabs in settings
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.onclick = () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    const target = btn.getAttribute("data-tab");
    document.getElementById(target).classList.add("active");
  };
});

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
