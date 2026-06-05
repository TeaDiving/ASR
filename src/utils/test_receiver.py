import asyncio
import websockets
import json

async def receive_results():
    uri = "ws://localhost:8765"
    print(f"Connecting to ASR server at {uri}...")
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Waiting for transcription results...\n")
            while True:
                message = await websocket.recv()
                
                # 1. 打印原始的 JSON 字符串
                print(f"[RAW JSON RECEIVED] {message}")
                
                # 2. 解析 JSON 并提取内容
                data = json.loads(message)
                print(f"[PARSED CONTENT] text: {data['text']}, lang: {data['language']}\n")
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(receive_results())
