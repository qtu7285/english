/**
 * English Tutor & Vault AI - Main Application Entry
 * Modularized with Native ES Modules (Zero-Build, Zero-Dependency)
 */

import { state } from './modules/state.js';
import * as dom from './modules/dom.js';
import { syncUserProfileFromServer, fetchQuotaFromServer } from './modules/api.js';
import { bindChatEvents, restoreChatHistory, appendMessage } from './modules/chat.js';
import { updateContextChips } from './modules/chips.js';
import { bindSettingsEvents, updateHeaderModelDisplay, openSettingsModal, closeSettingsModal } from './modules/settings.js';
import { bindDrawerEvents, closeDrawer } from './modules/drawer.js';
import { bindVaultEvents, openVaultModal, closeVaultModal } from './modules/vault.js';
import { initPWA, initLiveReload, initPullToRefresh } from './modules/pwa.js';
import { checkAuthSession, bindAuthEvents, openLoginModal, closeLoginModal, applyRoleUI } from './modules/auth.js';

// Purge legacy OAuth keys left in localStorage
["gemini_oauth_token", "oauth_client_id", "oauth_client_secret"].forEach(k => localStorage.removeItem(k));

// Route URL Hash to Modals / Views
export function handleHashRoute() {
  const hash = window.location.hash;

  if (hash === "#login") {
    openLoginModal(false);
  } else {
    closeLoginModal(false);
  }

  if (hash.startsWith("#settings")) {
    let tab = "tab-emoji";
    if (hash === "#settings/ai") tab = "tab-ai";
    else if (hash === "#settings/voice") tab = "tab-voice";
    openSettingsModal(tab, closeDrawer, false);
  } else {
    closeSettingsModal(false);
  }

  if (hash === "#vault") {
    openVaultModal(false);
  } else {
    closeVaultModal(false);
  }
}

// Initialize Application
async function initApp() {
  // 1. Bind UI & Auth events
  bindChatEvents();
  bindDrawerEvents((cmd) => {
    if (dom.messageInput) dom.messageInput.value = cmd;
    if (dom.chatForm) dom.chatForm.dispatchEvent(new Event("submit"));
  });
  bindSettingsEvents(() => {
    appendMessage("assistant", `[OK] Đã lưu cài đặt cho người học #${state.username} (User: ${state.avatarUser}, AI: ${state.avatarAI}, Từ mục tiêu: ${state.avatarTarget}, Avatar chat: ${state.showChatAvatars ? "Bật" : "Tắt"}).`);
  }, closeDrawer);
  bindVaultEvents();

  bindAuthEvents(async (user) => {
    await syncUserProfileFromServer();
    await fetchQuotaFromServer();
    updateHeaderModelDisplay();
    appendMessage("assistant", `[OK] Đã đăng nhập người học #${user.username} (${user.role === 'admin' ? 'Quản trị viên' : 'Người học'}).`);
  });

  // 2. Setup PWA, LiveReload, Gestures & Hash Routing
  initPWA();
  initLiveReload();
  initPullToRefresh();
  window.addEventListener("hashchange", handleHashRoute);
  handleHashRoute();

  // 3. Check Session & Synchronize with server
  try {
    await checkAuthSession();
    await syncUserProfileFromServer();
    await fetchQuotaFromServer();
    updateHeaderModelDisplay();
  } catch (e) {
    console.warn("[Init] Đồng bộ dữ liệu nền:", e);
  }

  // 4. Restore chat history or show initial prompt
  restoreChatHistory();
  if (!state.conversation || state.conversation.length === 0) {
    updateContextChips("");
  }
}

// Global click outside to close modals
window.onclick = (e) => {
  const loginModal = document.getElementById("loginModal");
  if (loginModal && e.target === loginModal) {
    closeLoginModal(true);
  }
  if (dom.settingsModal && e.target === dom.settingsModal) {
    closeSettingsModal(true);
  }
  if (dom.vaultModal && e.target === dom.vaultModal) {
    closeVaultModal(true);
  }
};

initApp();
