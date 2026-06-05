# PR1: Scope Pf Responsibilities

## Summary

PR1 defines the data handoff boundary between Person A and Person B.
It only documents the responsibility scope and JSON file format. It does not implement file reading, file watching, translation, correction, APIs, or subtitle UI.

## Module Boundary

Person A is responsible for:

```text
audio capture -> real-time audio processing -> Whisper recognition -> write ASR JSON file
```

Person B is responsible for:

```text
read ASR JSON file -> correction -> AI translation -> subtitle packaging -> subtitle display
```

The boundary between Person A and Person B is:

```text
data/asr-output.json
```

Person A writes the latest English recognition result into this JSON file.
Person B reads this JSON file in later PRs and starts processing from the English text field.

## Handoff File

The handoff file path is:

```text
data/asr-output.json
```

The example file path is:

```text
data/asr-output.example.json
```

## ASRTextMessage

Person A must write one `ASRTextMessage` object to `data/asr-output.json`.

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

- Person A writes only the latest recognition result to `data/asr-output.json`.
- Person B depends only on the JSON fields defined in `ASRTextMessage`.
- Person B does not depend on Person A's audio capture, audio stream processing, or Whisper implementation.
- PR1 does not implement runtime reading or writing logic.

## Acceptance Criteria

- Person A knows the exact JSON file path to write.
- Person B knows the exact JSON file path to read in later PRs.
- Both sides use `text` as the English recognition text field.
- `data/asr-output.example.json` can be used as the reference example.
- No translation, correction, API, file watcher, or UI logic is included in PR1.
