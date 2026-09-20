/**
 * Vault Explorer Module
 */
import { state } from './state.js';
import * as dom from './dom.js';

export function resetVaultMobileView() {
  if (dom.vaultLayout) dom.vaultLayout.classList.remove("show-preview");
  if (dom.vaultBackBtn) dom.vaultBackBtn.style.display = "none";
}

export async function loadVaultFiles(subpath = "") {
  resetVaultMobileView();
  if (!dom.vaultFileList) return;
  dom.vaultFileList.innerHTML = '<div class="vault-loading-box"><span class="vault-spinner"></span></div>';
  try {
    const res = await fetch(`/api/vault/list?subpath=${encodeURIComponent(subpath)}`);
    const data = await res.json();
    renderVaultFiles(data.files || []);
  } catch (err) {
    dom.vaultFileList.innerHTML = `<div style="color:red; padding:10px;">Lỗi: ${err.message}</div>`;
  }
}

export function renderVaultFiles(files) {
  if (!dom.vaultFileList) return;
  dom.vaultFileList.innerHTML = "";
  if (files.length === 0) {
    dom.vaultFileList.innerHTML = '<div style="padding:10px; color:#94a3b8;">Không tìm thấy file nào.</div>';
    return;
  }

  files.forEach(f => {
    const item = document.createElement("div");
    item.className = "vault-item";
    item.innerHTML = `
      <span class="file-name">${f.name}</span>
      <span class="file-badge">${f.type}</span>
    `;
    item.onclick = () => selectVaultFile(f, item);
    dom.vaultFileList.appendChild(item);
  });
}

export async function selectVaultFile(file, element) {
  document.querySelectorAll(".vault-item").forEach(el => el.classList.remove("selected"));
  element.classList.add("selected");
  state.selectedVaultFile = file;
  if (dom.insertToChatBtn) dom.insertToChatBtn.disabled = false;

  if (dom.vaultLayout) dom.vaultLayout.classList.add("show-preview");
  if (dom.vaultBackBtn) dom.vaultBackBtn.style.display = "inline-flex";

  if (!dom.vaultPreview) return;
  dom.vaultPreview.innerHTML = "Đang tải...";
  try {
    const res = await fetch(`/api/vault/read?path=${encodeURIComponent(file.path)}`);
    const data = await res.json();
    if (data.content !== undefined) {
      dom.vaultPreview.innerText = data.content;
    } else {
      dom.vaultPreview.innerText = data.error || "Không thể đọc file.";
    }
  } catch (err) {
    dom.vaultPreview.innerText = "Lỗi khi đọc file: " + err.message;
  }
}

export function bindVaultEvents() {
  const refreshVaultBtn = document.getElementById("refreshVaultBtn");

  if (dom.vaultBtn && dom.vaultModal) {
    dom.vaultBtn.onclick = () => {
      resetVaultMobileView();
      dom.vaultModal.classList.remove("hidden");
      loadVaultFiles();
    };

    if (dom.vaultBackBtn) {
      dom.vaultBackBtn.onclick = resetVaultMobileView;
    }

    if (dom.closeVaultBtn) {
      dom.closeVaultBtn.onclick = () => {
        dom.vaultModal.classList.add("hidden");
        resetVaultMobileView();
      };
    }

    if (refreshVaultBtn) refreshVaultBtn.onclick = () => loadVaultFiles();

    if (dom.vaultSearchInput) {
      dom.vaultSearchInput.oninput = async (e) => {
        const q = e.target.value.trim();
        if (!q) {
          loadVaultFiles();
          return;
        }
        resetVaultMobileView();
        try {
          const res = await fetch(`/api/vault/search?q=${encodeURIComponent(q)}`);
          const data = await res.json();
          renderVaultFiles((data.matches || []).map(m => ({
            name: m.path.split("/").pop(),
            path: m.path,
            type: m.match_type === "filename" ? "file" : `line ${m.line}`
          })));
        } catch (err) {}
      };
    }

    if (dom.insertToChatBtn) {
      dom.insertToChatBtn.onclick = () => {
        if (state.selectedVaultFile && dom.vaultPreview && dom.vaultPreview.innerText) {
          if (dom.messageInput) {
            dom.messageInput.value = `Hãy phân tích nội dung file ${state.selectedVaultFile.path}:\n\n` + dom.vaultPreview.innerText.slice(0, 1000);
            dom.messageInput.focus();
          }
          dom.vaultModal.classList.add("hidden");
          resetVaultMobileView();
        }
      };
    }
  }
}
