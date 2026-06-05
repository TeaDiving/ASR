(function () {
  const OVERLAY_ID = "asr-translation-subtitle-overlay";

  function ensureOverlay() {
    let overlay = document.getElementById(OVERLAY_ID);

    if (overlay) {
      return overlay;
    }

    overlay = document.createElement("div");
    overlay.id = OVERLAY_ID;
    overlay.style.position = "fixed";
    overlay.style.left = "50%";
    overlay.style.bottom = "7vh";
    overlay.style.transform = "translateX(-50%)";
    overlay.style.width = "min(920px, calc(100vw - 32px))";
    overlay.style.padding = "14px 18px";
    overlay.style.borderRadius = "8px";
    overlay.style.background = "rgba(8, 12, 18, 0.84)";
    overlay.style.color = "#ffffff";
    overlay.style.fontFamily =
      'Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif';
    overlay.style.textAlign = "center";
    overlay.style.zIndex = "2147483647";
    overlay.style.boxShadow = "0 12px 36px rgba(0, 0, 0, 0.32)";
    overlay.style.pointerEvents = "none";
    overlay.style.display = "none";

    overlay.innerHTML = `
      <div data-asr-source style="font-size: 16px; line-height: 1.45; opacity: 0.82;"></div>
      <div data-asr-translation style="font-size: 24px; line-height: 1.35; font-weight: 700; margin-top: 4px;"></div>
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
