const form = document.querySelector("#settings-form");
const statusElement = document.querySelector("#status");
const resultElement = document.querySelector("#result");
const saveButton = document.querySelector("#save-button");
const overlayButton = document.querySelector("#overlay-button");
const hideButton = document.querySelector("#hide-button");
const translateButton = document.querySelector("#translate-button");

const STORAGE_KEYS = ["backendUrl", "appId", "apiKey", "apiSecret"];

function setStatus(message, isError = false) {
  statusElement.textContent = message;
  statusElement.classList.toggle("error", isError);
}

function getFormValues() {
  const formData = new FormData(form);
  return {
    backendUrl: String(formData.get("backendUrl") || "").replace(/\/+$/, ""),
    appId: String(formData.get("appId") || ""),
    apiKey: String(formData.get("apiKey") || ""),
    apiSecret: String(formData.get("apiSecret") || ""),
    text: String(formData.get("text") || ""),
  };
}

async function getActiveTab() {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  return tab;
}

async function sendToActiveTab(message) {
  const tab = await getActiveTab();

  if (!tab || !tab.id) {
    throw new Error("No active tab");
  }

  return chrome.tabs.sendMessage(tab.id, message);
}

async function loadSettings() {
  const values = await chrome.storage.local.get(STORAGE_KEYS);

  for (const key of STORAGE_KEYS) {
    if (values[key]) {
      form.elements[key].value = values[key];
    }
  }
}

async function saveSettings() {
  const values = getFormValues();
  await chrome.storage.local.set({
    backendUrl: values.backendUrl,
    appId: values.appId,
    apiKey: values.apiKey,
    apiSecret: values.apiSecret,
  });
  setStatus("API settings saved");
}

async function translateText(event) {
  event.preventDefault();
  const values = getFormValues();
  translateButton.disabled = true;
  resultElement.classList.remove("visible");
  setStatus("Translating...");

  try {
    await saveSettings();
    const response = await fetch(`${values.backendUrl}/api/translate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text: values.text,
        xfyunCredentials: {
          appId: values.appId,
          apiKey: values.apiKey,
          apiSecret: values.apiSecret,
        },
      }),
    });
    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Translation failed");
    }

    resultElement.textContent = data.translatedText;
    resultElement.classList.add("visible");
    await sendToActiveTab({
      type: "ASR_RENDER_SUBTITLE",
      normalizedText: data.normalizedText,
      translatedText: data.translatedText,
    });
    setStatus("Translated and rendered on page");
  } catch (error) {
    setStatus(error.message || "Translation failed", true);
  } finally {
    translateButton.disabled = false;
  }
}

saveButton.addEventListener("click", saveSettings);
overlayButton.addEventListener("click", async () => {
  try {
    await sendToActiveTab({ type: "ASR_SHOW_OVERLAY" });
    setStatus("Overlay shown on current tab");
  } catch (error) {
    setStatus(error.message || "Cannot show overlay", true);
  }
});
hideButton.addEventListener("click", async () => {
  try {
    await sendToActiveTab({ type: "ASR_HIDE_OVERLAY" });
    setStatus("Overlay hidden");
  } catch (error) {
    setStatus(error.message || "Cannot hide overlay", true);
  }
});
form.addEventListener("submit", translateText);

loadSettings();
