import asyncio
import argparse
import sys
import numpy as np
from audio.capture import AudioCapturer
from audio.vad import VADHandler
from asr.whisper import WhisperASR
from server.websocket import WebSocketServer
import sounddevice as sd
import time

class ASRSystem:
    def __init__(self, device_index=None, model_size="base"):
        self.capturer = AudioCapturer(device_index=device_index, samplerate=16000, blocksize=512)
        self.vad = VADHandler()
        self.asr = WhisperASR(model_size=model_size, device="cpu") 
        self.ws_server = WebSocketServer()
        
        self.audio_buffer = []
        self.is_running = False
        self.last_partial_time = 0

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
                    
                    # Use VAD to detect speech state
                    speech_dict = self.vad.is_speech(chunk)
                    if speech_dict:
                        if 'start' in speech_dict: 
                            in_speech = True; silence_counter = 0
                        elif 'end' in speech_dict: 
                            in_speech = False

                    # GATING: Only collect audio if we are in speech or sound is significant
                    # This prevents "You" hallucinations from background hiss
                    if in_speech or peak > 0.05:
                        self.audio_buffer.append(chunk)
                        silence_counter = 0 # Reset silence if we hear SOMETHING
                    else:
                        # If we are not in speech, keep silence_counter going
                        if len(self.audio_buffer) > 0:
                            silence_counter += 1
                    
                    # Logic 1: Immediate Feedback (Partial Results)
                    current_time = time.time()
                    if in_speech and (current_time - self.last_partial_time > 1.5):
                        if len(self.audio_buffer) > 30:
                            await self.do_transcribe(segment_id, is_final=False)
                            self.last_partial_time = current_time

                    # Logic 2: Finalize on Silence
                    should_finalize = False
                    if not in_speech and len(self.audio_buffer) > 0:
                        if silence_counter > 12: # 0.35s of consistent silence (Faster!)
                            should_finalize = True
                    
                    # Logic 3: Safety cut at 25 seconds (Whisper limit is 30)
                    if len(self.audio_buffer) > 800: 
                        should_finalize = True

                    if should_finalize:
                        if len(self.audio_buffer) > 40:
                            print(f"\n[FINALIZING] Segment {segment_id}")
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
        if not self.audio_buffer: return
        
        # Don't clear buffer if it's just a partial result
        audio_to_process = np.concatenate(self.audio_buffer)
        
        try:
            # We use beam_size=1 for partial results to make it faster
            text, lang = await asyncio.to_thread(self.asr.transcribe, audio_to_process)
            
            if text:
                prefix = ">>> " if not is_final else "FINAL: "
                print(f"{prefix}({lang}) {text}          ", end="\r" if not is_final else "\n", flush=True)
                
                await self.ws_server.broadcast({
                    "id": segment_id,
                    "text": text,
                    "language": lang,
                    "is_final": is_final
                })
        except Exception as e:
            print(f"Transcribe Error: {e}")

    async def run(self):
        self.is_running = True
        try:
            self.capturer.start()
        except Exception as e:
            print(f"Capture Error: {e}"); return
        await asyncio.gather(self.ws_server.start(), self.process_audio())

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
