import sounddevice as sd

def list_audio_devices():
    print("Available Audio Devices:")
    devices = sd.query_devices()
    hostapis = sd.query_hostapis()
    
    for i, dev in enumerate(devices):
        api_name = hostapis[dev['hostapi']]['name']
        print(f"{i}: {dev['name']}")
        print(f"   API: {api_name}, Max Inputs: {dev['max_input_channels']}, Max Outputs: {dev['max_output_channels']}")
        
        # Highlight Windows WASAPI Loopback devices
        if 'wasapi' in api_name.lower() and dev['max_input_channels'] > 0:
             print(f"   [Found Potential Input/Loopback Device]")

if __name__ == "__main__":
    list_audio_devices()
