/**
 * Chat & Messaging Module
 */
import { state } from './state.js';
import * as dom from './dom.js';
import { triggerHaptic, speakText, copyToClipboard, extractEnglishElements, escapeHtml } from './audio.js';
import { renderMarkdown } from './markdown.js';
import { extractChoiceOptions, updateDynamicChoices, updateContextChips } from './chips.js';
import { sendChatMessageToAPI, fetchQuotaFromServer, syncUserProfileFromServer } from './api.js';
import { updateHeaderModelDisplay } from './settings.js';
import { closeDrawer } from './drawer.js';

export function isQuestionPending() {
  if (!state.conversation || state.conversation.length === 0) return false;
  const lastAssistant = [...state.conversation].reverse().find(m => m.role === "assistant");
  if (!lastAssistant || !lastAssistant.text) return false;
  const txt = lastAssistant.text;
  return /Câu\s+\d+\/\d+|\[D[1-3]\]|_{2,}/i.test(txt) && !/Hoàn thành \d+\/\d+ câu/i.test(txt);
}

export function saveChatHistory() {
  try {
    localStorage.setItem("chat_conversation", JSON.stringify(state.conversation.slice(-30)));
  } catch (e) {
    console.warn("[Chat] Không thể lưu lịch sử chat:", e);
  }
}

export function restoreChatHistory() {
  try {
    const saved = localStorage.getItem("chat_conversation");
    if (!saved) return;
    const history = JSON.parse(saved);
    if (!Array.isArray(history) || history.length === 0) return;

    state.conversation = history;
    if (dom.chatMessages) {
      dom.chatMessages.innerHTML = "";
      history.forEach(msg => {
        appendMessage(msg.role, msg.text, msg.tool_logs || [], msg.metadata || {});
      });
    }
  } catch (e) {
    console.warn("[Chat] Không thể khôi phục lịch sử chat:", e);
  }
}

export function startNewChat() {
  triggerHaptic(20);
  closeDrawer();
  if (dom.chatMessages) {
    dom.chatMessages.innerHTML = `
      <div class="message-row assistant">
        <div class="avatar" id="initialAiAvatar">${state.avatarAI || "🤖"}</div>
        <div class="bubble">
          <div class="bubble-content">
            <p style="font-weight: 700; color: #38bdf8; line-height: 1.6; font-size: 15px;">
              🔥 Đam mê Anh luyện.<br>
              ⏱️ Không sót 1 phút.<br>
              📖 Không sót 1 từ.<br>
              💎 Điêu luyện rộng sâu.
            </p>
          </div>
        </div>
      </div>
    `;
  }
  state.conversation = [];
  try { localStorage.removeItem("chat_conversation"); } catch (e) {}
  updateDynamicChoices([]);
  updateContextChips("");
  if (dom.messageInput) {
    dom.messageInput.value = "";
    dom.messageInput.focus();
  }
}

