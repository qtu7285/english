/**
 * Audio, Speech Synthesis (TTS) & Haptics Module
 */
import { state } from './state.js';

export const VIETNAMESE_REGEX = /[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ]/i;

// Haptic feedback helper for mobile touch
export function triggerHaptic(ms = 25) {
  if (navigator && typeof navigator.vibrate === "function") {
    try { navigator.vibrate(ms); } catch (e) {}
  }
}

// English TTS Voice caching for mobile browsers
export let cachedEnVoice = null;
export function refreshEnglishVoice() {
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

export function stripHtmlAndEntities(str) {
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

export function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function escapeAttr(str) {
  return str.replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

export function makeAudioButton(text) {
  const clean = stripHtmlAndEntities(text)
    .replace(/\[.*?\]/g, "")
    .replace(/[*#`"“”]/g, "")
    .trim();
  if (!clean) return "";
  const attr = escapeAttr(clean);
  return `<button type="button" class="inline-audio-btn" data-text="${attr}" title="Phát âm câu này">🔊</button>`;
}

export function extractEnglishElements(text) {
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

  // 4. Scan lines starting with [EN] for English sentences
  lines.forEach(line => {
    const enMatch = line.match(/^[\s\-\*•]*\[EN\](?::)?\s*(.+)$/i);
    if (enMatch) {
      const cleanEn = enMatch[1].replace(/[*#`"“”]/g, "").trim();
      if (cleanEn && !cleanEn.includes("___") && !VIETNAMESE_REGEX.test(cleanEn) && cleanEn.split(/\s+/).length >= 2) {
        if (!sentences.includes(cleanEn)) sentences.push(cleanEn);
      }
    }
  });

  return { word: targetWord, sentences };
}

export function processLineForAudio(line) {
  if (!line || line.includes("inline-audio-btn") || line.includes("<pre>") || line.includes("<code>")) return line;

  // Do not process audio for status lines, definitions, or control badges
  if (line.includes("badge-vi") || line.includes("badge-next") || line.includes("badge-confirm") || line.includes("badge-ok") || line.includes("badge-error") || line.includes("badge-warn") || line.includes("badge-diff") || line.includes("bubble-divider")) {
    return line;
  }

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
  const quoteMatch = line.match(/(?:^|[\s(])(?:&quot;|["“])([A-Za-z0-9\s,.'’!?\-]{4,})(?:&quot;|["”])(?=[\s),.!?]|$)/);
  if (quoteMatch) {
    const cleanQuote = stripHtmlAndEntities(quoteMatch[1]).replace(/[*#`]/g, "").trim();
    if (cleanQuote && !VIETNAMESE_REGEX.test(cleanQuote) && cleanQuote.split(/\s+/).length >= 2) {
      const btn = makeAudioButton(cleanQuote);
      if (btn) return line.replace(quoteMatch[0], quoteMatch[0] + ' ' + btn);
    }
  }

  // Pattern 4: Line starting with EN flag badge and English sentence (without blank ___)
  const enBadgeMatch = line.match(/^(?:<p>)?[\s\-]*(?:<span class="badge badge-en"[^>]*>.*?<\/span>)\s*([A-Za-z0-9\s,.'’!?\-]{4,})/);
  if (enBadgeMatch) {
    const sent = stripHtmlAndEntities(enBadgeMatch[1]).replace(/[*#`"“”]/g, "").trim();
    if (sent && !sent.includes("___") && !VIETNAMESE_REGEX.test(sent) && sent.split(/\s+/).length >= 2) {
      const btn = makeAudioButton(sent);
      if (btn && !line.includes(btn)) return line + ' ' + btn;
    }
  }

  return line;
}

// Speech Synthesis with Android Chrome fix
export function speakText(explicitText) {
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

  let clean = stripHtmlAndEntities(toSpeak);
  clean = clean.replace(/\([^)]*[àáảãạăắằẳẵặâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ][^)]*\)/gi, "");
  clean = clean
    .replace(/\[.*?\]/g, "")
    .replace(/(_+\s*)+/g, ", ")
    .replace(/[*#`"“”]/g, "")
    .replace(/\s+/g, " ")
    .trim();

  if (!clean) return;

  // Chrome Android audio engine fix
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

// Copy to Clipboard with fallback for HTTP / LAN IP
export async function copyToClipboard(text, btnElement) {
  if (!text) return false;
  const clean = stripHtmlAndEntities(text)
    .replace(/\[.*?\]/g, "")
    .replace(/[*#`]/g, "")
    .trim();
  if (!clean) return false;

  let copied = false;

  if (navigator && navigator.clipboard && typeof navigator.clipboard.writeText === "function") {
    try {
      await navigator.clipboard.writeText(clean);
      copied = true;
    } catch (err) {
      copied = false;
    }
  }

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

  if (copied) {
    triggerHaptic(35);
  }

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
