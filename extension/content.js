(function () {
  const OVERLAY_ID = "asr-translation-subtitle-overlay";
  const OVERLAY_STYLE_ID = "asr-translation-subtitle-overlay-style";

  function ensureOverlayStyles() {
    if (document.getElementById(OVERLAY_STYLE_ID)) {
      return;
    }

    const style = document.createElement("style");
    style.id = OVERLAY_STYLE_ID;
    style.textContent = `
      #${OVERLAY_ID} {
        position: fixed;
        left: 50%;
        bottom: calc(88px + env(safe-area-inset-bottom));
        transform: translateX(-50%);
        width: min(860px, calc(100vw - 32px));
        max-width: calc(100vw - 32px);
        padding: 18px 22px;
        border-radius: 10px;
        background: rgba(0, 0, 0, 0.72);
        color: #ffffff;
        font-family: Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
        text-align: center;
        z-index: 2147483647;
        box-shadow: 0 14px 40px rgba(0, 0, 0, 0.34);
        pointer-events: none;
        white-space: normal;
        overflow-wrap: anywhere;
        word-break: break-word;
        display: none;
      }

      #${OVERLAY_ID} .asr-subtitle-english {
        color: #ffffff;
        font-size: 16px;
        line-height: 1.45;
        opacity: 0.88;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      #${OVERLAY_ID} .asr-subtitle-chinese {
        color: #ffffff;
        font-size: 28px;
        line-height: 1.35;
        font-weight: 700;
        margin-top: 6px;
        overflow-wrap: anywhere;
        word-break: break-word;
      }

      @media (max-width: 640px) {
        #${OVERLAY_ID} {
          width: calc(100vw - 24px);
          max-width: calc(100vw - 24px);
          bottom: calc(72px + env(safe-area-inset-bottom));
          padding: 12px 14px;
          border-radius: 8px;
        }

        #${OVERLAY_ID} .asr-subtitle-english {
          font-size: 14px;
          line-height: 1.4;
        }

        #${OVERLAY_ID} .asr-subtitle-chinese {
          font-size: 22px;
          line-height: 1.35;
          margin-top: 4px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function ensureOverlay() {
    ensureOverlayStyles();

    let overlay = document.getElementById(OVERLAY_ID);

    if (overlay) {
      return overlay;
    }

    overlay = document.createElement("div");
    overlay.id = OVERLAY_ID;
    overlay.style.pointerEvents = "none";
    overlay.style.display = "none";

    overlay.innerHTML = `
      <div data-asr-source class="asr-subtitle-english"></div>
      <div data-asr-translation class="asr-subtitle-chinese"></div>
    `;

    document.body.appendChild(overlay);
    return overlay;
  }

  function renderSubtitle(sourceText, translatedText) {
    const overlay = ensureOverlay();
    overlay.querySelector("[data-asr-source]").textContent = sourceText || "";
    overlay.querySelector("[data-asr-translation]").textContent = translatedText || "";
    overlay.style.display = "block";
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) {
      return false;
    }

    if (message.type === "ASR_SHOW_OVERLAY") {
      renderSubtitle("Subtitle overlay ready", "字幕层已就绪");
      sendResponse({ ok: true });
      return true;
    }

    if (message.type === "ASR_HIDE_OVERLAY") {
      const overlay = document.getElementById(OVERLAY_ID);
      if (overlay) {
        overlay.style.display = "none";
      }
      sendResponse({ ok: true });
      return true;
    }

    if (message.type === "ASR_RENDER_SUBTITLE") {
      renderSubtitle(message.normalizedText, message.translatedText);
      sendResponse({ ok: true });
      return true;
    }

    return false;
  });
})();
