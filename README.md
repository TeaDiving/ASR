## ASR Person B Service

Start the WebSocket receiving service on port 8765:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```

Person A sends ASR JSON messages to:

```text
ws://localhost:8765/ws/asr
```
