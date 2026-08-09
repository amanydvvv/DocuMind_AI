"""
DocuMind AI — RAG Engine & Integration Test Suite
Validates document upload, background ingestion, hybrid retrieval, and LLM Q&A generation.
"""

import pytest
import os
import uuid
import tempfile
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import engine, async_session
from app.services.ingestion import ingest_document
from app.services.retrieval import retrieve_context


@pytest.mark.asyncio
async def test_full_rag_integration_pipeline():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. User Auth Signup
        email = f"testuser_{uuid.uuid4().hex[:6]}@example.com"
        password = "password1234"
        res = await client.post("/api/auth/signup", json={"email": email, "password": password})
        assert res.status_code == 201, f"Signup failed: {res.text}"
        token = res.json()["access_token"]
        user_id = uuid.UUID(res.json()["user_id"])
        client.headers.update({"Authorization": f"Bearer {token}"})

        # 2. Server Health Check
        health_res = await client.get("/api/health")
        assert health_res.status_code == 200, f"Health check failed: {health_res.text}"
        health_data = health_res.json()
        assert health_data["status"] in ["healthy", "degraded", "unhealthy"]

        # 3. Document Upload & Ingestion
        unique_id = str(uuid.uuid4())
        content = f"Project Xyzzy is a highly classified initiative to develop a new propulsion system. The lead engineer is Dr. Samantha Carter. It was started in 2024. Random ID: {unique_id}"

        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_file:
            tmp_file.write(content.encode("utf-8"))
            file_path = tmp_file.name

        try:
            with open(file_path, "rb") as f:
                files = {"file": ("test_document.md", f, "text/markdown")}
                upload_res = await client.post("/api/documents/upload", files=files)

            assert upload_res.status_code == 201, f"Expected 201, got {upload_res.status_code}. Response: {upload_res.text}"
            doc_data = upload_res.json()
            assert "id" in doc_data, "No id in response"
            doc_id = doc_data["id"]

            # Ingest document
            await ingest_document(str(doc_id), file_path)

            # Check completed status
            get_res = await client.get(f"/api/documents/{doc_id}")
            assert get_res.status_code == 200
            status_data = get_res.json()
            assert status_data["status"] == "completed"
            assert status_data.get("chunk_count", 0) > 0

            # 4. Chat Q&A — Clear Match
            payload_clear = {"question": "Who is the lead engineer for Project Xyzzy?"}
            chat_res = await client.post("/api/chat", json=payload_clear)
            if chat_res.status_code == 429:
                pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
            assert chat_res.status_code == 200, f"Expected 200, got {chat_res.status_code}. Response: {chat_res.text}"
            chat_data = chat_res.json()
            assert "answer" in chat_data
            assert "Samantha Carter" in chat_data["answer"] or "Carter" in chat_data["answer"], f"Answer did not contain expected keyword: {chat_data['answer']}"
            assert "citations" in chat_data
            assert len(chat_data["citations"]) > 0, "Citations list is empty"

            # 5. Chat Q&A — Out of Context
            payload_ooc = {"question": "What is the budget for Project Xyzzy?"}
            ooc_res = await client.post("/api/chat", json=payload_ooc)
            if ooc_res.status_code == 429:
                pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
            assert ooc_res.status_code == 200
            ooc_data = ooc_res.json()
            answer_lower = ooc_data["answer"].lower()
            assert any(x in answer_lower for x in ["not find", "couldn't find", "don't have enough", "not mentioned", "not provided", "no information", "cannot answer", "cover"]), f"Fabricated answer detected: {ooc_data['answer']}"

            # 6. Chat Q&A — Nonsense
            payload_nonsense = {"question": "asdf qwerty!@#$"}
            nonsense_res = await client.post("/api/chat", json=payload_nonsense)
            if nonsense_res.status_code == 429:
                pytest.skip("Google Gemini API free tier rate limit / quota exhausted (HTTP 429)")
            assert nonsense_res.status_code == 200
            nonsense_data = nonsense_res.json()
            assert "answer" in nonsense_data

            # 7. Direct Service — Hybrid Retrieval Exact Keyword
            async with async_session() as db:
                results_kw = await retrieve_context("propulsion system Samantha Carter", db, user_id=user_id)
                assert len(results_kw) > 0, "Hybrid retrieval should return matched chunks for keyword query"
                chunk, score, filename = results_kw[0]
                assert score > 0.0, "Top chunk score should be greater than 0"
                assert filename is not None

            # 8. Direct Service — Hybrid Retrieval Semantic Match
            async with async_session() as db:
                results_sem = await retrieve_context("classified space drive initiative", db, user_id=user_id)
                assert len(results_sem) > 0, "Hybrid retrieval should return matched chunks for semantic query"
                chunk, score, filename = results_sem[0]
                assert score >= 0.0

            # 9. Direct Service — RRF Fused Ranking
            async with async_session() as db:
                results_rrf = await retrieve_context("Project Xyzzy 2024", db, user_id=user_id)
                assert len(results_rrf) <= 5, "Final top-K should be capped at 5 chunks"
                if len(results_rrf) > 1:
                    assert results_rrf[0][1] >= results_rrf[1][1]

        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

    await engine.dispose()
