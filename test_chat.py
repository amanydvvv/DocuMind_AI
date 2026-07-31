import requests
import json
import sys

def test_chat():
    url = "http://localhost:8000/api/chat"
    
    # Upload first to ensure it's there
    with open("backend/test_document.md", "rb") as f:
        resp = requests.post("http://localhost:8000/api/documents/upload", files={"file": f})
    
    # Wait for processing
    import time
    doc_id = resp.json().get("id")
    if not doc_id:
        docs = requests.get("http://localhost:8000/api/documents").json().get("documents", [])
        for d in docs:
            if d["filename"] == "test_document.md":
                doc_id = d["id"]
                break
    
    time.sleep(2) # Give it a second if it just uploaded
            
    payload = {
        "question": "Who is the lead engineer for Project Xyzzy?",
        "document_id": doc_id
    }
    print("Testing /api/chat with:", payload)
    
    resp = requests.post(url, json=payload)
    print(f"Status Code: {resp.status_code}")
    print("Response Headers:", resp.headers)
    print("Response Body:")
    try:
        data = resp.json()
        print(json.dumps(data, indent=2))
        
        # Test second turn if first turn succeeds
        if resp.status_code == 200 and "conversation_id" in data:
            conv_id = data["conversation_id"]
            payload2 = {
                "question": "What is the budget for that project?",
                "conversation_id": conv_id,
                "document_id": doc_id
            }
            print("\nTesting turn 2 with:", payload2)
            resp2 = requests.post(url, json=payload2)
            print(f"Status Code: {resp2.status_code}")
            print(json.dumps(resp2.json(), indent=2))
            
    except Exception as e:
        print("Failed to parse JSON:", str(e))
        print("Raw text:", resp.text)
        sys.exit(1)

if __name__ == "__main__":
    test_chat()
