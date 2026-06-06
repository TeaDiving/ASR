from faster_whisper import WhisperModel
import numpy as np

class WhisperASR:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        print(f"--- Loading Whisper model '{model_size}' (this may take a minute)... ---")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"--- Whisper model '{model_size}' is READY! ---")

    def transcribe(self, audio_data):
        # vad_filter=True is the key to preventing "repetition hallucinations"
        # It strips the silence from the audio before Whisper sees it.
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=5,
            vad_filter=True, 
            vad_parameters=dict(min_silence_duration_ms=500),
            no_speech_threshold=0.65, # Slightly higher to be more strict
            condition_on_previous_text=False
        )
        
        full_text = ""
        for segment in segments:
            full_text += segment.text
            
        return full_text.strip(), info.language
