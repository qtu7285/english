/**
 * English Tutor & Vault AI - Frontend Application
 */

let initialModel = localStorage.getItem("gemini_model") || "gemini-3.6-flash";
if (initialModel === "gemini-2.5-flash" || initialModel === "gemini-1.5-flash" || initialModel === "gemini-2.0-flash") {
  initialModel = "gemini-3.6-flash";
  localStorage.setItem("gemini_model", "gemini-3.6-flash");
}

// Ngăn trình duyệt tự động khôi phục vị trí cuộn khi tải lại trang
if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}
window.scrollTo(0, 0);

// Đồng bộ chiều cao khả dụng chính xác từ visualViewport cho thiết bị di động
function syncAppHeight() {
  const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
  document.documentElement.style.setProperty("--app-height", `${vh}px`);
}
if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", syncAppHeight);
  window.visualViewport.addEventListener("scroll", syncAppHeight);
}
window.addEventListener("resize", syncAppHeight);
syncAppHeight();

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
const vaultLayout = document.getElementById("vaultLayout");
const vaultFileList = document.getElementById("vaultFileList");
const vaultPreview = document.getElementById("vaultPreview");
const vaultBackBtn = document.getElementById("vaultBackBtn");
const insertToChatBtn = document.getElementById("insertToChatBtn");

// Haptic feedback helper for mobile touch
function triggerHaptic(ms = 25) {
  if (navigator && typeof navigator.vibrate === "function") {
    try { navigator.vibrate(ms); } catch (e) {}
  }
}

// English TTS Voice caching for mobile browsers
let cachedEnVoice = null;
function refreshEnglishVoice() {
  if (!("speechSynthesis" in window)) return;
  const voices = window.speechSynthesis.getVoices();
  if (!voices || voices.length === 0) return;
  cachedEnVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.default)) ||
                  voices.find(v => v.lang.startsWith("en")) || null;
}
if ("speechSynthesis" in window) {
  refreshEnglishVoice();
  window.speechSynthesis.onvoiceschanged = refreshEnglishVoice;
}

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

// Helper quan ly an/hien thanh Quick Chips khi khong co chip nao
function updateQuickChipsVisibility() {
  const bar = document.getElementById("quickChipsBar");
  if (!bar) return;
  const hasChips = bar.querySelectorAll(".chip").length > 0;
  bar.style.display = hasChips ? "flex" : "none";
}

// Update the dynamic choice chips in the Quick Chips bar
function updateDynamicChoices(choices) {
  const container = document.getElementById("dynamicChoiceChips");
  if (!container) return;
  container.innerHTML = "";

  if (!choices || choices.length === 0) {
    updateQuickChipsVisibility();
    return;
  }

  choices.forEach(c => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "chip chip-choice";
    btn.setAttribute("data-send", c.send);
    btn.innerText = c.key;
    btn.title = `${c.key}: ${c.text}`;
    container.appendChild(btn);
  });

  updateQuickChipsVisibility();
}

