/**
 * Authentication & Role-Based Access Control Module
 */
import { state } from './state.js';
import { triggerHaptic } from './audio.js';
import { syncUserProfileFromServer } from './api.js';
import { closeDrawer } from './drawer.js';

let onAuthChangedCallback = null;

export function openLoginModal(pushHistory = true) {
  triggerHaptic(15);
  closeDrawer();
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.classList.remove("hidden");
    const passInput = document.getElementById("loginPasswordInput");
    if (passInput) passInput.focus();
  }
  if (pushHistory && window.location.hash !== "#login") {
    if (window.history.pushState) {
      window.history.pushState(null, "", "#login");
    } else {
      window.location.hash = "#login";
    }
  }
}

export function closeLoginModal(pushHistory = true) {
  triggerHaptic(15);
  const modal = document.getElementById("loginModal");
  if (modal) {
    modal.classList.add("hidden");
  }
  if (pushHistory && window.location.hash === "#login") {
    if (window.history.pushState) {
      window.history.pushState(null, "", window.location.pathname + window.location.search);
    } else {
      window.location.hash = "";
    }
  }
}

export function applyRoleUI(role, username) {
  const isAdmin = (role === "admin" || username === "qtu");
  
  // 1. Cập nhật nhãn và avatar người dùng trên Header
  const headerUserAvatar = document.getElementById("headerUserAvatar");
  const headerUserName = document.getElementById("headerUserName");
  const headerUserRole = document.getElementById("headerUserRole");
  if (headerUserAvatar) headerUserAvatar.textContent = state.avatarUser || (isAdmin ? "🎡" : "🧑‍🎓");
  if (headerUserName) headerUserName.textContent = username;
  if (headerUserRole) {
    headerUserRole.textContent = isAdmin ? "Admin" : "User";
    headerUserRole.className = `user-badge-role ${isAdmin ? 'admin' : 'user'}`;
  }

  // 2. Cập nhật thông tin người dùng trong Drawer
  const drawerUserName = document.getElementById("drawerUserName");
  const drawerUserAvatar = document.getElementById("drawerUserAvatar");
  const drawerUserSub = document.getElementById("drawerUserSub");
  if (drawerUserName) drawerUserName.textContent = username;
  if (drawerUserAvatar) drawerUserAvatar.textContent = state.avatarUser || (isAdmin ? "🎡" : "🧑‍🎓");
  if (drawerUserSub) drawerUserSub.textContent = isAdmin ? "Quản trị viên" : "Người học";

  // 3. Phân quyền hiển thị các menu kỹ thuật (Admin vs User)
  // Dropdown More Menu
  const menuBugFixIm5Btn = document.getElementById("menuBugFixIm5Btn");
  const menuBugFixIz6Btn = document.getElementById("menuBugFixIz6Btn");
  const menuGitBtn = document.getElementById("menuGitBtn");
  const dropdownDividers = document.querySelectorAll(".dropdown-menu .dropdown-divider");

  if (menuBugFixIm5Btn) menuBugFixIm5Btn.style.display = isAdmin ? "" : "none";
  if (menuBugFixIz6Btn) menuBugFixIz6Btn.style.display = isAdmin ? "" : "none";
  if (menuGitBtn) menuGitBtn.style.display = isAdmin ? "" : "none";
  dropdownDividers.forEach(d => d.style.display = isAdmin ? "" : "none");

  // Drawer Nav List
  const navGitBtn = document.getElementById("navGitBtn");
  const navBugFixIm5Btn = document.getElementById("navBugFixIm5Btn");
  const navBugFixIz6Btn = document.getElementById("navBugFixIz6Btn");
  if (navGitBtn) navGitBtn.style.display = isAdmin ? "" : "none";
  if (navBugFixIm5Btn) navBugFixIm5Btn.style.display = isAdmin ? "" : "none";
  if (navBugFixIz6Btn) navBugFixIz6Btn.style.display = isAdmin ? "" : "none";

  // Drawer AI Quota & Account Switch
  const drawerAiQuotaCard = document.getElementById("drawerAiQuotaCard");
  const drawerSwitchAccountBtn = document.getElementById("drawerSwitchAccountBtn");
  if (!isAdmin) {
    if (drawerAiQuotaCard) drawerAiQuotaCard.style.display = "none";
    if (drawerSwitchAccountBtn) drawerSwitchAccountBtn.style.display = "none";
  } else {
    if (drawerSwitchAccountBtn) drawerSwitchAccountBtn.style.display = "";
  }
}

