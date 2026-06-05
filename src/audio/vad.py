import torch
import numpy as np

class VADHandler:
    def __init__(self, model_path=None, threshold=0.3, sampling_rate=16000):
        # Added skip_validation=True to bypass GitHub API rate limits (403 Error)
        # Added trust_repo=True to avoid interactive confirmation
        self.model, utils = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                           model='silero_vad',
                                           force_reload=False,
                                           trust_repo=True,
                                           skip_validation=True)
        (self.get_speech_timestamps, self.save_audio, self.read_audio, self.VADIterator, self.collect_chunks) = utils
        self.sampling_rate = sampling_rate
        self.threshold = threshold
        self.iterator = self.VADIterator(self.model, threshold=self.threshold, sampling_rate=self.sampling_rate)

    def is_speech(self, audio_chunk):
        # audio_chunk should be a 1D numpy array or torch tensor
        if isinstance(audio_chunk, np.ndarray):
            audio_chunk = torch.from_numpy(audio_chunk).float()
        
        # Ensure it's 1D
        if audio_chunk.ndim > 1:
            audio_chunk = audio_chunk.squeeze()

        # The iterator maintains state (start/end of speech)
        speech_dict = self.iterator(audio_chunk, return_seconds=True)
        return speech_dict

    def reset(self):
        self.iterator.reset_states()
