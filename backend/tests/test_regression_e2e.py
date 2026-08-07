import asyncio
import httpx
import json
import sys

BASE = "http://localhost:8000"
TIMEOUT = 30.0

async def test_signup_login():
    """Test signup and login flow."""
    print("=== TEST: Signup + Login ===")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Signup
        email = f"test_{int(asyncio.get_event_loop().time()*1000)}@example.com"
        password = "TestPass123!"
        resp = await client.post(f"{BASE}/api/auth/signup", json={"email": email, "password": password})
        print(f"Signup: {resp.status_code} {resp.text}")
        assert resp.status_code in (200, 201), f"Signup failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        access_token = data["access_token"]
        refresh_token = data["refresh_token"]
        print("Signup OK, got tokens")

        # Login
        resp = await client.post(f"{BASE}/api/auth/login", json={"email": email, "password": password})
        print(f"Login: {resp.status_code} {resp.text}")
        assert resp.status_code == 200, f"Login failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        print("Login OK")

        # Test /me endpoint (reads users table)
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = await client.get(f"{BASE}/api/auth/me", headers=headers)
        print(f"/me: {resp.status_code} {resp.text}")
        assert resp.status_code == 200, f"/me failed: {resp.text}"
        print("/me OK")

        return access_token, refresh_token

async def test_upload_document(token):
    """Upload a document and poll to completed."""
    print("\n=== TEST: Upload Document ===")
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        headers = {"Authorization": f"Bearer {token}"}
        # Create a simple text file
        content = b"# Test Document\n\nThis is a test document for RAG.\n\nIt contains some information about the system.\n\nThe system uses vector embeddings for retrieval.\n\nRLS is now enabled on all tables."
        files = {"file": ("test.md", content, "text/markdown")}
        resp = await client.post(f"{BASE}/api/documents/upload", headers=headers, files=files)
        print(f"Upload: {resp.status_code} {resp.text}")
        assert resp.status_code in (200, 201), f"Upload failed: {resp.text}"
        data = resp.json()
        doc_id = data["id"]
        print(f"Uploaded document {doc_id}")

        # Poll for completion
        for i in range(30):
            await asyncio.sleep(2)
            resp = await client.get(f"{BASE}/api/documents/{doc_id}", headers=headers)
            if resp.status_code == 200:
                doc = resp.json()
                status = doc.get("status")
                print(f"  Poll {i+1}: status={status}")
                if status == "completed":
                    print("Document processing completed")
                    return doc_id
                elif status == "failed":
                    raise Exception(f"Document processing failed: {doc.get('error_message')}")
            else:
                print(f"  Poll {i+1}: {resp.status_code} {resp.text}")
        raise Exception("Document processing timeout")

async def test_chat_query(token, doc_id):
    """Send a chat query, confirm real answer + citation."""
    print("\n=== TEST: Chat Query ===")
    async with httpx.AsyncClient(timeout=60.0) as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # Send query (auto-creates conversation)
        resp = await client.post(
            f"{BASE}/api/chat",
            headers=headers,
            json={"question": "What does the test document say about RLS?"}
        )
        print(f"Chat: {resp.status_code} {resp.text}")
        assert resp.status_code == 200, f"Chat failed: {resp.text}"
        data = resp.json()
        assert "answer" in data
        assert "citations" in data
        print(f"Answer: {data['answer'][:200]}...")
        print(f"Citations: {len(data['citations'])}")
        assert len(data["citations"]) > 0, "Expected at least one citation"
        print("Chat OK with citations")

async def test_forged_jwt():
    """Test forged/invalid JWT returns 401."""
    print("\n=== TEST: Forged/Invalid JWT (should return 401) ===")
    # Use a completely invalid token
    forged_token = "invalid.token.signature"
    
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        headers = {"Authorization": f"Bearer {forged_token}"}
        resp = await client.get(f"{BASE}/api/auth/me", headers=headers)
        print(f"Invalid JWT /me: {resp.status_code} {resp.text}")
        assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.text}"
        print("Invalid JWT correctly rejected (401)")

async def main():
    try:
        token, refresh = await test_signup_login()
        doc_id = await test_upload_document(token)
        await test_chat_query(token, doc_id)
        await test_forged_jwt()
        print("\n=== ALL REGRESSION TESTS PASSED ===")
    except Exception as e:
        print(f"\n=== REGRESSION TEST FAILED: {e} ===")
        sys.exit(1)

asyncio.run(main())