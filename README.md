## ASR Person B Service

Start the WebSocket receiving service on port 8765:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

Person A sends ASR JSON messages to:

```text
ws://localhost:8765/ws/asr
```

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
