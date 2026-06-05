import json
from pathlib import Path


EXTENSION_DIR = Path("extension")


def test_extension_manifest_defines_browser_plugin() -> None:
    manifest = json.loads((EXTENSION_DIR / "manifest.json").read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "popup.html"
    assert "storage" in manifest["permissions"]
    assert "activeTab" in manifest["permissions"]
    assert manifest["content_scripts"][0]["js"] == ["content.js"]


def test_extension_popup_collects_api_credentials_and_text() -> None:
    popup_html = (EXTENSION_DIR / "popup.html").read_text(encoding="utf-8")

    assert 'id="app-id"' in popup_html
    assert 'id="api-key"' in popup_html
    assert 'id="api-secret"' in popup_html
    assert 'id="source-text"' in popup_html
    assert 'id="translate-button"' in popup_html


def test_extension_popup_calls_translation_api_and_renders_subtitle() -> None:
    popup_js = (EXTENSION_DIR / "popup.js").read_text(encoding="utf-8")

    assert "/api/translate" in popup_js
    assert "xfyunCredentials" in popup_js
    assert "ASR_RENDER_SUBTITLE" in popup_js


def test_extension_content_script_injects_subtitle_overlay() -> None:
    content_js = (EXTENSION_DIR / "content.js").read_text(encoding="utf-8")

    assert "asr-translation-subtitle-overlay" in content_js
    assert "ASR_SHOW_OVERLAY" in content_js
    assert "ASR_RENDER_SUBTITLE" in content_js