// Update dynamic context chips (e.g. '3 câu luyện', '5 câu luyện') based on tutoring flow
function updateContextChips(lastText) {
  const container = document.getElementById("dynamicContextChips");
  if (!container) return;
  container.innerHTML = "";

  if (!lastText) {
    // Trang thai ban dau: an toan bo chip de giu giao dien gon gang
    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu dang trong mot cau hoi luyen tap (Cau 1/N, Cau 2/N...)
  const isQuestion = /Câu\s+\d+\/\d+|\[D[1-3]\]|_{2,}/i.test(lastText) && !/Hoàn thành \d+\/\d+ câu/i.test(lastText);
  if (isQuestion) {
    // Dang lam test: AN TOAN BO nut chon so cau de tranh hoc vien bam nham lam hong bai test!
    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu vua hoan thanh vong luyen tap
  const isCompleted = /Hoàn thành \d+\/\d+ câu/i.test(lastText);
  if (isCompleted) {
    const chip3 = document.createElement("button");
    chip3.type = "button";
    chip3.className = "chip";
    chip3.setAttribute("data-send", "3");
    chip3.innerText = "Luyện tiếp 3 câu";
    container.appendChild(chip3);

    const chip5 = document.createElement("button");
    chip5.type = "button";
    chip5.className = "chip";
    chip5.setAttribute("data-send", "5");
    chip5.innerText = "Luyện tiếp 5 câu";
    container.appendChild(chip5);

    updateQuickChipsVisibility();
    return;
  }

  // Kiem tra neu AI vua giai nghia xong tu vung (xuat hien dong [NEXT] Nhap so cau de luyen)
  const hasNextTestPrompt = /\[NEXT\]\s*Nhập số câu|số câu để luyện/i.test(lastText);
  if (hasNextTestPrompt) {
    const chip3 = document.createElement("button");
    chip3.type = "button";
    chip3.className = "chip";
    chip3.setAttribute("data-send", "3");
    chip3.innerText = "3 câu luyện";
    container.appendChild(chip3);

    const chip5 = document.createElement("button");
    chip5.type = "button";
    chip5.className = "chip";
    chip5.setAttribute("data-send", "5");
    chip5.innerText = "5 câu luyện";
    container.appendChild(chip5);

    const chip10 = document.createElement("button");
    chip10.type = "button";
    chip10.className = "chip";
    chip10.setAttribute("data-send", "10");
    chip10.innerText = "10 câu";
    container.appendChild(chip10);

    updateQuickChipsVisibility();
    return;
  }

  updateQuickChipsVisibility();
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
    if (!cachedEnVoice) refreshEnglishVoice();
    if (cachedEnVoice) {
      utterance.voice = cachedEnVoice;
    } else {
      const voices = window.speechSynthesis.getVoices();
      const enVoice = voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.default)) ||
                      voices.find(v => v.lang.startsWith("en"));
      if (enVoice) utterance.voice = enVoice;
    }

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

  // Haptic feedback on copy
  if (copied) {
    triggerHaptic(35);
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
          triggerHaptic(20);
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
    updateContextChips(text);

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

// Check if last message was an active test question waiting for an answer
function isQuestionPending() {
  if (!state.conversation || state.conversation.length === 0) return false;
  const lastAssistant = [...state.conversation].reverse().find(m => m.role === "assistant");
  if (!lastAssistant || !lastAssistant.text) return false;
  const txt = lastAssistant.text;
  return /Câu\s+\d+\/\d+|\[D[1-3]\]|_{2,}/i.test(txt) && !/Hoàn thành \d+\/\d+ câu/i.test(txt);
}

// Send Message Handler
async function handleSendMessage(msgText) {
  let text = (msgText || messageInput.value).trim();
  if (!text) return;

  // Tu dong them dau '.' khi nguoi hoc nhap mot tu don de hoc (vi du: 'urge' -> '.urge')
  // Khong them dau '.' neu la lenh (.s, .g, .help, #qtu), so cau (3, 5), dap an trac nghiem (A, B, C, D),
  // hoac khi he thong dang cho tra loi mot cau hoi luyen tap.
  const isCommandOrNumber = /^[.#]/.test(text) || /^\d+$/.test(text);
  const isChoiceOption = /^[a-dA-D]$/.test(text) && document.querySelectorAll(".btn-bubble-choice").length > 0;
  const isSingleWord = /^[A-Za-z]{2,30}$/.test(text);

  if (!isCommandOrNumber && !isChoiceOption && isSingleWord && !isQuestionPending()) {
    text = "." + text.toLowerCase();
  }

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

function resetVaultMobileView() {
  if (vaultLayout) vaultLayout.classList.remove("show-preview");
  if (vaultBackBtn) vaultBackBtn.style.display = "none";
}

// Vault Explorer
async function loadVaultFiles(subpath = "") {
  resetVaultMobileView();
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

  // Hien thi preview va nut quay lai danh sach tren giao dien mobile
  if (vaultLayout) vaultLayout.classList.add("show-preview");
  if (vaultBackBtn) vaultBackBtn.style.display = "inline-flex";

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
    // Bo qua neu nguoi hoc dang gõ bo go tieng Viet (IME Composition)
    if (e.isComposing || e.keyCode === 229) return;
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
    updateDynamicChoices([]);
    updateContextChips("");
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
  resetVaultMobileView();
  vaultModal.classList.remove("hidden");
  loadVaultFiles();
};

if (vaultBackBtn) {
  vaultBackBtn.onclick = () => {
    resetVaultMobileView();
  };
}

closeVaultBtn.onclick = () => {
  vaultModal.classList.add("hidden");
  resetVaultMobileView();
};
refreshVaultBtn.onclick = () => loadVaultFiles();

vaultSearchInput.oninput = async (e) => {
  const q = e.target.value.trim();
  if (!q) {
    loadVaultFiles();
    return;
  }
  resetVaultMobileView();
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
    resetVaultMobileView();
    messageInput.focus();
  }
};

// Close modal on click outside
window.onclick = (e) => {
  if (e.target === settingsModal) settingsModal.classList.add("hidden");
  if (e.target === vaultModal) {
    vaultModal.classList.add("hidden");
    resetVaultMobileView();
  }
};

// PWA Install Prompt Handler
let deferredPrompt = null;
let swRegisterError = null;
const installPwaBtn = document.getElementById("installPwaBtn");

// Đang chạy trong chế độ app rời => đã cài, không cần hiện nút nữa
const isStandaloneApp =
  (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
  window.navigator.standalone === true;

function pwaPort() {
  return location.port || (location.protocol === "https:" ? "443" : "80");
}

// Lý do cụ thể khiến Chrome chưa bắn beforeinstallprompt
function pwaBlockReason() {
  if (!window.isSecureContext) {
    return (
      "[X] Chrome chỉ cho cài PWA trên origin an toàn (HTTPS hoặc localhost).\n\n" +
      "Địa chỉ đang mở: " + location.origin + "\n\n" +
      "Cách 1 - mở ngay trên máy đang chạy server:\n" +
      "  http://localhost:" + pwaPort() + "\n\n" +
      "Cách 2 - bật HTTPS cục bộ (cài CA một lần, dùng được mọi thiết bị):\n" +
      "  bash app/run.sh gen-cert\n" +
      "  bash app/run.sh tls\n\n" +
      "Cách 3 - cho Chrome tin origin này:\n" +
      "  chrome://flags/#unsafely-treat-insecure-origin-as-secure\n" +
      "  thêm " + location.origin + " -> Enabled -> Relaunch"
    );
  }
  if (!("serviceWorker" in navigator)) {
    return "[X] Trình duyệt này không hỗ trợ Service Worker nên không cài được PWA. Hãy mở bằng Chrome, không dùng trình duyệt trong ứng dụng khác.";
  }
  if (swRegisterError) {
    // Lỗi cert nghĩa là trang đã được mở bằng cách bỏ qua cảnh báo bảo mật:
    // Chrome vẫn hiện nội dung nhưng từ chối đăng ký Service Worker.
    if (/ssl|certificate|cert/i.test(swRegisterError)) {
      return (
        "[X] Chrome chưa tin chứng chỉ của " + location.host + " nên chặn Service Worker.\n\n" +
        "Chi tiết: " + swRegisterError + "\n\n" +
        "Bạn đang xem trang này nhờ bấm 'Tiếp tục truy cập' ở cảnh báo bảo mật. Chrome không\n" +
        "bao giờ cho cài PWA trên origin đã bỏ qua cảnh báo, kể cả khi trang hiển thị bình thường.\n\n" +
        "Kiểm tra theo thứ tự:\n" +
        "  1. Cài đặt -> Bảo mật -> Thông tin xác thực -> Thông tin xác thực đáng tin cậy -> tab\n" +
        "     NGƯỜI DÙNG: phải thấy 'English Tutor Local CA'. Không thấy nghĩa là chưa cài,\n" +
        "     hoặc đã cài nhầm vào mục 'Chứng chỉ người dùng VPN và ứng dụng'.\n" +
        "  2. Cài đúng mục: Cài chứng chỉ -> Chứng chỉ CA -> chọn /sdcard/Download/english-ca.crt\n" +
        "  3. Đóng hẳn Chrome (vuốt khỏi danh sách ứng dụng) rồi mở lại - trust store chỉ được\n" +
        "     đọc lại khi Chrome khởi động.\n" +
        "  4. Xoá quyết định bỏ qua cũ: Menu 3 chấm -> Cài đặt trang -> Xoá & đặt lại.\n" +
        "  5. Mở lại https://" + location.host + " - không được còn cảnh báo bảo mật nào."
      );
    }
    return (
      "[X] Service Worker đăng ký thất bại nên Chrome coi trang là chưa cài được.\n\n" +
      "Chi tiết: " + swRegisterError + "\n\n" +
      "Hãy tải lại trang một lần rồi thử lại."
    );
  }
  // Tới đây mọi tiêu chí kỹ thuật đều đạt: HTTPS tin cậy, Service Worker chạy.
  // Chrome không cho biết vì sao im lặng, nên liệt kê đúng hai khả năng thật.
  const diag = [
    "secureContext=" + window.isSecureContext,
    "serviceWorker=" + (navigator.serviceWorker && navigator.serviceWorker.controller ? "đang điều khiển" : "chưa điều khiển trang"),
    "displayMode=" + (window.matchMedia("(display-mode: standalone)").matches ? "standalone" : "browser"),
  ].join(", ");

  return (
    "[~] Trang đã đạt mọi tiêu chí cài đặt nhưng Chrome chưa gửi lời mời tự động.\n\n" +
    "Khả năng 1 - app đã được cài rồi:\n" +
    "  Chrome không mời cài lại. Kiểm tra màn hình chính, nếu đã có icon 'English AI'\n" +
    "  thì mở từ icon đó là xong.\n\n" +
    "Khả năng 2 - Chrome chưa chủ động mời:\n" +
    "  Cài tay vẫn được và cho kết quả tương đương:\n" +
    "  Menu 3 chấm của Chrome -> 'Cài đặt ứng dụng' (hoặc 'Thêm vào Màn hình chính').\n\n" +
    "Nếu Service Worker vừa mới đăng ký lần đầu, tải lại trang một lần rồi thử lại.\n\n" +
    "Trạng thái: " + diag
  );
}

// Luôn hiện nút khi chưa cài, chỉ đổi trạng thái sáng/mờ theo mức sẵn sàng
function refreshInstallBtn() {
  if (!installPwaBtn) return;

  if (isStandaloneApp) {
    installPwaBtn.classList.add("pwa-hidden");
    return;
  }

  installPwaBtn.classList.remove("pwa-hidden");

  const ready = !!deferredPrompt;
  installPwaBtn.classList.toggle("pwa-blocked", !ready);
  installPwaBtn.title = ready
    ? "Cài đặt App về màn hình chính"
    : "Chưa cài tự động được - bấm để xem lý do và cách khắc phục";

  if (!ready) {
    console.warn("[PWA] Chưa sẵn sàng cài:\n" + pwaBlockReason());
  }
}

window.addEventListener("beforeinstallprompt", (e) => {
  e.preventDefault();
  deferredPrompt = e;
  refreshInstallBtn();
});

if (installPwaBtn) {
  installPwaBtn.onclick = async () => {
    if (!deferredPrompt) {
      alert(pwaBlockReason());
      return;
    }
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    deferredPrompt = null;
    if (outcome === "accepted") {
      installPwaBtn.classList.add("pwa-hidden");
      return;
    }
    refreshInstallBtn();
    alert("Gợi ý: Do server chạy cục bộ trên Termux, Google không đóng gói WebAPK tự động được. Bấm Menu 3 chấm của Chrome -> 'Tạo lối tắt' (hoặc 'Thêm vào màn hình chính') là vẫn ghim được icon ra màn hình chính.");
  };
}

window.addEventListener("appinstalled", () => {
  deferredPrompt = null;
  if (installPwaBtn) installPwaBtn.classList.add("pwa-hidden");
});

// Register PWA Service Worker
if ('serviceWorker' in navigator) {
  let swRefreshing = false;
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!swRefreshing) {
      swRefreshing = true;
      console.log('[PWA] Service Worker cập nhật phiên bản mới, đang tải lại...');
      window.location.reload();
    }
  });

  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js')
      .then((reg) => {
        // Chu dong kiem tra ban moi moi khi mo app
        reg.update();
        reg.onupdatefound = () => {
          const installingWorker = reg.installing;
          if (installingWorker) {
            installingWorker.onstatechange = () => {
              if (installingWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('[PWA] Đã cài đặt xong phiên bản mới.');
              }
            };
          }
        };
      })
      .catch((err) => {
        swRegisterError = (err && err.message) ? err.message : String(err);
        console.warn('[PWA] Service Worker registration failed:', err);
        refreshInstallBtn();
      });
  });
} else {
  swRegisterError = null;
}

