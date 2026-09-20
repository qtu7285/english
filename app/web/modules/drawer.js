/**
 * Navigation Drawer Module
 */
import * as dom from './dom.js';
import { triggerHaptic } from './audio.js';

export function openDrawer() {
  triggerHaptic(15);
  if (dom.drawerSidebar) dom.drawerSidebar.classList.add("open");
  if (dom.drawerBackdrop) dom.drawerBackdrop.classList.remove("hidden");
}

export function closeDrawer() {
  if (dom.drawerSidebar) dom.drawerSidebar.classList.remove("open");
  if (dom.drawerBackdrop) dom.drawerBackdrop.classList.add("hidden");
}

export function bindDrawerEvents(onSendShortcut) {
  if (dom.menuToggleBtn) dom.menuToggleBtn.onclick = openDrawer;
  if (dom.drawerCloseBtn) dom.drawerCloseBtn.onclick = closeDrawer;
  if (dom.drawerBackdrop) dom.drawerBackdrop.onclick = closeDrawer;

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && dom.drawerSidebar && dom.drawerSidebar.classList.contains("open")) {
      closeDrawer();
    }
  });

  const shortcuts = [
    { btn: dom.navSaveBtn, cmd: ".s" },
    { btn: dom.navGitBtn, cmd: ".g" },
    { btn: dom.navBugFixB5Btn, cmd: ".b5" },
    { btn: dom.navBugFixB6Btn, cmd: ".b6" },
    { btn: dom.navHelpBtn, cmd: ".help" }
  ];

  shortcuts.forEach(({ btn, cmd }) => {
    if (btn) {
      btn.onclick = () => {
        triggerHaptic(15);
        closeDrawer();
        if (typeof onSendShortcut === "function") {
          onSendShortcut(cmd);
        }
      };
    }
  });

  // Bind Header More Menu (3-dots)
  if (dom.headerMoreBtn && dom.headerMoreMenu) {
    const toggleMoreMenu = (e) => {
      e.stopPropagation();
      triggerHaptic(15);
      dom.headerMoreMenu.classList.toggle("hidden");
    };

    const closeMoreMenu = () => {
      if (dom.headerMoreMenu && !dom.headerMoreMenu.classList.contains("hidden")) {
        dom.headerMoreMenu.classList.add("hidden");
      }
    };

    dom.headerMoreBtn.onclick = toggleMoreMenu;

    window.addEventListener("click", (e) => {
      if (!dom.headerMoreMenu.contains(e.target) && e.target !== dom.headerMoreBtn && !dom.headerMoreBtn.contains(e.target)) {
        closeMoreMenu();
      }
    });

    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape") closeMoreMenu();
    });

    const moreShortcuts = [
      { btn: dom.menuSaveBtn, cmd: ".s" },
      { btn: dom.menuGitBtn, cmd: ".g" },
      { btn: dom.menuHelpBtn, cmd: ".help" },
      { btn: dom.menuBugFixB5Btn, cmd: ".b5" },
      { btn: dom.menuBugFixB6Btn, cmd: ".b6" }
    ];

    moreShortcuts.forEach(({ btn, cmd }) => {
      if (btn) {
        btn.onclick = () => {
          triggerHaptic(15);
          closeMoreMenu();
          if (typeof onSendShortcut === "function") {
            onSendShortcut(cmd);
          }
        };
      }
    });
  }
}
