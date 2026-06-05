# AI Simultaneous Interpretation Assistant (ASR Component)

This is the backend component for an AI-powered simultaneous interpretation tool. It handles real-time audio capture, voice activity detection (VAD), and automated speech recognition (ASR).

## Core Technologies
- **ASR Engine:** `faster-whisper` for high-performance inference.
- **VAD:** `silero-vad` for robust speech endpoint detection.
- **Audio Capture:** `sounddevice` (supports WASAPI loopback on Windows).
- **Communication:** `websockets` for streaming text results to the translation module (Person B).

## Project Structure
- `src/main.py`: Main entry point and orchestration.
- `src/audio/`: Audio capture and VAD logic.
- `src/asr/`: Whisper model integration.
- `src/server/`: WebSocket server for data transmission.
- `src/utils/`: Utility scripts (e.g., device listing).

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. (Windows) Find your loopback device index:
   ```bash
   python src/utils/list_devices.py
   ```
3. Run the system:
   ```bash
   python src/main.py
   ```

## Next Steps
- Implement system-level audio loopback selection in `AudioCapturer`.
- Optimize chunking strategy for lower latency.
- Integrate with Person B's translation module.
