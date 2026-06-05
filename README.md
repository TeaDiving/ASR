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

XFYUN credentials:

- `.env`: private credentials, keep locally and do not upload.
- `.env.example`: blank template, share with teammates.
- `.gitignore`: blocks `.env` from being uploaded and leaking API keys.

Create your local `.env` from `.env.example`, then fill in:

```text
XF_APPID=your_app_id
XF_APIKEY=your_api_key
XF_SECRET=your_api_secret
XF_SPARK_API_URL=wss://spark-api.xf-yun.com/v4.0/chat
XF_SPARK_DOMAIN=4.0Ultra
```

The same XFYUN credential set is used for machine translation and Spark AI correction. Successful ASR messages return both `normalizedText` and `translatedText`.

Create a subtitle result object:

```text
POST http://127.0.0.1:8765/api/subtitle
```

```json
{
  "text": "Good morning everyone.",
  "isFinal": true,
  "xfyunCredentials": {
    "appId": "your_app_id",
    "apiKey": "your_api_key",
    "apiSecret": "your_api_secret"
  }
}
```

The response includes `id`, `sourceText`, `normalizedText`, `translatedText`, `timestamp`, and `isFinal`.

Subscribe to realtime subtitle results:

```text
GET http://127.0.0.1:8765/api/subtitle/stream
```

The stream uses SSE and emits `subtitle` events whenever `POST /api/subtitle` successfully creates a new subtitle object.
