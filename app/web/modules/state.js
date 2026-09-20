/**
 * State Management Module
 */

export const MODEL_DISPLAY_NAMES = {
  "gemini-3.6-flash": "3.6 Flash",
  "gemini-3.7-flash": "3.7 Flash",
  "gemini-3.8-flash": "3.8 Flash",
  "gemini-3.1-pro": "3.1 Pro"
};

let initialModel = localStorage.getItem("gemini_model") || "gemini-3.6-flash";
if (initialModel === "gemini-2.5-flash" || initialModel === "gemini-1.5-flash" || initialModel === "gemini-2.0-flash") {
  initialModel = "gemini-3.6-flash";
  localStorage.setItem("gemini_model", "gemini-3.6-flash");
}

export const state = {
  username: localStorage.getItem("username") || "qtu",
  avatarUser: localStorage.getItem("avatar_user") || "🧑‍🎓",
  avatarAI: localStorage.getItem("avatar_ai") || "🤖",
  avatarTarget: localStorage.getItem("avatar_target") || "🎯",
  showChatAvatars: localStorage.getItem("show_chat_avatars") === "true",
  engine: localStorage.getItem("ai_engine") || "antigravity",
  apiKey: localStorage.getItem("gemini_api_key") || "",
  model: initialModel,
  enableVaultTools: localStorage.getItem("enable_vault_tools") !== "false",
  ttsRate: parseFloat(localStorage.getItem("tts_rate") || "0.9"),
  conversation: [],
  currentVaultPath: "",
  selectedVaultFile: null,
  quota: null,
  role: localStorage.getItem("user_role") || (localStorage.getItem("username") === "qtu" ? "admin" : "learner"),
  canViewAIInfo: localStorage.getItem("can_view_ai_info") === "true" || (localStorage.getItem("username") === "qtu")
};
