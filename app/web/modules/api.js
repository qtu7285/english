/**
 * API Client Module
 */
import { state } from './state.js';

export async function syncUserProfileFromServer(targetUser = null) {
  try {
    const u = (targetUser || state.username || "qtu").trim().toLowerCase();
    const res = await fetch(`/api/user/profile?username=${encodeURIComponent(u)}`);
    if (!res.ok) return null;
    const data = await res.json();
    if (data.username) state.username = data.username;
    if (data.avatar_user) state.avatarUser = data.avatar_user;
    if (data.avatar_ai) state.avatarAI = data.avatar_ai;
    if (data.avatar_target) state.avatarTarget = data.avatar_target;
    if (typeof data.show_chat_avatars === "boolean") state.showChatAvatars = data.show_chat_avatars;
    if (data.role) state.role = data.role;
    if (typeof data.can_view_ai_info === "boolean") state.canViewAIInfo = data.can_view_ai_info;
    if (data.ai_engine) state.engine = data.ai_engine;
    if (data.gemini_model) state.model = data.gemini_model;
    if (data.tts_rate) state.ttsRate = data.tts_rate;

    localStorage.setItem("username", state.username);
    localStorage.setItem("avatar_user", state.avatarUser);
    localStorage.setItem("avatar_ai", state.avatarAI);
    localStorage.setItem("avatar_target", state.avatarTarget);
    localStorage.setItem("show_chat_avatars", state.showChatAvatars);
    localStorage.setItem("user_role", state.role || "learner");
    localStorage.setItem("can_view_ai_info", state.canViewAIInfo);
    localStorage.setItem("ai_engine", state.engine);
    localStorage.setItem("gemini_model", state.model);
    localStorage.setItem("tts_rate", state.ttsRate);

    return data;
  } catch (e) {
    console.warn("[Profile] Đồng bộ profile từ server bị hoãn:", e);
    return null;
  }
}

export async function saveUserProfileToServer(profile) {
  try {
    const res = await fetch("/api/user/profile", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile)
    });
    return res.ok;
  } catch (e) {
    console.warn("[Profile] Lưu profile lên server bị hoãn:", e);
    return false;
  }
}

export async function fetchQuotaFromServer() {
  try {
    const u = (state.username || "qtu").trim().toLowerCase();
    const res = await fetch(`/api/quota?username=${encodeURIComponent(u)}`);
    if (!res.ok) return null;
    const data = await res.json();
    if (data && data.available) {
      state.quota = data;
    } else {
      state.quota = null;
    }
    return state.quota;
  } catch (e) {
    console.warn("[Quota] Không thể tải quota:", e);
    return null;
  }
}

export async function sendChatMessageToAPI(body) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  return res;
}

export async function fetchSavedAccounts() {
  const res = await fetch(`/api/auth/accounts?username=${encodeURIComponent(state.username || 'qtu')}`);
  if (!res.ok) return [];
  const data = await res.json();
  return (data && data.accounts) ? data.accounts : [];
}

export async function switchSavedAccount(targetEmail) {
  const res = await fetch("/api/auth/switch", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: state.username || "qtu",
      target_email: targetEmail
    })
  });
  return await res.json();
}

export async function fetchAdminUsersList() {
  const res = await fetch(`/api/users/list?username=${encodeURIComponent(state.username || 'qtu')}`);
  if (!res.ok) return [];
  const data = await res.json();
  return (data && data.users) ? data.users : [];
}

export async function updateUserPermission(user, canView) {
  const res = await fetch("/api/user/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      username: user.username,
      display_name: user.display_name || user.username,
      avatar_user: user.avatar_user || "🧑‍🎓",
      avatar_ai: user.avatar_ai || "🤖",
      avatar_target: user.avatar_target || "🎯",
      role: user.role || "learner",
      can_view_ai_info: canView
    })
  });
  return res.ok;
}
