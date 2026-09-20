/**
 * Settings & Customization Module
 */
import { state, MODEL_DISPLAY_NAMES } from './state.js';
import * as dom from './dom.js';
import { triggerHaptic } from './audio.js';
import { fetchSavedAccounts, switchSavedAccount, fetchAdminUsersList, updateUserPermission, saveUserProfileToServer, fetchQuotaFromServer } from './api.js';

export function applyFontSize(size) {
  if (size) {
    document.documentElement.style.setProperty("--bubble-font-size", size);
  }
}

export function updateExistingAvatarsInChat() {
  if (dom.initialAiAvatar) {
    dom.initialAiAvatar.innerText = state.avatarAI || "🤖";
  }
  document.querySelectorAll(".message-row.assistant:not(.loading-row) .avatar").forEach(av => {
    av.innerText = state.avatarAI || "🤖";
  });
  document.querySelectorAll(".message-row.user .avatar").forEach(av => {
    av.innerText = state.avatarUser || "🧑‍🎓";
  });
  if (dom.drawerUserAvatar) {
    dom.drawerUserAvatar.innerText = state.avatarUser || "🧑‍🎓";
  }
  if (dom.drawerUserName) {
    dom.drawerUserName.innerText = state.username || "qtu";
  }
}

export function applyChatAvatarsVisibility() {
  if (!dom.chatMessages) return;
  if (state.showChatAvatars) {
    dom.chatMessages.classList.remove("hide-avatars");
  } else {
    dom.chatMessages.classList.add("hide-avatars");
  }
}

export function updateHeaderModelDisplay() {
  if (!dom.headerModelSelect) return;
  const curModel = state.model || "gemini-3.6-flash";
  const baseName = MODEL_DISPLAY_NAMES[curModel] || curModel;

  const exists = Array.from(dom.headerModelSelect.options).some(opt => opt.value === curModel);
  if (exists) {
    dom.headerModelSelect.value = curModel;
  } else {
    dom.headerModelSelect.value = "gemini-3.6-flash";
  }

  if (dom.headerModelLabel) {
    if (state.quota && state.quota.gemini_5h) {
      dom.headerModelLabel.innerText = `${baseName} (${state.quota.gemini_5h})`;
    } else {
      dom.headerModelLabel.innerText = baseName;
    }
  }

  const q5h = (state.quota && state.quota.gemini_5h) ? state.quota.gemini_5h : "";
  const qWeek = (state.quota && state.quota.gemini_week) ? state.quota.gemini_week : "";
  const suffix = (q5h && qWeek) ? ` (5h: ${q5h} | Tuần: ${qWeek})` : (q5h ? ` (${q5h})` : "");
  Array.from(dom.headerModelSelect.options).forEach(opt => {
    const b = MODEL_DISPLAY_NAMES[opt.value] || opt.value;
    opt.text = `${b}${suffix}`;
  });

  if (dom.headerModelIndicator) {
    if (state.quota && state.quota.gemini_5h) {
      const p = parseInt(state.quota.gemini_5h, 10);
      if (!isNaN(p)) {
        if (p > 50) {
          dom.headerModelIndicator.style.backgroundColor = "var(--accent-ok)";
        } else if (p >= 20) {
          dom.headerModelIndicator.style.backgroundColor = "#f59e0b";
        } else {
          dom.headerModelIndicator.style.backgroundColor = "var(--accent-err)";
        }
      }
    } else {
      dom.headerModelIndicator.style.backgroundColor = "var(--accent-ok)";
    }
  }
}

export function syncHeaderModelSelect() {
  updateHeaderModelDisplay();
}

export function updateEngineUI() {
  const isAntigravity = dom.engineSelect.value === "antigravity";
  const isAdmin = state.role === "admin" || state.username === "qtu";

  if (isAntigravity) {
    dom.engineHint.innerText = "Sử dụng hệ thống sẵn có, không cần cài đặt thêm.";
    if (dom.apiKeyGroup) dom.apiKeyGroup.style.display = "none";
    if (dom.antigravityAccountsGroup) {
      dom.antigravityAccountsGroup.style.display = isAdmin ? "block" : "none";
      if (isAdmin) loadSavedAccountsList();
    }
  } else {
    dom.engineHint.innerText = "Sử dụng Gemini API Key của bạn để học.";
    if (dom.apiKeyGroup) dom.apiKeyGroup.style.display = "block";
    dom.apiKeyInput.placeholder = "Dán API Key của bạn tại đây...";
    if (dom.antigravityAccountsGroup) {
      dom.antigravityAccountsGroup.style.display = "none";
    }
  }
}

