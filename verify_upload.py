import time
import requests
import sys

API_URL = "http://localhost:8000/api/documents"
FILE_PATH = "backend/test_document.md"

def upload_and_poll():
    # First, list documents and delete any existing test_document.md to avoid 409
    docs = requests.get(API_URL).json().get("documents", [])
    for doc in docs:
        if doc["filename"] == "test_document.md":
            print(f"Deleting existing document: {doc['id']}")
            requests.delete(f"{API_URL}/{doc['id']}")

    print(f"Uploading {FILE_PATH}...")
    with open(FILE_PATH, "rb") as f:
        files = {"file": f}
        resp = requests.post(f"{API_URL}/upload", files=files)
        
    if resp.status_code != 201:
        print(f"Upload failed: {resp.status_code} - {resp.text}")
        sys.exit(1)
        
    doc = resp.json()
    doc_id = doc["id"]
    print(f"Upload successful. Document ID: {doc_id}")
    
    print("Polling for completion...")
    for _ in range(30): # Wait up to 60s
        resp = requests.get(f"{API_URL}/{doc_id}")
        if resp.status_code != 200:
            print(f"Failed to fetch status: {resp.status_code}")
            sys.exit(1)
            
        doc = resp.json()
        print(f"Status: {doc['status']}, Chunks: {doc.get('chunk_count', 0)}")
        if doc["status"] == "completed":
            print("Processing completed successfully!")
            print(doc)
            sys.exit(0)
        elif doc["status"] == "error":
            print(f"Processing failed: {doc.get('error_message')}")
            sys.exit(1)
            
        time.sleep(2)
        
    print("Timeout waiting for completion.")
    sys.exit(1)

if __name__ == "__main__":
    upload_and_poll()
