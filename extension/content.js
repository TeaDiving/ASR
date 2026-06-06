(function () {
  const OVERLAY_ID = "asr-translation-subtitle-overlay";
  const OVERLAY_STYLE_ID = "asr-translation-subtitle-overlay-style";
  const DEFAULT_BACKEND_URL = "http://127.0.0.1:8000";

  let subtitleStream = null;
  let isDragging = false;
  let dragStartX, dragStartY;
  let overlayStartX, overlayStartY;

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
        bottom: 100px;
        transform: translateX(-50%);
        width: min(860px, calc(100vw - 32px));
        max-width: calc(100vw - 32px);
        padding: 18px 22px;
        border-radius: 12px;
        background: rgba(0, 0, 0, 0.75);
        backdrop-filter: blur(8px);
        -webkit-backdrop-filter: blur(8px);
        color: #ffffff;
        font-family: Inter, "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
        text-align: center;
        z-index: 2147483647;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        cursor: move;
        user-select: none;
        display: none;
        transition: background 0.2s;
        border: 1px solid rgba(255, 255, 255, 0.1);
      }

      #${OVERLAY_ID}:hover {
        background: rgba(20, 20, 20, 0.85);
      }

      #${OVERLAY_ID} .asr-subtitle-english {
        color: rgba(255, 255, 255, 0.9);
        font-size: 16px;
        line-height: 1.4;
        margin-bottom: 4px;
      }

      #${OVERLAY_ID} .asr-subtitle-chinese {
        color: #ffffff;
        font-size: 26px;
        line-height: 1.3;
        font-weight: 700;
      }

      .asr-drag-handle {
        position: absolute;
        top: 4px;
        left: 50%;
        transform: translateX(-50%);
        width: 40px;
        height: 4px;
        background: rgba(255, 255, 255, 0.2);
        border-radius: 2px;
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
    overlay.innerHTML = `
      <div class="asr-drag-handle"></div>
      <div data-asr-source class="asr-subtitle-english"></div>
      <div data-asr-translation class="asr-subtitle-chinese"></div>
    `;

    document.body.appendChild(overlay);

    // Load saved position
    chrome.storage.local.get(["subtitlePos"], (result) => {
      if (result.subtitlePos) {
        overlay.style.left = result.subtitlePos.x;
        overlay.style.top = result.subtitlePos.y;
        overlay.style.bottom = "auto";
        overlay.style.transform = "none";
      }
    });

    // Drag and drop implementation
    overlay.addEventListener("mousedown", (e) => {
      if (e.button !== 0) return; // Only left click
      isDragging = true;
      dragStartX = e.clientX;
      dragStartY = e.clientY;
      
      const rect = overlay.getBoundingClientRect();
      overlayStartX = rect.left;
      overlayStartY = rect.top;
      
      overlay.style.transition = "none"; // Disable transitions while dragging
      e.preventDefault();
    });

    document.addEventListener("mousemove", (e) => {
      if (!isDragging) return;

      const deltaX = e.clientX - dragStartX;
      const deltaY = e.clientY - dragStartY;

      const newX = overlayStartX + deltaX;
      const newY = overlayStartY + deltaY;

      overlay.style.left = `${newX}px`;
      overlay.style.top = `${newY}px`;
      overlay.style.bottom = "auto";
      overlay.style.transform = "none";
    });

    document.addEventListener("mouseup", () => {
      if (isDragging) {
        isDragging = false;
        overlay.style.transition = "";
        
        // Save position
        chrome.storage.local.set({
          subtitlePos: {
            x: overlay.style.left,
            y: overlay.style.top
          }
        });
      }
    });

    return overlay;
  }

  function renderSubtitle(sourceText, translatedText) {
    const overlay = ensureOverlay();
    overlay.querySelector("[data-asr-source]").textContent = sourceText || "";
    overlay.querySelector("[data-asr-translation]").textContent = translatedText || "";
    overlay.style.display = "block";
  }

  function normalizeBackendUrl(backendUrl) {
    return String(backendUrl || DEFAULT_BACKEND_URL).replace(/\/+$/, "");
  }

  function disconnectSubtitleStream() {
    if (subtitleStream) {
      subtitleStream.close();
      subtitleStream = null;
    }
  }

  function connectSubtitleStream(backendUrl) {
    disconnectSubtitleStream();
    ensureOverlay();

    const streamUrl = `${normalizeBackendUrl(backendUrl)}/api/subtitle/stream`;
    subtitleStream = new EventSource(streamUrl);

    subtitleStream.addEventListener("subtitle", (event) => {
      try {
        const subtitle = JSON.parse(event.data);

        if (!subtitle || !subtitle.translatedText) {
          return;
        }

        renderSubtitle(subtitle.sourceText, subtitle.translatedText);
      } catch (error) {
        console.error("Invalid subtitle stream event", error);
      }
    });

    subtitleStream.onerror = (error) => {
      console.error("Subtitle stream error", error);
    };
  }

  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (!message || !message.type) {
      return false;
    }

    if (message.type === "ASR_START_LIVE_SUBTITLE") {
      connectSubtitleStream(message.backendUrl);
      sendResponse({ ok: true });
      return true;
    }

    if (message.type === "ASR_SHOW_OVERLAY") {
      ensureOverlay().style.display = "block";
      sendResponse({ ok: true });
      return true;
    }

    if (message.type === "ASR_HIDE_OVERLAY") {
      disconnectSubtitleStream();
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