export async function checkAuthSession() {
  try {
    const token = localStorage.getItem("english_session_token");
    const headers = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    const res = await fetch("/api/auth/me", { headers });
    if (res.ok) {
      const data = await res.json();
      if (data.logged_in && data.user) {
        state.username = data.user.username;
        state.role = data.user.role || (data.user.username === "qtu" ? "admin" : "user");
        state.canViewAIInfo = data.user.can_view_ai_info || (data.user.username === "qtu");
        if (data.user.avatar_user) state.avatarUser = data.user.avatar_user;
        if (data.user.avatar_ai) state.avatarAI = data.user.avatar_ai;
        if (data.user.avatar_target) state.avatarTarget = data.user.avatar_target;

        localStorage.setItem("username", state.username);
        localStorage.setItem("user_role", state.role);
        applyRoleUI(state.role, state.username);
        return data.user;
      }
    }
  } catch (e) {
    console.warn("[Auth] Kiểm tra phiên:", e);
  }

  // Nếu chưa có session hợp lệ, dùng username trong localStorage hoặc qtu
  applyRoleUI(state.role || "admin", state.username || "qtu");
  return null;
}

export async function loginWithPassword(username, password) {
  const errorEl = document.getElementById("loginErrorMsg");
  if (errorEl) {
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      const msg = data.error || "Tài khoản hoặc mật khẩu không chính xác.";
      if (errorEl) {
        errorEl.textContent = msg;
        errorEl.classList.remove("hidden");
      }
      return false;
    }

    // Lưu token và thông tin phiên
    localStorage.setItem("english_session_token", data.token);
    state.username = data.user.username;
    state.role = data.user.role || (data.user.username === "qtu" ? "admin" : "user");
    state.canViewAIInfo = data.user.can_view_ai_info || (data.user.username === "qtu");
    if (data.user.avatar_user) state.avatarUser = data.user.avatar_user;
    if (data.user.avatar_ai) state.avatarAI = data.user.avatar_ai;
    if (data.user.avatar_target) state.avatarTarget = data.user.avatar_target;

    localStorage.setItem("username", state.username);
    localStorage.setItem("user_role", state.role);

    applyRoleUI(state.role, state.username);
    closeLoginModal(true);

    if (typeof onAuthChangedCallback === "function") {
      onAuthChangedCallback(data.user);
    }
    return true;
  } catch (e) {
    if (errorEl) {
      errorEl.textContent = "Không thể kết nối đến máy chủ: " + e.message;
      errorEl.classList.remove("hidden");
    }
    return false;
  }
}

export async function loginWithSocial(provider, credential, email = "", name = "") {
  const errorEl = document.getElementById("loginErrorMsg");
  if (errorEl) {
    errorEl.textContent = "";
    errorEl.classList.add("hidden");
  }

  try {
    const res = await fetch("/api/auth/social-login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ provider, credential, email, name })
    });

    const data = await res.json();
    if (!res.ok || !data.success) {
      const msg = data.error || "Đăng nhập mạng xã hội thất bại.";
      if (errorEl) {
        errorEl.textContent = msg;
        errorEl.classList.remove("hidden");
      }
      return false;
    }

    localStorage.setItem("english_session_token", data.token);
    state.username = data.user.username;
    state.role = data.user.role || (data.user.username === "qtu" ? "admin" : "user");
    state.canViewAIInfo = data.user.can_view_ai_info || (data.user.username === "qtu");

    localStorage.setItem("username", state.username);
    localStorage.setItem("user_role", state.role);

    applyRoleUI(state.role, state.username);
    closeLoginModal(true);

    if (typeof onAuthChangedCallback === "function") {
      onAuthChangedCallback(data.user);
    }
    return true;
  } catch (e) {
    if (errorEl) {
      errorEl.textContent = "Lỗi kết nối: " + e.message;
      errorEl.classList.remove("hidden");
    }
    return false;
  }
}

