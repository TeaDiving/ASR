import pyaudiowpatch as pyaudio
import numpy as np
import queue
import scipy.signal

class AudioCapturer:
    def __init__(self, device_index=None, samplerate=16000, channels=1, blocksize=512):
        self.pa = pyaudio.PyAudio()
        self.device_index = device_index
        self.target_samplerate = samplerate
        self.target_channels = channels
        self.target_blocksize = blocksize # Usually 512 for Silero VAD
        self.audio_queue = queue.Queue()
        self.stream = None
        
        # If no index provided, find default loopback
        if self.device_index is None:
            self.device_index = self._find_default_loopback()

        # Query device info
        dev_info = self.pa.get_device_info_by_index(self.device_index)
        self.native_samplerate = int(dev_info["defaultSampleRate"])
        self.native_channels = dev_info["maxInputChannels"]
        
        # CALCULATE: How many native frames do we need to get exactly target_blocksize samples?
        self.frames_to_request = int(self.target_blocksize * (self.native_samplerate / self.target_samplerate))

        print(f"Initializing PyAudioWPatch on Device {self.device_index}")
        print(f"Native: {self.native_samplerate}Hz, {self.native_channels}ch")
        print(f"Requesting {self.frames_to_request} frames per buffer.")

    def _find_default_loopback(self):
        wasapi_info = self.pa.get_host_api_info_by_type(pyaudio.paWASAPI)
        default_speakers = self.pa.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
        if not default_speakers["isLoopbackDevice"]:
            for loopback in self.pa.get_loopback_device_info_generator():
                if default_speakers["name"] in loopback["name"]:
                    return loopback["index"]
        return wasapi_info["defaultOutputDevice"]

    def _callback(self, in_data, frame_count, time_info, status):
        data = np.frombuffer(in_data, dtype=np.float32)
        
        # 1. Handle Multiple Channels
        if self.native_channels > 1:
            data = data.reshape(-1, self.native_channels)
            data = np.mean(data, axis=1) 
            
        # 2. Resample (This will now result in exactly self.target_blocksize)
        if self.native_samplerate != self.target_samplerate:
            data = scipy.signal.resample(data, self.target_blocksize)
            
        self.audio_queue.put(data.astype(np.float32))
        return (None, pyaudio.paContinue)

    def start(self):
        try:
            print(f"Opening PyAudio Stream on Device {self.device_index}...")
            self.stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=self.native_channels,
                rate=self.native_samplerate,
                input=True,
                input_device_index=self.device_index,
                stream_callback=self._callback,
                frames_per_buffer=self.frames_to_request
            )
            print("Audio Stream STARTED (PyAudioWPatch)")
        except Exception as e:
            print(f"!!! PyAudio ERROR: {e}")
            raise

    def stop(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        self.pa.terminate()

    def get_audio(self):
        return self.audio_queue.get()
