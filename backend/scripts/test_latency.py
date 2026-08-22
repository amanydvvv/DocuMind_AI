import time
import requests
import sys
from pathlib import Path

# Add backend root to path so we can import app modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app.core.security import create_access_token
    token = create_access_token({"sub": "fe796590-ab5a-46af-9b09-772b7a60b385"})
    headers = {"Authorization": f"Bearer {token}"}
except Exception:
    headers = {}

url = "http://localhost:8000/api/chat/stream"  # KueryCore local streaming RAG endpoint
payload = {"question": "What is the main topic of the documents?"}  # Expected payload for KueryCore

print("Testing latency...")

# 1. Test Blocking (Simulates how long a user waits for the FULL response without SSE)
start_blocking = time.perf_counter()
requests.post(url, json=payload, headers=headers)
blocking_time = (time.perf_counter() - start_blocking) * 1000

# 2. Test Streaming (TTFT)
start_streaming = time.perf_counter()
with requests.post(url, json=payload, headers=headers, stream=True) as r:
    first_chunk = next(r.iter_content(chunk_size=1))  # Captures the very first byte/token sent back
streaming_ttft = (time.perf_counter() - start_streaming) * 1000

reduction = blocking_time - streaming_ttft

print(f"Full Wait Time: {blocking_time:.2f} ms")
print(f"Streaming TTFT: {streaming_ttft:.2f} ms")
print(f"Reduction in wait time: {reduction:.2f} ms")