export async function logoutUser() {
  triggerHaptic(15);
  const token = localStorage.getItem("english_session_token");
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token || ""}`,
        "Content-Type": "application/json"
      }
    });
  } catch (e) {
    console.warn("[Auth] Logout request error:", e);
  }

  localStorage.removeItem("english_session_token");
  // Mở modal login để chọn người dùng tiếp theo
  openLoginModal(true);
}

export function bindAuthEvents(onAuthChanged) {
  onAuthChangedCallback = onAuthChanged;

  // Nút mở modal đăng nhập từ Header
  const headerUserBtn = document.getElementById("headerUserBtn");
  if (headerUserBtn) {
    headerUserBtn.onclick = () => openLoginModal(true);
  }

  // Nút đóng modal đăng nhập
  const closeLoginBtn = document.getElementById("closeLoginBtn");
  if (closeLoginBtn) {
    closeLoginBtn.onclick = () => closeLoginModal(true);
  }

  // Chọn nhanh user (qtu / gty)
  const quickUserBtns = document.querySelectorAll(".quick-user-btn");
  const usernameInput = document.getElementById("loginUsernameInput");
  const passwordInput = document.getElementById("loginPasswordInput");

  quickUserBtns.forEach(btn => {
    btn.onclick = () => {
      triggerHaptic(10);
      quickUserBtns.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const u = btn.getAttribute("data-user");
      const p = btn.getAttribute("data-pass");
      if (usernameInput) usernameInput.value = u;
      if (passwordInput) {
        passwordInput.value = p;
        passwordInput.focus();
      }
    };
  });

  // Submit form đăng nhập mật khẩu
  const loginForm = document.getElementById("loginForm");
  if (loginForm) {
    loginForm.onsubmit = async (e) => {
      e.preventDefault();
      const u = (usernameInput ? usernameInput.value : "").trim();
      const p = (passwordInput ? passwordInput.value : "").trim();
      if (!u || !p) return;
      await loginWithPassword(u, p);
    };
  }

  // Nút Đăng xuất
  const menuLogoutBtn = document.getElementById("menuLogoutBtn");
  if (menuLogoutBtn) {
    menuLogoutBtn.onclick = logoutUser;
  }
  const drawerLogoutBtn = document.getElementById("drawerLogoutBtn");
  if (drawerLogoutBtn) {
    drawerLogoutBtn.onclick = (e) => {
      e.stopPropagation();
      logoutUser();
    };
  }

  // Social Login: Google & Facebook
  const googleLoginBtn = document.getElementById("googleLoginBtn");
  if (googleLoginBtn) {
    googleLoginBtn.onclick = async () => {
      triggerHaptic(15);
      try {
        const res = await fetch("/api/auth/oauth-config");
        const cfg = await res.json();
        if (cfg && cfg.google_client_id) {
          // Khởi chạy Google OAuth nếu đã cấu hình
          alert("[OK] Đang khởi tạo kết nối Google Sign-in với Client ID: " + cfg.google_client_id);
        } else {
          alert("[~] Tính năng Google Login đang chờ cấu hình Client ID.\n\nBạn có thể thêm 'google_client_id' vào file 'app/data/oauth_config.json' để kích hoạt.");
        }
      } catch (e) {
        alert("[X] Không thể kết nối tới máy chủ để kiểm tra cấu hình OAuth.");
      }
    };
  }

  const facebookLoginBtn = document.getElementById("facebookLoginBtn");
  if (facebookLoginBtn) {
    facebookLoginBtn.onclick = async () => {
      triggerHaptic(15);
      try {
        const res = await fetch("/api/auth/oauth-config");
        const cfg = await res.json();
        if (cfg && cfg.facebook_app_id) {
          alert("[OK] Đang khởi tạo kết nối Facebook Login với App ID: " + cfg.facebook_app_id);
        } else {
          alert("[~] Tính năng Facebook Login đang chờ cấu hình App ID.\n\nBạn có thể thêm 'facebook_app_id' vào file 'app/data/oauth_config.json' để kích hoạt.");
        }
      } catch (e) {
        alert("[X] Không thể kết nối tới máy chủ để kiểm tra cấu hình OAuth.");
      }
    };
  }
}
