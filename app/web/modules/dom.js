/**
 * DOM Elements & Viewport Management
 */

// Viewport Height Sync for Mobile Browsers
export function syncAppHeight() {
  const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
  document.documentElement.style.setProperty("--app-height", `${vh}px`);
}

if ("scrollRestoration" in history) {
  history.scrollRestoration = "manual";
}
window.scrollTo(0, 0);

if (window.visualViewport) {
  window.visualViewport.addEventListener("resize", syncAppHeight);
  window.visualViewport.addEventListener("scroll", syncAppHeight);
}
window.addEventListener("resize", syncAppHeight);
syncAppHeight();

// Chat Elements
export const chatViewport = document.getElementById("chatViewport");
export const chatMessages = document.getElementById("chatMessages");
export const chatForm = document.getElementById("chatForm");
export const messageInput = document.getElementById("messageInput");
export const sendBtn = document.getElementById("sendBtn");
export const newChatBtn = document.getElementById("newChatBtn") || document.getElementById("clearBtn");
export const clearBtn = newChatBtn;
export const initialAiAvatar = document.getElementById("initialAiAvatar");

// Header Elements
export const headerModelSelect = document.getElementById("headerModelSelect");
export const headerModelLabel = document.getElementById("headerModelLabel");
export const headerModelIndicator = document.getElementById("headerModelIndicator");

// Quick Chips Bar
export const quickChipsBar = document.getElementById("quickChipsBar");
export const dynamicChoiceChips = document.getElementById("dynamicChoiceChips");
export const dynamicContextChips = document.getElementById("dynamicContextChips");

// Drawer Elements
export const menuToggleBtn = document.getElementById("menuToggleBtn");
export const drawerBackdrop = document.getElementById("drawerBackdrop");
export const drawerSidebar = document.getElementById("drawerSidebar");
export const drawerCloseBtn = document.getElementById("drawerCloseBtn");
export const drawerNewChatBtn = document.getElementById("drawerNewChatBtn");
export const drawerSettingsBtn = document.getElementById("drawerSettingsBtn");
export const drawerUserCard = document.getElementById("drawerUserCard");
export const drawerUserAvatar = document.getElementById("drawerUserAvatar");
export const drawerUserName = document.getElementById("drawerUserName");
export const navSaveBtn = document.getElementById("navSaveBtn");
export const navGitBtn = document.getElementById("navGitBtn");
export const navBugFixIm5Btn = document.getElementById("navBugFixIm5Btn");
export const navBugFixIz6Btn = document.getElementById("navBugFixIz6Btn");
export const navHelpBtn = document.getElementById("navHelpBtn");

// Header More Menu Elements
export const headerMoreBtn = document.getElementById("headerMoreBtn");
export const headerMoreMenu = document.getElementById("headerMoreMenu");
export const menuSaveBtn = document.getElementById("menuSaveBtn");
export const menuGitBtn = document.getElementById("menuGitBtn");
export const menuHelpBtn = document.getElementById("menuHelpBtn");
export const menuBugFixIm5Btn = document.getElementById("menuBugFixIm5Btn");
export const menuBugFixIz6Btn = document.getElementById("menuBugFixIz6Btn");

// Drawer Quota & Accounts
export const drawerAiQuotaCard = document.getElementById("drawerAiQuotaCard");
export const drawerAiEmail = document.getElementById("drawerAiEmail");
export const drawerAiQuota5h = document.getElementById("drawerAiQuota5h");
export const drawerAiQuotaWeek = document.getElementById("drawerAiQuotaWeek");
export const drawerSwitchAccountBtn = document.getElementById("drawerSwitchAccountBtn");

// Settings Modal Elements
export const settingsBtn = document.getElementById("settingsBtn") || drawerSettingsBtn;
export const settingsModal = document.getElementById("settingsModal");
export const closeSettingsBtn = document.getElementById("closeSettingsBtn");
export const saveSettingsBtn = document.getElementById("saveSettingsBtn");
export const settingsTabs = document.querySelector("#settingsModal .modal-tabs");
export const usernameInput = document.getElementById("usernameInput");
export const userAvatarPicker = document.getElementById("userAvatarPicker");
export const customUserAvatarInput = document.getElementById("customUserAvatarInput");
export const aiAvatarPicker = document.getElementById("aiAvatarPicker");
export const customAiAvatarInput = document.getElementById("customAiAvatarInput");
export const targetAvatarPicker = document.getElementById("targetAvatarPicker");
export const customTargetAvatarInput = document.getElementById("customTargetAvatarInput");
export const showChatAvatarsCheck = document.getElementById("showChatAvatarsCheck");
export const fontSizeSelect = document.getElementById("fontSizeSelect");
export const engineSelect = document.getElementById("engineSelect");
export const engineHint = document.getElementById("engineHint");
export const apiKeyGroup = document.getElementById("apiKeyGroup");
export const apiKeyInput = document.getElementById("apiKeyInput");
export const modelGroup = document.getElementById("modelGroup");
export const modelSelect = document.getElementById("modelSelect");
export const customModelInput = document.getElementById("customModelInput");
export const enableVaultToolsCheck = document.getElementById("enableVaultToolsCheck");
export const antigravityAccountsGroup = document.getElementById("antigravityAccountsGroup");
export const savedAccountsList = document.getElementById("savedAccountsList");
export const adminUsersSection = document.getElementById("adminUsersSection");
export const adminUsersList = document.getElementById("adminUsersList");
export const ttsRate = document.getElementById("ttsRate");
export const ttsRateVal = document.getElementById("ttsRateVal");
export const testVoiceBtn = document.getElementById("testVoiceBtn");

// Vault Modal Elements
export const vaultBtn = document.getElementById("vaultBtn");
export const vaultModal = document.getElementById("vaultModal");
export const closeVaultBtn = document.getElementById("closeVaultBtn");
export const vaultSearchInput = document.getElementById("vaultSearchInput");
export const vaultLayout = document.getElementById("vaultLayout");
export const vaultFileList = document.getElementById("vaultFileList");
export const vaultPreview = document.getElementById("vaultPreview");
export const vaultBackBtn = document.getElementById("vaultBackBtn");
export const insertToChatBtn = document.getElementById("insertToChatBtn");

// PWA Install Button
export const pwaInstallBtn = document.getElementById("pwaInstallBtn");
