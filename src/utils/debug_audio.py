import sounddevice as sd

def debug_devices():
    print("Full Device Information:")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        print(f"ID {i}: {dev['name']}")
        print(f"   API: {sd.query_hostapis(dev['hostapi'])['name']}")
        print(f"   Inputs: {dev['max_input_channels']}, Outputs: {dev['max_output_channels']}")
        # Look for any hints of loopback in the full dict
        for key, value in dev.items():
            if 'loopback' in str(key).lower() or 'loopback' in str(value).lower():
                print(f"   !!! Found Loopback hint: {key}={value}")
    
    print("\nChecking WasapiSettings available arguments:")
    import inspect
    try:
        sig = inspect.signature(sd.WasapiSettings.__init__)
        print(f"WasapiSettings.__init__ signature: {sig}")
    except Exception as e:
        print(f"Could not check signature: {e}")

if __name__ == "__main__":
    debug_devices()
