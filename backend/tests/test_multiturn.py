import asyncio
import httpx
import json

async def run_multiturn_test():
    async with httpx.AsyncClient(timeout=30.0) as client:
        print("=== TURN 1: Initial Question ===")
        q1 = "Who is the lead engineer for Project Xyzzy?"
        r1 = await client.post("http://127.0.0.1:8000/api/chat", json={"question": q1})
        print(f"Status: {r1.status_code}")
        d1 = r1.json()
        print(json.dumps(d1, indent=2))
        
        conv_id = d1.get("conversation_id")
        print(f"\nExtracted conversation_id: {conv_id}")
        
        print("\n=== TURN 2: Follow-up Question (using conversation_id) ===")
        q2 = "What year was her project started?"
        r2 = await client.post("http://127.0.0.1:8000/api/chat", json={"question": q2, "conversation_id": conv_id})
        print(f"Status: {r2.status_code}")
        d2 = r2.json()
        print(json.dumps(d2, indent=2))

if __name__ == "__main__":
    asyncio.run(run_multiturn_test())
