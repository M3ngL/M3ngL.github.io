(function () {
  "use strict";

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

  async function decrypt(ciphertextB64, password) {
    const payload = JSON.parse(atob(ciphertextB64));
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

  function numberHeadings(container) {
    const headers = container.querySelectorAll("h2, h3, h4, h5, h6");
    const nums = [0, 0, 0, 0, 0];
    headers.forEach((h) => {
      const level = parseInt(h.tagName.substring(1)) - 2;
      if (level >= 0 && level < nums.length) {
        nums[level]++;
        for (let i = level + 1; i < nums.length; i++) {
          nums[i] = 0;
        }
        const prefix = nums.slice(0, level + 1).join(".");
        h.innerHTML = `${prefix} ${h.innerHTML}`;
      }
    });
  }

  function rebuildToc() {
    const content = document.querySelector(".post");
    const tocList = document.querySelector(".toc-list");
    if (!content || !tocList) return;

    tocList.innerHTML = "";
    const headings = content.querySelectorAll("h2, h3, h4, h5, h6");
    const numberStack = [0, 0, 0, 0, 0];

    headings.forEach((heading, index) => {
      const level = parseInt(heading.tagName.charAt(1));
      heading.id = heading.id || `heading-${index}`;

      numberStack[level - 2]++;
      for (let i = level - 1; i < numberStack.length; i++) numberStack[i] = 0;

      const numberStr = numberStack
        .slice(0, level - 2 + 1)
        .filter((n) => n > 0)
        .join(".");

      const li = document.createElement("li");
      li.classList.add(`toc-level-${level}`);
      li.innerHTML = `<a href="#${heading.id}">${numberStr} ${heading.textContent}</a>`;
      tocList.appendChild(li);
    });
  }

  function linkifyUrls(container) {
    const regex = /(https?:\/\/[^\s<>"]+)/g;
    container.querySelectorAll("p, li").forEach((el) => {
      el.childNodes.forEach((node) => {
        if (node.nodeType === Node.TEXT_NODE) {
          const replaced = node.textContent.replace(regex, (url) => {
            return `<a href="${url}" target="_blank">${url}</a>`;
          });
          if (replaced !== node.textContent) {
            const span = document.createElement("span");
            span.innerHTML = replaced;
            el.replaceChild(span, node);
          }
        }
      });
    });
  }

  function reinitPostContent(container) {
    rebuildToc();
    numberHeadings(container);
    linkifyUrls(container);
    if (typeof MathJax !== "undefined" && MathJax.typesetPromise) {
      MathJax.typesetPromise([container]);
    }
  }

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

  function createLockUi() {
    const ui = document.createElement("div");
    ui.className = "lock-ui";
    ui.innerHTML = `
      <div class="lock-message">此文章已加密，请输入密码查看：</div>
      <div class="lock-form">
        <input type="password" class="lock-input" placeholder="密码" autocomplete="off" />
        <button type="button" class="lock-button">解锁</button>
      </div>
      <div class="lock-error"></div>
    `;
    return ui;
  }

  async function decryptAndRender(password, ciphertext, container) {
    const html = await decrypt(ciphertext, password);
    const content = document.createElement("div");
    content.className = "unlocked-content";
    content.innerHTML = html;
    container.replaceWith(content);
    reinitPostContent(content);
  }

  function showUnlockUi(container, ciphertext) {
    const ui = createLockUi();
    container.replaceWith(ui);

    const input = ui.querySelector(".lock-input");
    const button = ui.querySelector(".lock-button");
    const error = ui.querySelector(".lock-error");

    async function unlock() {
      const password = input.value;
      if (!password) {
        error.textContent = "请输入密码。";
        return;
      }
      error.textContent = "";
      button.disabled = true;
      button.textContent = "解锁中...";

      try {
        await decryptAndRender(password, ciphertext, ui);
      } catch (e) {
        error.textContent = "密码错误，请重试。";
        button.disabled = false;
        button.textContent = "解锁";
      }
    }

    button.addEventListener("click", unlock);
    input.addEventListener("keypress", function (e) {
      if (e.key === "Enter") unlock();
    });
    input.focus();
  }

  document.addEventListener("DOMContentLoaded", function () {
    const container = document.querySelector(".locked-content");
    if (!container) return;

    const ciphertext = container.getAttribute("data-ciphertext");
    if (!ciphertext) return;

    const cachedPassword = getCachedPassword();
    if (cachedPassword) {
      decryptAndRender(cachedPassword, ciphertext, container).catch(() => {
        showUnlockUi(container, ciphertext);
      });
    } else {
      showUnlockUi(container, ciphertext);
    }
  });
})();