// Hiện nút ngay lập tức, không chờ beforeinstallprompt.
// Khi môi trường vẫn còn hợp lệ, chờ một nhịp ngắn cho Chrome bắn sự kiện
// trước khi chuyển nút sang trạng thái mờ, tránh nhấp nháy vô cớ.
if (installPwaBtn && !isStandaloneApp) {
  installPwaBtn.classList.remove("pwa-hidden");
}
if (window.isSecureContext && "serviceWorker" in navigator) {
  setTimeout(() => {
    if (!deferredPrompt) refreshInstallBtn();
  }, 3000);
} else {
  refreshInstallBtn();
}

// Live-Reload via Server-Sent Events (SSE) from Golang engine
(function initLiveReload() {
  if (!("EventSource" in window)) return;
  let sse = null;
  function connect() {
    sse = new EventSource("/api/live-reload");
    sse.onmessage = (e) => {
      if (e.data === "reload") {
        console.log("[LiveReload] File thay đổi, tự động tải lại trang...");
        location.reload();
      }
    };
    sse.onerror = () => {
      sse.close();
      setTimeout(connect, 3000);
    };
  }
  connect();
})();

// Khoi tao chip ngu canh ban dau (hien thi tu mau de hoc thu)
updateContextChips("");

// Pull-to-Refresh Gesture Handling cho PWA va trinh duyet di dong
(function initPullToRefresh() {
  const ptr = document.getElementById("ptrIndicator");
  const spinner = document.getElementById("ptrSpinner");
  const label = document.getElementById("ptrLabel");
  if (!ptr || !spinner || !label || !chatViewport) return;

  let startY = 0;
  let isPulling = false;
  let hasTriggeredHaptic = false;
  const PTR_THRESHOLD = 55;
  const PTR_MAX = 80;

  chatViewport.addEventListener("touchstart", (e) => {
    if (chatViewport.scrollTop <= 0) {
      startY = e.touches[0].pageY;
      isPulling = true;
      hasTriggeredHaptic = false;
    } else {
      isPulling = false;
    }
  }, { passive: true });

  chatViewport.addEventListener("touchmove", (e) => {
    if (!isPulling || chatViewport.scrollTop > 0) return;
    const currentY = e.touches[0].pageY;
    const diff = currentY - startY;

    if (diff > 0) {
      // Ngan chan trinh duyet mobile cuon ca window hoac giat man hinh
      if (e.cancelable) e.preventDefault();

      // Co giat theo luc keo rubber-band
      const pullHeight = Math.min(diff * 0.4, PTR_MAX);
      ptr.style.height = `${pullHeight}px`;
      ptr.classList.add("visible");

      const rotation = Math.min(pullHeight * 5, 360);
      spinner.style.transform = `rotate(${rotation}deg)`;

      if (pullHeight >= PTR_THRESHOLD) {
        label.innerText = "Thả ra để làm mới";
        if (!hasTriggeredHaptic) {
          triggerHaptic(20);
          hasTriggeredHaptic = true;
        }
      } else {
        label.innerText = "Kéo xuống để làm mới";
        hasTriggeredHaptic = false;
      }
    }
  }, { passive: false });

  chatViewport.addEventListener("touchend", () => {
    if (!isPulling) return;
    isPulling = false;
    const pullHeight = parseFloat(ptr.style.height) || 0;

    if (pullHeight >= PTR_THRESHOLD) {
      ptr.style.height = "38px";
      ptr.classList.add("refreshing");
      label.innerText = "Đang làm mới...";
      triggerHaptic(35);
      setTimeout(() => {
        window.scrollTo(0, 0);
        window.location.reload();
      }, 350);
    } else {
      ptr.style.height = "0px";
      ptr.classList.remove("visible");
      setTimeout(() => {
        spinner.style.transform = "rotate(0deg)";
        label.innerText = "Kéo xuống để làm mới";
      }, 200);
    }
  }, { passive: true });
})();