export function createLoadingIndicator() {
  const row = document.createElement("div");
  row.className = "message-row assistant loading-row";

  const avatar = document.createElement("div");
  avatar.className = "avatar avatar-thinking";
  avatar.innerText = state.avatarAI || "🤖";

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
  if (dom.chatMessages) dom.chatMessages.appendChild(row);
  if (dom.chatViewport) dom.chatViewport.scrollTop = dom.chatViewport.scrollHeight;

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

export function appendMessage(role, text, toolLogs = [], metadata = {}) {
  const row = document.createElement("div");
  row.className = `message-row ${role}`;

  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.innerText = role === "user" ? (state.avatarUser || "🧑‍🎓") : (state.avatarAI || "🤖");

  const bubble = document.createElement("div");
  bubble.className = "bubble";

  const content = document.createElement("div");
  content.className = "bubble-content";

  if (role === "user") {
    const headwordMatch = text.match(/^\.([A-Za-z][A-Za-z\s\-]{1,29})$/);
    const controlCmds = ["s", "g", "help", "cd", "m", "q", "p", "t"];
    if (headwordMatch && !controlCmds.includes(headwordMatch[1].toLowerCase())) {
      const targetEmoji = state.avatarTarget || "🎯";
      const word = headwordMatch[1];
      content.innerHTML = `<span class="target-headword"><span class="target-icon" title="Từ mục tiêu">${targetEmoji}</span> <strong>${escapeHtml(word)}</strong></span>`;
    } else {
      content.innerHTML = renderMarkdown(text);
    }
  } else {
    content.innerHTML = renderMarkdown(text);
  }

  bubble.appendChild(content);

  // Assistant action bar
  if (role === "assistant") {
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
    updateContextChips(text, metadata.type || "");

    const extracted = extractEnglishElements(text);
    const targetWord = metadata.target_word || extracted.word;
    const mainSentence = metadata.audio_sentence || (extracted.sentences.length > 0 ? extracted.sentences[0] : "");

    if (targetWord || mainSentence || metadata.retryText) {
      const actions = document.createElement("div");
      actions.className = "bubble-actions";

      if (targetWord) {
        const wordBtn = document.createElement("button");
        wordBtn.type = "button";
        wordBtn.className = "btn-action speak-btn";
        wordBtn.setAttribute("data-text", targetWord);
        wordBtn.innerHTML = `🔊 Từ: <strong>${escapeHtml(targetWord)}</strong>`;
        actions.appendChild(wordBtn);
      }

      if (mainSentence) {
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

      if (metadata.retryText) {
        const retryBtn = document.createElement("button");
        retryBtn.type = "button";
        retryBtn.className = "btn-action retry-btn";
        retryBtn.innerHTML = `🔄 Thử lại`;
        retryBtn.onclick = () => {
          triggerHaptic(20);
          row.remove();
          handleSendMessage(metadata.retryText, true);
        };
        actions.appendChild(retryBtn);
      }

      bubble.appendChild(actions);
    }
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  if (dom.chatMessages) dom.chatMessages.appendChild(row);
  if (dom.chatViewport) dom.chatViewport.scrollTop = dom.chatViewport.scrollHeight;

  return row;
}

export async function handleSendMessage(msgText, isRetry = false) {
  let text = (msgText || (dom.messageInput ? dom.messageInput.value : "")).trim();
  if (!text) return;

  const isCommandOrNumber = /^[.#]/.test(text) || /^\d+$/.test(text);
  const isChoiceOption = /^[a-dA-D]$/.test(text) && document.querySelectorAll(".btn-bubble-choice").length > 0;
  const isSingleWord = /^[A-Za-z]{2,30}$/.test(text);

  if (!isCommandOrNumber && !isChoiceOption && isSingleWord && !isQuestionPending()) {
    text = "." + text.toLowerCase();
  }

  if (dom.messageInput) {
    dom.messageInput.value = "";
    dom.messageInput.style.height = "auto";
  }
  updateDynamicChoices([]);

  const usernameMatch = text.match(/^#([a-z0-9][a-z0-9_-]*)$/i);
  if (usernameMatch) {
    const newU = usernameMatch[1].toLowerCase();
    state.username = newU;
    localStorage.setItem("username", newU);
    syncUserProfileFromServer(newU);
  }

  const priorHistory = state.conversation.slice(-10);

  if (!isRetry) {
    appendMessage("user", text);
  }

  const loadingIndicator = createLoadingIndicator();
  if (dom.sendBtn) dom.sendBtn.disabled = true;

  try {
    const res = await sendChatMessageToAPI({
      engine: state.engine,
      message: text,
      history: priorHistory,
      apiKey: state.apiKey,
      model: state.model,
      enableVaultTools: state.enableVaultTools
    });

    const data = await res.json();
    loadingIndicator.remove();

    if (data.error) {
      appendMessage("assistant", `[X] Lỗi: ${data.error}`, [], { retryText: text });
    } else {
      state.conversation.push({ role: "user", text });
      state.conversation.push({ role: "assistant", text: data.text, metadata: data });
      saveChatHistory();
      appendMessage("assistant", data.text, data.tool_logs, data);
      fetchQuotaFromServer().then(() => updateHeaderModelDisplay());

      const extracted = extractEnglishElements(data.text);
      if (extracted.sentences && extracted.sentences.length > 0) {
        copyToClipboard(extracted.sentences[0]);
      }
    }
  } catch (err) {
    loadingIndicator.remove();
    appendMessage("assistant", `[X] Lỗi kết nối: ${err.message}`, [], { retryText: text });
  } finally {
    if (dom.sendBtn) dom.sendBtn.disabled = false;
  }
}

export function bindChatEvents() {
  if (dom.chatMessages) {
    dom.chatMessages.addEventListener("click", (e) => {
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
  }

  if (dom.chatForm) {
    dom.chatForm.onsubmit = (e) => {
      e.preventDefault();
      handleSendMessage();
    };
  }

  if (dom.messageInput) {
    dom.messageInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter" && !e.shiftKey) {
        if (e.isComposing || e.keyCode === 229) return;
        e.preventDefault();
        handleSendMessage();
      }
    });

    dom.messageInput.addEventListener("input", () => {
      dom.messageInput.style.height = "auto";
      dom.messageInput.style.height = Math.min(dom.messageInput.scrollHeight, 120) + "px";
    });
  }

  if (dom.quickChipsBar) {
    dom.quickChipsBar.addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (chip) {
        const sendVal = chip.getAttribute("data-send");
        if (sendVal) {
          handleSendMessage(sendVal);
        }
      }
    });
  }

  if (dom.newChatBtn) dom.newChatBtn.onclick = startNewChat;
  if (dom.drawerNewChatBtn) dom.drawerNewChatBtn.onclick = startNewChat;
}