export async function loadSavedAccountsList(onAccountSwitched) {
  if (!dom.savedAccountsList) return;
  dom.savedAccountsList.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">Đang tải danh sách tài khoản...</span>';
  try {
    const accounts = await fetchSavedAccounts();
    if (accounts.length === 0) {
      dom.savedAccountsList.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">Chưa có tài khoản nào được lưu.</span>';
      return;
    }
    dom.savedAccountsList.innerHTML = "";
    accounts.forEach(acc => {
      const row = document.createElement("div");
      row.className = `account-row ${acc.is_active ? 'active' : ''}`;
      row.innerHTML = `
        <div class="account-email">
          <span>📧</span>
          <span>${acc.email}</span>
          ${acc.is_active ? '<span class="account-badge-active">Đang dùng</span>' : ''}
        </div>
        ${!acc.is_active ? `<button type="button" class="account-switch-btn" data-email="${acc.email}">Kích hoạt</button>` : ''}
      `;
      const btn = row.querySelector(".account-switch-btn");
      if (btn) {
        btn.addEventListener("click", async () => {
          triggerHaptic(25);
          btn.disabled = true;
          btn.innerText = "Đang đổi...";
          try {
            const swData = await switchSavedAccount(acc.email);
            if (swData.success) {
              if (typeof onAccountSwitched === "function") {
                onAccountSwitched(acc.email);
              }
              loadSavedAccountsList(onAccountSwitched);
              fetchQuotaFromServer().then(() => updateHeaderModelDisplay());
            }
          } catch (e) {
            console.warn("Lỗi chuyển tài khoản:", e);
          }
        });
      }
      dom.savedAccountsList.appendChild(row);
    });
  } catch (e) {
    dom.savedAccountsList.innerHTML = '<span style="color: var(--accent-err); font-size: 11px;">Lỗi tải dữ liệu tài khoản.</span>';
  }
}

export async function loadAdminUsersList() {
  if (!dom.adminUsersList) return;
  dom.adminUsersList.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">Đang tải danh sách người học...</span>';
  try {
    const users = await fetchAdminUsersList();
    const otherUsers = users.filter(u => u.username !== "qtu");
    if (otherUsers.length === 0) {
      dom.adminUsersList.innerHTML = '<span style="color: var(--text-muted); font-size: 11px;">Chưa có người học nào khác trong hệ thống.</span>';
      return;
    }
    dom.adminUsersList.innerHTML = "";
    otherUsers.forEach(u => {
      const row = document.createElement("div");
      row.className = "admin-user-row";
      const isAllowed = !!(u.can_view_ai_info);
      row.innerHTML = `
        <div class="admin-user-info">
          <span>${u.avatar_user || "🧑‍🎓"}</span>
          <span class="admin-user-name">#${u.username}</span>
          <span class="admin-user-role-badge ${u.role === 'admin' ? 'admin' : ''}">${u.role === 'admin' ? 'Admin' : 'Người học'}</span>
        </div>
        <label style="display: flex; align-items: center; gap: 6px; font-size: 11px; cursor: pointer;">
          <input type="checkbox" class="user-ai-perm-check" data-user="${u.username}" ${isAllowed ? 'checked' : ''}>
          <span>Xem thông tin AI</span>
        </label>
      `;
      const chk = row.querySelector(".user-ai-perm-check");
      chk.addEventListener("change", async () => {
        triggerHaptic(20);
        await updateUserPermission(u, chk.checked);
      });
      dom.adminUsersList.appendChild(row);
    });
  } catch (e) {
    dom.adminUsersList.innerHTML = '<span style="color: var(--accent-err); font-size: 11px;">Lỗi kết nối khi tải danh sách.</span>';
  }
}

