import asyncio
import argparse
import sys
import numpy as np
from audio.capture import AudioCapturer
from audio.vad import VADHandler
from asr.whisper import WhisperASR
import websockets
import json
import sounddevice as sd
import time

class ASRSystem:
    def __init__(self, device_index=None, model_size="base", backend_url="ws://127.0.0.1:8000/ws/asr"):
        self.capturer = AudioCapturer(device_index=device_index, samplerate=16000, blocksize=512)
        self.vad = VADHandler()
        self.asr = WhisperASR(model_size=model_size, device="cpu") 
        self.backend_url = backend_url
        self.ws = None
        
        self.audio_buffer = []
        self.is_running = False
        self.last_partial_time = 0
        self.is_processing = False # Prevent overlapping transcription tasks

    async def connect_backend(self):
        while self.is_running:
            try:
                print(f"Connecting to backend at {self.backend_url}...")
                async with websockets.connect(self.backend_url) as websocket:
                    self.ws = websocket
                    print("Connected to backend.")
                    await websocket.wait_closed()
            except Exception as e:
                print(f"WebSocket connection error: {e}. Retrying in 3s...")
                self.ws = None
                await asyncio.sleep(3)

    async def process_audio(self):
        print("\n>>> ASR Streaming Mode is LIVE!", flush=True)
        segment_id = 0
        in_speech = False
        silence_counter = 0
        
        while self.is_running:
            try:
                if not self.capturer.audio_queue.empty():
                    chunk = self.capturer.audio_queue.get_nowait().flatten()
                    peak = np.max(np.abs(chunk)) 
                    
                    speech_dict = self.vad.is_speech(chunk)
                    if speech_dict:
                        if 'start' in speech_dict: 
                            in_speech = True; silence_counter = 0
                        elif 'end' in speech_dict: 
                            in_speech = False

                    # GATING: Higher threshold to ignore minor noise/hiss
                    if in_speech or peak > 0.1:
                        self.audio_buffer.append(chunk)
                        silence_counter = 0 
                    else:
                        if len(self.audio_buffer) > 0:
                            silence_counter += 1
                    
                    current_time = time.time()
                    # LOGIC 1: Partial updates (now non-blocking and throttled)
                    if in_speech and not self.is_processing and (current_time - self.last_partial_time > 1.2):
                        if len(self.audio_buffer) > 30:
                            # Fire and forget task to keep the audio loop running smoothly
                            asyncio.create_task(self.do_transcribe(segment_id, is_final=False))
                            self.last_partial_time = current_time

                    # LOGIC 2: Finalize on silence
                    should_finalize = False
                    if not in_speech and len(self.audio_buffer) > 0:
                        if silence_counter > 10: 
                            should_finalize = True
                    
                    if len(self.audio_buffer) > 800: 
                        should_finalize = True

                    if should_finalize and not self.is_processing:
                        if len(self.audio_buffer) > 40:
                            await self.do_transcribe(segment_id, is_final=True)
                            segment_id += 1
                        self.audio_buffer = []
                        in_speech = False
                        silence_counter = 0
                else:
                    await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Loop Error: {e}")

    async def do_transcribe(self, segment_id, is_final=False):
        # Don't allow multiple partials to run at once
        if not self.audio_buffer or (self.is_processing and not is_final): return
        
        self.is_processing = True
        audio_to_process = np.concatenate(self.audio_buffer)
        
        try:
            # text, lang, confidence
            text, lang, confidence = await asyncio.to_thread(self.asr.transcribe, audio_to_process)
            
            if text:
                # Relaxed confidence gate for partials
                if not is_final and confidence < -1.0:
                    self.is_processing = False
                    return

                prefix = ">>> " if not is_final else "FINAL: "
                print(f"{prefix}({lang}) [{confidence:.2f}] {text}          ", end="\r" if not is_final else "\n", flush=True)
                
                if self.ws:
                    try:
                        await self.ws.send(json.dumps({
                            "id": str(segment_id),
                            "text": text,
                            "language": lang,
                            "is_final": is_final
                        }))
                    except Exception as e:
                        print(f"Send Error: {e}")
        except Exception as e:
            print(f"Transcribe Error: {e}")
        finally:
            self.is_processing = False

    async def run(self):
        self.is_running = True
        try:
            self.capturer.start()
        except Exception as e:
            print(f"Capture Error: {e}"); return
        await asyncio.gather(self.connect_backend(), self.process_audio())

    def stop(self):
        self.is_running = False
        self.capturer.stop()

def list_devices_briefly():
    print("\nAvailable Audio Devices (Inputs & Outputs):")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    for i, dev in enumerate(devices):
        api_name = hostapis[dev['hostapi']]['name']
        # Show all devices that could potentially be used
        direction = ""
        if dev['max_input_channels'] > 0: direction += " [Input]"
        if dev['max_output_channels'] > 0: direction += " [Output/Loopback]"
        
        if direction:
            print(f"[{i}] {dev['name']} ({api_name}){direction}")
    print("")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", type=int)
    parser.add_argument("--model", type=str, default="base")
    args = parser.parse_args()
    if args.device is None:
        list_devices_briefly()
        val = input("Device ID: ")
        args.device = int(val) if val.strip() else None
    system = ASRSystem(device_index=args.device, model_size=args.model)
    try:
        asyncio.run(system.run())
    except KeyboardInterrupt:
        system.stop()
