# PR1: Scope Pf Responsibilities

## Summary

PR1 defines the data handoff boundary between Person A and Person B.
PR2 implements the WebSocket JSON receiving entrypoint for Person B. This document does not define translation, correction, or subtitle UI behavior.

## Module Boundary

Person A is responsible for:

```text
audio capture -> real-time audio processing -> Whisper recognition -> send ASR JSON message over WebSocket
```

Person B is responsible for:

```text
receive ASR JSON message over WebSocket -> correction -> AI translation -> subtitle packaging -> subtitle display
```

The boundary between Person A and Person B is:

```text
WebSocket JSON message
```

Person A sends the latest English recognition result to Person B through WebSocket.
Person B starts processing from the English text field in the received JSON message.

## WebSocket Handoff

The WebSocket endpoint is:

```text
ws://localhost:8765/ws/asr
```

The example payload file path is:

```text
data/asr-output.example.json
```

## ASRTextMessage

Person A must send one `ASRTextMessage` object to `/ws/asr`.

```json
{
  "id": "asr_001",
  "text": "Good morning everyone.",
  "timestamp": 1710000000000,
  "isFinal": true
}
```

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | yes | Unique ID for the current recognition result |
| `text` | string | yes | English text recognized by Whisper |
| `timestamp` | number | yes | Recognition result time in milliseconds |
| `isFinal` | boolean | yes | Whether this recognition result is final |

## Handoff Rules

- Person A sends the latest recognition result to `ws://localhost:8765/ws/asr`.
- Person B depends only on the JSON fields defined in `ASRTextMessage`.
- Person B does not depend on Person A's audio capture, audio stream processing, or Whisper implementation.
- `data/asr-output.example.json` is only an example payload, not a runtime handoff file.
- PR2 only implements the receiving entrypoint and acknowledgement response.

## Acceptance Criteria

- Person A knows the exact WebSocket endpoint to send to.
- Person B can receive `ASRTextMessage` messages through `/ws/asr`.
- Both sides use `text` as the English recognition text field.
- `data/asr-output.example.json` can be used as the reference example.
- No translation, correction, file watcher, or UI logic is included in PR2.

## Local Run Command

Start Person B's WebSocket service on port 8765:

```bash
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8765 --reload
```
