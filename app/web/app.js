/**
 * English Tutor & Vault AI - Main Application Entry
 * Modularized with Native ES Modules (Zero-Build, Zero-Dependency)
 */

import { state } from './modules/state.js';
import * as dom from './modules/dom.js';
import { syncUserProfileFromServer, fetchQuotaFromServer } from './modules/api.js';
import { bindChatEvents, restoreChatHistory, appendMessage } from './modules/chat.js';
import { updateContextChips } from './modules/chips.js';
import { bindSettingsEvents, updateHeaderModelDisplay } from './modules/settings.js';
import { bindDrawerEvents, closeDrawer } from './modules/drawer.js';
import { bindVaultEvents } from './modules/vault.js';
import { initPWA, initLiveReload, initPullToRefresh } from './modules/pwa.js';

// Purge legacy OAuth keys left in localStorage
["gemini_oauth_token", "oauth_client_id", "oauth_client_secret"].forEach(k => localStorage.removeItem(k));

// Initialize Application
async function initApp() {
  // 1. Bind UI events
  bindChatEvents();
  bindDrawerEvents((cmd) => {
    if (dom.messageInput) dom.messageInput.value = cmd;
    if (dom.chatForm) dom.chatForm.dispatchEvent(new Event("submit"));
  });
  bindSettingsEvents(() => {
    appendMessage("assistant", `[OK] Đã lưu cài đặt cho người học #${state.username} (User: ${state.avatarUser}, AI: ${state.avatarAI}, Từ mục tiêu: ${state.avatarTarget}, Avatar chat: ${state.showChatAvatars ? "Bật" : "Tắt"}).`);
  }, closeDrawer);
  bindVaultEvents();

  // 2. Setup PWA, LiveReload, Gestures
  initPWA();
  initLiveReload();
  initPullToRefresh();

  // 3. Restore chat history or show initial prompt
  restoreChatHistory();
  if (!state.conversation || state.conversation.length === 0) {
    updateContextChips("");
  }

  // 4. Background synchronization with server
  try {
    await syncUserProfileFromServer();
    await fetchQuotaFromServer();
    updateHeaderModelDisplay();
  } catch (e) {
    console.warn("[Init] Đồng bộ dữ liệu nền:", e);
  }
}

// Global click outside to close modals
window.onclick = (e) => {
  if (dom.settingsModal && e.target === dom.settingsModal) {
    dom.settingsModal.classList.add("hidden");
  }
  if (dom.vaultModal && e.target === dom.vaultModal) {
    dom.vaultModal.classList.add("hidden");
  }
};

initApp();