export function openSettingsModal(targetTab = null, closeDrawerFn = null, updateHash = true) {
  triggerHaptic(15);
  if (typeof closeDrawerFn === "function") closeDrawerFn();
  if (dom.usernameInput) dom.usernameInput.value = state.username || "qtu";

  // Đồng bộ picker Avatar User
  if (dom.userAvatarPicker) {
    let matchedUser = false;
    dom.userAvatarPicker.querySelectorAll(".avatar-opt").forEach(b => {
      if (b.getAttribute("data-avatar") === state.avatarUser) {
        b.classList.add("selected");
        matchedUser = true;
      } else {
        b.classList.remove("selected");
      }
    });
    if (dom.customUserAvatarInput) {
      dom.customUserAvatarInput.value = matchedUser ? "" : (state.avatarUser || "");
    }
  }

  // Đồng bộ picker Avatar AI
  if (dom.aiAvatarPicker) {
    let matchedAi = false;
    dom.aiAvatarPicker.querySelectorAll(".avatar-opt").forEach(b => {
      if (b.getAttribute("data-avatar") === state.avatarAI) {
        b.classList.add("selected");
        matchedAi = true;
      } else {
        b.classList.remove("selected");
      }
    });
    if (dom.customAiAvatarInput) {
      dom.customAiAvatarInput.value = matchedAi ? "" : (state.avatarAI || "");
    }
  }

  // Đồng bộ picker Biểu tượng Từ mục tiêu
  if (dom.targetAvatarPicker) {
    let matchedTarget = false;
    const curTarget = state.avatarTarget || "🎯";
    dom.targetAvatarPicker.querySelectorAll(".avatar-opt").forEach(b => {
      if (b.getAttribute("data-avatar") === curTarget) {
        b.classList.add("selected");
        matchedTarget = true;
      } else {
        b.classList.remove("selected");
      }
    });
    if (dom.customTargetAvatarInput) {
      dom.customTargetAvatarInput.value = matchedTarget ? "" : curTarget;
    }
  }

  dom.engineSelect.value = state.engine;
  dom.apiKeyInput.value = state.apiKey;

  const optionExists = Array.from(dom.modelSelect.options).some(opt => opt.value === state.model);
  if (optionExists) {
    dom.modelSelect.value = state.model;
    dom.customModelInput.style.display = "none";
  } else {
    dom.modelSelect.value = "custom";
    dom.customModelInput.value = state.model;
    dom.customModelInput.style.display = "block";
  }

  dom.enableVaultToolsCheck.checked = state.enableVaultTools;
  if (dom.showChatAvatarsCheck) {
    dom.showChatAvatarsCheck.checked = !!state.showChatAvatars;
  }
  if (dom.fontSizeSelect) {
    dom.fontSizeSelect.value = localStorage.getItem("chat_font_size") || "15px";
  }
  dom.ttsRate.value = state.ttsRate;
  dom.ttsRateVal.innerText = state.ttsRate + "x";

  // Hiển thị khu vực quản lý quyền cho Admin
  if (dom.adminUsersSection) {
    if (state.role === "admin" || state.username === "qtu") {
      dom.adminUsersSection.style.display = "block";
      loadAdminUsersList();
    } else {
      dom.adminUsersSection.style.display = "none";
    }
  }

  // Cập nhật hiển thị động cơ AI và tài khoản liên quan
  updateEngineUI();

  const activeTab = targetTab || "tab-emoji";
  if (dom.settingsTabs) {
    dom.settingsTabs.querySelectorAll(".modal-tab-btn").forEach(b => {
      if (b.getAttribute("data-tab") === activeTab) {
        b.classList.add("active");
      } else {
        b.classList.remove("active");
      }
    });
    document.querySelectorAll("#settingsModal .tab-content").forEach(c => {
      if (c.id === activeTab) {
        c.classList.add("active");
      } else {
        c.classList.remove("active");
      }
    });
  }

  dom.settingsModal.classList.remove("hidden");

  if (updateHash) {
    let desiredHash = "#settings";
    if (activeTab === "tab-ai") desiredHash = "#settings/ai";
    else if (activeTab === "tab-voice") desiredHash = "#settings/voice";
    if (window.location.hash !== desiredHash) {
      window.location.hash = desiredHash;
    }
  }
}

