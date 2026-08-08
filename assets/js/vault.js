(function () {
  "use strict";

  const HASH_KEY = "vault_auth_hash";
  const CONTENT_KEY = "vault_unlocked_content";

  async function digestPassword(password) {
    const enc = new TextEncoder();
    const buf = await window.crypto.subtle.digest("SHA-256", enc.encode(password));
    return Array.from(new Uint8Array(buf))
      .map((b) => b.toString(16).padStart(2, "0"))
      .join("");
  }

  async function deriveKey(password, salt, iterations) {
    const enc = new TextEncoder();
    const keyMaterial = await window.crypto.subtle.importKey(
      "raw",
      enc.encode(password),
      { name: "PBKDF2" },
      false,
      ["deriveKey"]
    );
    return window.crypto.subtle.deriveKey(
      {
        name: "PBKDF2",
        salt: salt,
        iterations: iterations,
        hash: "SHA-256",
      },
      keyMaterial,
      { name: "AES-GCM", length: 256 },
      false,
      ["decrypt"]
    );
  }

  async function decrypt(payloadB64, password) {
    const payload = JSON.parse(atob(payloadB64));
    const salt = Uint8Array.from(atob(payload.salt), (c) => c.charCodeAt(0));
    const iv = Uint8Array.from(atob(payload.iv), (c) => c.charCodeAt(0));
    const ct = Uint8Array.from(atob(payload.ct), (c) => c.charCodeAt(0));
    const key = await deriveKey(password, salt, payload.iter);
    const decrypted = await window.crypto.subtle.decrypt(
      { name: "AES-GCM", iv: iv },
      key,
      ct
    );
    return new TextDecoder().decode(decrypted);
  }

  function getPayload() {
    const el = document.getElementById("vault-payload");
    if (!el) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function renderUnlocked(html) {
    const container = document.getElementById("vault-content");
    const lockUi = document.getElementById("vault-lock-ui");
    if (container) {
      container.innerHTML = html;
      container.style.display = "";
    }
    if (lockUi) {
      lockUi.style.display = "none";
    }
    renderLockButton();
  }

  function renderLockButton() {
    if (document.getElementById("vault-lock-button")) return;
    const container = document.getElementById("vault-content");
    if (!container) return;

    const wrapper = document.createElement("div");
    wrapper.style.textAlign = "center";

    const btn = document.createElement("button");
    btn.id = "vault-lock-button";
    btn.type = "button";
    btn.className = "lock-button";
    btn.style.marginTop = "1.5rem";
    btn.textContent = "🔒 锁定 Vault";
    btn.addEventListener("click", lockVault);

    wrapper.appendChild(btn);
    container.appendChild(wrapper);
  }

  function showLockUi() {
    const container = document.getElementById("vault-content");
    const lockUi = document.getElementById("vault-lock-ui");
    if (container) {
      container.innerHTML = "";
      container.style.display = "none";
    }
    if (lockUi) {
      lockUi.style.display = "";
    }
  }

  function lockVault() {
    localStorage.removeItem(HASH_KEY);
    sessionStorage.removeItem(CONTENT_KEY);
    showLockUi();
  }

  async function tryUnlock(password, saveOnSuccess) {
    const payload = getPayload();
    if (!payload) {
      showError("Vault 配置异常，未找到加密数据。");
      return false;
    }

    try {
      const html = await decrypt(payload.data, password);
      if (saveOnSuccess) {
        const hash = await digestPassword(password);
        localStorage.setItem(HASH_KEY, hash);
        sessionStorage.setItem(CONTENT_KEY, html);
      }
      renderUnlocked(html);
      return true;
    } catch (e) {
      return false;
    }
  }

  function showError(message) {
    const error = document.getElementById("vault-error");
    if (error) error.textContent = message;
  }

  function clearError() {
    showError("");
  }

  function restoreFromSession() {
    const html = sessionStorage.getItem(CONTENT_KEY);
    if (!html) return false;
    renderUnlocked(html);
    return true;
  }

  function bindUnlockEvents() {
    const input = document.getElementById("vault-password");
    const button = document.getElementById("vault-unlock");
    if (!input || !button) return;

    async function onUnlock() {
      clearError();
      const password = input.value.trim();
      if (!password) {
        showError("请输入密码。");
        return;
      }

      button.disabled = true;
      button.textContent = "解锁中...";

      const ok = await tryUnlock(password, true);
      if (!ok) {
        showError("密码错误，请重试。");
        input.value = "";
        input.focus();
      }

      button.disabled = false;
      button.textContent = "解锁";
    }

    button.addEventListener("click", onUnlock);
    input.addEventListener("keypress", function (e) {
      if (e.key === "Enter") onUnlock();
    });
    input.focus();
  }

  document.addEventListener("DOMContentLoaded", function () {
    if (!restoreFromSession()) {
      bindUnlockEvents();
    }
  });
})();
