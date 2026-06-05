## ASR Person B Service

Start the WebSocket receiving service on port 8765:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

Person A sends ASR JSON messages to:

```text
ws://localhost:8765/ws/asr
```

Open the webpage plugin after starting the service:

```text
http://127.0.0.1:8765/plugin
```

The plugin lets users enter their own XFYUN API credentials and English text for translation.

Load the browser extension prototype from:

```text
extension/
```

In Chrome or Edge, open the extensions page, enable developer mode, and load `extension/` as an unpacked extension. The popup lets users save XFYUN API credentials, send English test text to `/api/translate`, and render the translated Chinese subtitle overlay on the current webpage.

XFYUN machine translation credentials:

- `.env`: private credentials, keep locally and do not upload.
- `.env.example`: blank template, share with teammates.
- `.gitignore`: blocks `.env` from being uploaded and leaking API keys.

Create your local `.env` from `.env.example`, then fill in:

```text
XFYUN_APP_ID=your_app_id
XFYUN_API_KEY=your_api_key
XFYUN_API_SECRET=your_api_secret
```

Successful ASR messages return both `normalizedText` and `translatedText`.
