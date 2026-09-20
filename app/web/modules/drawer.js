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
}
