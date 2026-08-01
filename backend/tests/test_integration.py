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

def _post_chat_with_retry(payload):
    return requests.post(f"{BASE_URL}/api/chat", json=payload)

def test_chat_clear_match():
    payload = {"question": "Who is the lead engineer for Project Xyzzy?"}
    response = _post_chat_with_retry(payload)
    if response.status_code == 429:
        pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    data = response.json()
    assert "answer" in data
    assert "Samantha Carter" in data["answer"] or "Carter" in data["answer"], "Answer did not contain expected keyword"
    assert "citations" in data
    assert len(data["citations"]) > 0, "Citations list is empty"

def test_chat_not_in_document():
    payload = {"question": "What is the budget for Project Xyzzy?"}
    response = _post_chat_with_retry(payload)
    if response.status_code == 429:
        pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    answer_lower = data["answer"].lower()
    assert any(x in answer_lower for x in ["not find", "couldn't find", "don't have enough", "not mentioned", "not provided", "no information", "cannot answer"]), f"Fabricated answer detected: {data['answer']}"

def test_chat_nonsense():
    payload = {"question": "asdf qwerty!@#$"}
    response = _post_chat_with_retry(payload)
    if response.status_code == 429:
        pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"
    data = response.json()
    assert "answer" in data
    assert "citations" in data

def _run_async(coro):
    import asyncio
    from app.database import engine, async_session
    async def wrapper():
        try:
            return await coro(async_session)
        finally:
            await engine.dispose()
    return asyncio.run(wrapper())

def test_hybrid_retrieval_exact_keyword():
    from app.services.retrieval import retrieve_context
    async def _test(session_factory):
        async with session_factory() as db:
            results = await retrieve_context("propulsion system Samantha Carter", db)
            assert len(results) > 0, "Hybrid retrieval should return matched chunks for keyword query"
            chunk, score, filename = results[0]
            assert score > 0.0, "Top chunk score should be greater than 0"
            assert filename is not None
    _run_async(_test)

def test_hybrid_retrieval_semantic_match():
    from app.services.retrieval import retrieve_context
    async def _test(session_factory):
        async with session_factory() as db:
            results = await retrieve_context("classified space drive initiative", db)
            assert len(results) > 0, "Hybrid retrieval should return matched chunks for semantic query"
            chunk, score, filename = results[0]
            assert score >= 0.0
    _run_async(_test)

def test_rrf_fused_ranking():
    from app.services.retrieval import retrieve_context
    async def _test(session_factory):
        async with session_factory() as db:
            results = await retrieve_context("Project Xyzzy 2024", db)
            assert len(results) <= 5, "Final top-K should be capped at 5 chunks"
            if len(results) > 1:
                assert results[0][1] >= results[1][1]
    _run_async(_test)