export function closeSettingsModal(updateHash = true) {
  if (dom.settingsModal) dom.settingsModal.classList.add("hidden");
  if (updateHash && window.location.hash.startsWith("#settings")) {
    history.pushState(null, "", window.location.pathname + window.location.search);
  }
}

export function bindSettingsEvents(onSettingsSaved, closeDrawerFn) {
  applyFontSize(localStorage.getItem("chat_font_size") || "15px");
  applyChatAvatarsVisibility();
  syncHeaderModelSelect();

  if (dom.fontSizeSelect) {
    dom.fontSizeSelect.value = localStorage.getItem("chat_font_size") || "15px";
    dom.fontSizeSelect.addEventListener("change", () => {
      applyFontSize(dom.fontSizeSelect.value);
      localStorage.setItem("chat_font_size", dom.fontSizeSelect.value);
    });
  }

  if (dom.headerModelSelect) {
    dom.headerModelSelect.addEventListener("change", () => {
      triggerHaptic(20);
      const val = dom.headerModelSelect.value;
      state.model = val;
      localStorage.setItem("gemini_model", val);
      if (!state.apiKey) {
        state.engine = "antigravity";
        localStorage.setItem("ai_engine", "antigravity");
        if (dom.engineSelect) {
          dom.engineSelect.value = "antigravity";
          updateEngineUI();
        }
      }
      if (dom.modelSelect) {
        dom.modelSelect.value = val;
      }
      updateHeaderModelDisplay();
    });
  }

  if (dom.engineSelect) dom.engineSelect.onchange = updateEngineUI;

  if (dom.modelSelect) {
    dom.modelSelect.onchange = () => {
      if (dom.modelSelect.value === "custom") {
        dom.customModelInput.style.display = "block";
        dom.customModelInput.focus();
      } else {
        dom.customModelInput.style.display = "none";
      }
    };
  }

  // Tabs navigation in settings modal
  if (dom.settingsTabs) {
    dom.settingsTabs.querySelectorAll(".modal-tab-btn").forEach(btn => {
      btn.onclick = () => {
        triggerHaptic(15);
        dom.settingsTabs.querySelectorAll(".modal-tab-btn").forEach(b => b.classList.remove("active"));
        document.querySelectorAll("#settingsModal .tab-content").forEach(c => c.classList.remove("active"));
        btn.classList.add("active");
        const tabId = btn.getAttribute("data-tab");
        const target = document.getElementById(tabId);
        if (target) target.classList.add("active");

        let desiredHash = "#settings";
        if (tabId === "tab-ai") desiredHash = "#settings/ai";
        else if (tabId === "tab-voice") desiredHash = "#settings/voice";
        if (window.location.hash !== desiredHash) {
          history.replaceState(null, "", desiredHash);
        }
      };
    });
  }

  // Avatar pickers
  [
    { picker: dom.userAvatarPicker, input: dom.customUserAvatarInput },
    { picker: dom.aiAvatarPicker, input: dom.customAiAvatarInput },
    { picker: dom.targetAvatarPicker, input: dom.customTargetAvatarInput }
  ].forEach(({ picker, input }) => {
    if (!picker) return;
    picker.querySelectorAll(".avatar-opt").forEach(btn => {
      btn.onclick = () => {
        triggerHaptic(15);
        picker.querySelectorAll(".avatar-opt").forEach(b => b.classList.remove("selected"));
        btn.classList.add("selected");
        if (input) input.value = "";
      };
    });
    if (input) {
      input.oninput = () => {
        if (input.value.trim()) {
          picker.querySelectorAll(".avatar-opt").forEach(b => b.classList.remove("selected"));
        }
      };
    }
  });

  if (dom.settingsBtn) dom.settingsBtn.onclick = () => openSettingsModal(null, closeDrawerFn);
  if (dom.drawerSettingsBtn) dom.drawerSettingsBtn.onclick = () => openSettingsModal(null, closeDrawerFn);
  if (dom.drawerSwitchAccountBtn) {
    dom.drawerSwitchAccountBtn.onclick = () => {
      triggerHaptic(20);
      if (typeof closeDrawerFn === "function") closeDrawerFn();
      openSettingsModal("tab-ai", closeDrawerFn);
    };
  }
  if (dom.drawerUserCard) dom.drawerUserCard.onclick = () => openSettingsModal("tab-emoji", closeDrawerFn);
  if (dom.closeSettingsBtn) dom.closeSettingsBtn.onclick = closeSettingsModal;

  if (dom.ttsRate) {
    dom.ttsRate.oninput = () => {
      if (dom.ttsRateVal) dom.ttsRateVal.innerText = dom.ttsRate.value + "x";
    };
  }

  if (dom.saveSettingsBtn) {
    dom.saveSettingsBtn.onclick = () => {
      // Username
      let newUsername = state.username || "qtu";
      if (dom.usernameInput) {
        const raw = dom.usernameInput.value.trim().toLowerCase();
        if (raw && /^[a-z0-9][a-z0-9_-]*$/.test(raw)) {
          newUsername = raw;
        }
      }
      state.username = newUsername;

      // User avatar
      if (dom.customUserAvatarInput && dom.customUserAvatarInput.value.trim()) {
        state.avatarUser = dom.customUserAvatarInput.value.trim();
      } else if (dom.userAvatarPicker) {
        const sel = dom.userAvatarPicker.querySelector(".avatar-opt.selected");
        if (sel) state.avatarUser = sel.getAttribute("data-avatar");
      }

      // AI avatar
      if (dom.customAiAvatarInput && dom.customAiAvatarInput.value.trim()) {
        state.avatarAI = dom.customAiAvatarInput.value.trim();
      } else if (dom.aiAvatarPicker) {
        const sel = dom.aiAvatarPicker.querySelector(".avatar-opt.selected");
        if (sel) state.avatarAI = sel.getAttribute("data-avatar");
      }

      // Target Word avatar
      if (dom.customTargetAvatarInput && dom.customTargetAvatarInput.value.trim()) {
        state.avatarTarget = dom.customTargetAvatarInput.value.trim();
      } else if (dom.targetAvatarPicker) {
        const sel = dom.targetAvatarPicker.querySelector(".avatar-opt.selected");
        if (sel) state.avatarTarget = sel.getAttribute("data-avatar");
      }
      if (!state.avatarTarget) state.avatarTarget = "🎯";

      state.engine = dom.engineSelect.value;
      state.apiKey = dom.apiKeyInput.value.trim();

      if (dom.modelSelect.value === "custom") {
        state.model = dom.customModelInput.value.trim() || "gemini-3.6-flash";
      } else {
        state.model = dom.modelSelect.value;
      }

      state.enableVaultTools = dom.enableVaultToolsCheck.checked;
      state.ttsRate = parseFloat(dom.ttsRate.value);

      if (dom.showChatAvatarsCheck) {
        state.showChatAvatars = dom.showChatAvatarsCheck.checked;
        localStorage.setItem("show_chat_avatars", state.showChatAvatars);
        applyChatAvatarsVisibility();
      }
      if (dom.fontSizeSelect) {
        const sz = dom.fontSizeSelect.value;
        applyFontSize(sz);
        localStorage.setItem("chat_font_size", sz);
      }

      localStorage.setItem("username", state.username);
      localStorage.setItem("avatar_user", state.avatarUser);
      localStorage.setItem("avatar_ai", state.avatarAI);
      localStorage.setItem("avatar_target", state.avatarTarget);
      localStorage.setItem("ai_engine", state.engine);
      localStorage.setItem("gemini_api_key", state.apiKey);
      localStorage.setItem("gemini_model", state.model);
      localStorage.setItem("enable_vault_tools", state.enableVaultTools);
      localStorage.setItem("tts_rate", state.ttsRate);

      updateExistingAvatarsInChat();
      syncHeaderModelSelect();

      saveUserProfileToServer({
        username: state.username,
        display_name: state.username,
        avatar_user: state.avatarUser,
        avatar_ai: state.avatarAI,
        avatar_target: state.avatarTarget,
        show_chat_avatars: state.showChatAvatars,
        ai_engine: state.engine,
        gemini_model: state.model,
        tts_rate: state.ttsRate
      });

      closeSettingsModal();
      if (typeof onSettingsSaved === "function") {
        onSettingsSaved();
      }
    };
  }
}
