from faster_whisper import WhisperModel
import numpy as np

class WhisperASR:
    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        print(f"--- Loading Whisper model '{model_size}' (this may take a minute)... ---")
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        print(f"--- Whisper model '{model_size}' is READY! ---")

    def transcribe(self, audio_data):
        # Optimized for maximum speed (latency-first)
        segments, info = self.model.transcribe(
            audio_data, 
            beam_size=1, # FASTEST mode
            vad_filter=True, 
            vad_parameters=dict(min_silence_duration_ms=500),
            no_speech_threshold=0.8,
            condition_on_previous_text=False
        )
        
        full_text = ""
        avg_logprob = 0
        count = 0
        for segment in segments:
            full_text += segment.text
            avg_logprob += segment.avg_logprob
            count += 1
            
        final_confidence = avg_logprob / count if count > 0 else -1.0
        return full_text.strip(), info.language, final_confidence
