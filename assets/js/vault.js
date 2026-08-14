(function () {
  "use strict";

  const CONTENT_KEY = "vault_unlocked_content";
  const PASSWORD_KEY = "vault_unlocked_password";
  const TIME_KEY = "vault_unlock_time";
  const TTL = 24 * 60 * 60 * 1000;

  function getCachedPassword() {
    const password = localStorage.getItem(PASSWORD_KEY);
    const time = localStorage.getItem(TIME_KEY);
    if (!password || !time) return null;
    if (Date.now() - parseInt(time, 10) > TTL) {
      localStorage.removeItem(PASSWORD_KEY);
      localStorage.removeItem(TIME_KEY);
      return null;
    }
    return password;
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
        sessionStorage.setItem(CONTENT_KEY, html);
        localStorage.setItem(PASSWORD_KEY, password);
        localStorage.setItem(TIME_KEY, Date.now().toString());
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

  document.addEventListener("DOMContentLoaded", async function () {
    if (restoreFromSession()) return;

    const cachedPassword = getCachedPassword();
    if (cachedPassword) {
      const ok = await tryUnlock(cachedPassword, true);
      if (ok) return;
    }

    bindUnlockEvents();
  });
})();
