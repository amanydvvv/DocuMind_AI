import pytest
import requests
import time
import os
import uuid
import tempfile

BASE_URL = "http://localhost:8000"
STATE = {}

def test_server_health():
    response = requests.get(f"{BASE_URL}/api/health")
    assert response.status_code == 200, f"Health check failed: {response.text}"
    data = response.json()
    assert data["status"] in ["healthy", "degraded", "unhealthy"]

def test_document_upload():
    unique_id = str(uuid.uuid4())
    content = f"Project Xyzzy is a highly classified initiative to develop a new propulsion system. The lead engineer is Dr. Samantha Carter. It was started in 2024. Random ID: {unique_id}"
    
    with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
        tmp_file.write(content.encode("utf-8"))
        file_path = tmp_file.name
        
    try:
        with open(file_path, "rb") as f:
            files = {"file": ("test_document.md", f, "text/markdown")}
            response = requests.post(f"{BASE_URL}/api/documents/upload", files=files)
            
        assert response.status_code == 201, f"Expected 201, got {response.status_code}. Response: {response.text}"
        data = response.json()
        assert "id" in data, "No id in response"
        STATE["document_id"] = data["id"]
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

def test_ingestion_completes():
    doc_id = STATE.get("document_id")
    assert doc_id is not None, "Document ID not found from previous test"
    
    timeout = 30
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(f"{BASE_URL}/api/documents/{doc_id}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        if data["status"] == "completed":
            assert data.get("chunk_count", 0) > 0, "Chunk count should be > 0"
            return
        elif data["status"] == "failed":
            pytest.fail(f"Ingestion failed: {data.get('error_message')}")
            
        time.sleep(2)
        
    pytest.fail(f"Ingestion timed out after {timeout} seconds")

def test_chat_clear_match():
    payload = {"question": "Who is the lead engineer for Project Xyzzy?"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    
    assert "answer" in data
    assert "Samantha Carter" in data["answer"] or "Carter" in data["answer"], "Answer did not contain expected keyword"
    assert "citations" in data
    assert len(data["citations"]) > 0, "Citations list is empty"

def test_chat_not_in_document():
    payload = {"question": "What is the budget for Project Xyzzy?"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    answer_lower = data["answer"].lower()
    assert any(x in answer_lower for x in ["not find", "couldn't find", "don't have enough", "not mentioned", "not provided", "no information", "cannot answer"]), f"Fabricated answer detected: {data['answer']}"

def test_chat_nonsense():
    payload = {"question": "asdf qwerty!@#$"}
    response = requests.post(f"{BASE_URL}/api/chat", json=payload)
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    
    assert "answer" in data
    assert "citations" in data
