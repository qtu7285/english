/**
 * PWA, Service Worker, LiveReload & Gesture Module
 */
import { triggerHaptic } from './audio.js';
import { chatViewport } from './dom.js';

let deferredPrompt = null;
let swRegisterError = null;

const isStandaloneApp =
  (window.matchMedia && window.matchMedia("(display-mode: standalone)").matches) ||
  window.navigator.standalone === true;

function pwaPort() {
  return location.port || (location.protocol === "https:" ? "443" : "80");
}

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

export function refreshInstallBtn() {
  const installPwaBtn = document.getElementById("installPwaBtn");
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

export function initPWA() {
  const installPwaBtn = document.getElementById("installPwaBtn");

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
}

export function initLiveReload() {
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
}

export function attachPullToRefresh(container, onRefresh) {
  if (!container) return;

  // Find or create ptr element
  let ptr = container.querySelector(":scope > .pull-to-refresh");
  if (!ptr) {
    ptr = document.createElement("div");
    ptr.className = "pull-to-refresh";
    ptr.innerHTML = '<div class="ptr-spinner"></div><span class="ptr-label">Kéo xuống để làm mới</span>';
    container.prepend(ptr);
  }
  const spinner = ptr.querySelector(".ptr-spinner");
  const label = ptr.querySelector(".ptr-label");

  let startY = 0;
  let isPulling = false;
  let hasTriggeredHaptic = false;
  const PTR_THRESHOLD = 55;
  const PTR_MAX = 80;

  container.addEventListener("touchstart", (e) => {
    if (container.scrollTop <= 0) {
      startY = e.touches[0].pageY;
      isPulling = true;
      hasTriggeredHaptic = false;
    } else {
      isPulling = false;
    }
  }, { passive: true });

  container.addEventListener("touchmove", (e) => {
    if (!isPulling || container.scrollTop > 0) return;
    const currentY = e.touches[0].pageY;
    const diff = currentY - startY;

    if (diff > 0) {
      if (e.cancelable) e.preventDefault();

      const pullHeight = Math.min(diff * 0.4, PTR_MAX);
      ptr.style.height = `${pullHeight}px`;
      ptr.classList.add("visible");

      const rotation = Math.min(pullHeight * 5, 360);
      if (spinner) spinner.style.transform = `rotate(${rotation}deg)`;

      if (pullHeight >= PTR_THRESHOLD) {
        if (label) label.innerText = "Thả ra để làm mới";
        if (!hasTriggeredHaptic) {
          triggerHaptic(20);
          hasTriggeredHaptic = true;
        }
      } else {
        if (label) label.innerText = "Kéo xuống để làm mới";
        hasTriggeredHaptic = false;
      }
    }
  }, { passive: false });

  container.addEventListener("touchend", async () => {
    if (!isPulling) return;
    isPulling = false;
    const pullHeight = parseFloat(ptr.style.height) || 0;

    if (pullHeight >= PTR_THRESHOLD) {
      ptr.style.height = "38px";
      ptr.classList.add("refreshing");
      if (label) label.innerText = "Đang làm mới...";
      triggerHaptic(35);

      if (typeof onRefresh === "function") {
        try {
          await onRefresh();
        } catch (err) {
          console.warn("[PTR] Lỗi khi làm mới:", err);
        } finally {
          ptr.style.height = "0px";
          ptr.classList.remove("visible", "refreshing");
          setTimeout(() => {
            if (spinner) spinner.style.transform = "rotate(0deg)";
            if (label) label.innerText = "Kéo xuống để làm mới";
          }, 200);
        }
      } else {
        setTimeout(() => {
          window.scrollTo(0, 0);
          window.location.reload();
        }, 350);
      }
    } else {
      ptr.style.height = "0px";
      ptr.classList.remove("visible");
      setTimeout(() => {
        if (spinner) spinner.style.transform = "rotate(0deg)";
        if (label) label.innerText = "Kéo xuống để làm mới";
      }, 200);
    }
  }, { passive: true });
}

export function initPullToRefresh() {
  // 1. Màn hình Chat chính: reload toàn bộ trang
  if (chatViewport) {
    attachPullToRefresh(chatViewport, () => {
      window.scrollTo(0, 0);
      window.location.reload();
    });
  }

  // 2. Modal Cài đặt: đồng bộ lại Quota và hồ sơ người dùng
  const settingsBody = document.querySelector("#settingsModal .modal-body");
  if (settingsBody) {
    attachPullToRefresh(settingsBody, async () => {
      try {
        const { syncUserProfileFromServer, fetchQuotaFromServer } = await import('./api.js');
        const { updateHeaderModelDisplay } = await import('./settings.js');
        await syncUserProfileFromServer();
        await fetchQuotaFromServer();
        updateHeaderModelDisplay();
      } catch (e) {
        console.warn("[PTR Settings]", e);
      }
    });
  }

  // 3. Menu trượt (Navigation Drawer): đồng bộ Quota AI
  const drawerBody = document.querySelector(".drawer-body");
  if (drawerBody) {
    attachPullToRefresh(drawerBody, async () => {
      try {
        const { fetchQuotaFromServer } = await import('./api.js');
        const { updateHeaderModelDisplay } = await import('./settings.js');
        await fetchQuotaFromServer();
        updateHeaderModelDisplay();
      } catch (e) {
        console.warn("[PTR Drawer]", e);
      }
    });
  }

  // 4. Modal Kho tài liệu (Vault) nếu có
  const vaultList = document.getElementById("vaultFileList");
  if (vaultList) {
    attachPullToRefresh(vaultList, async () => {
      try {
        const { loadVaultFiles } = await import('./vault.js');
        await loadVaultFiles();
      } catch (e) {
        console.warn("[PTR Vault]", e);
      }
    });
  }
}
