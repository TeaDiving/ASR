import pyaudiowpatch as pyaudio

def list_wasapi_loopback_devices():
    p = pyaudio.PyAudio()
    try:
        # Get default WASAPI info
        wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
    except OSError:
        print("WASAPI is not available on this system.")
        return

    print("--- WASAPI Loopback Devices ---")
    default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
    
    if not default_speakers["isLoopbackDevice"]:
        for loopback in p.get_loopback_device_info_generator():
            print(f"ID {loopback['index']}: {loopback['name']}")
    
    p.terminate()

if __name__ == "__main__":
    list_wasapi_loopback_devices()
