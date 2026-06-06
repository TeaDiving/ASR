import subprocess
import time
import sys
import os

def run_system():
    print("Starting AI Simultaneous Interpretation Assistant...")
    
    # 1. Start Backend
    print("Launching Backend (FastAPI)...")
    backend_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 2. Wait for backend to be ready
    time.sleep(3)
    
    # 3. Start ASR
    print("Launching ASR Module (Person A)...")
    # Note: ASR module will prompt for device ID if not provided via --device
    asr_process = subprocess.Popen(
        [sys.executable, "src/main.py"],
        stdout=sys.stdout,
        stderr=sys.stderr,
        stdin=sys.stdin
    )
    
    try:
        # Keep the script running
        while True:
            line = backend_process.stdout.readline()
            if line:
                print(f"[Backend] {line.strip()}")
            if backend_process.poll() is not None or asr_process.poll() is not None:
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        backend_process.terminate()
        asr_process.terminate()

if __name__ == "__main__":
    run_system()
