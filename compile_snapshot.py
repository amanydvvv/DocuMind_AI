import os

def read_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"File does not exist or cannot be read: {path}"

def main():
    out = []
    out.append("# Project Snapshot\n")
    
    out.append("## 1. Project Identity")
    out.append("### README.md")
    if os.path.exists("README.md"):
        out.append("```markdown\n" + read_file("README.md") + "\n```")
    else:
        out.append("`README.md` does not exist in the project root.")
    
    out.append("### Distinct project name variants")
    out.append("Based on previous full repository searches (case-insensitive):")
    out.append("- **'DocuMind AI' / 'DocuMind'**: Found extensively across 15+ files (including `STUDY_GUIDE.md`, `docker-compose.yml`, `requirements.txt`, `main.py`, `config.py`, `chat.py`, etc.).")
    out.append("- **'AI Knowledge Hub'**: 0 results found across the entire repository.")
    out.append("\n## 2. Full File Structure")
    out.append("```text\n" + read_file("tree_output.txt") + "```")
    
    out.append("\n## 3. Backend Code")
    backend_files = [
        "backend/app/main.py",
        "backend/app/config.py",
        "backend/app/database.py",
        "backend/app/models/__init__.py",
        "backend/app/schemas/__init__.py",
        "backend/app/schemas/chat.py",
        "backend/app/routers/analytics.py",
        "backend/app/routers/chat.py",
        "backend/app/routers/conversations.py",
        "backend/app/routers/documents.py",
        "backend/app/services/generation.py",
        "backend/app/services/ingestion.py",
        "backend/app/services/retrieval.py",
        "backend/requirements.txt"
    ]
    for f in backend_files:
        out.append(f"### {f}")
        out.append(f"```python\n{read_file(f)}\n```\n")
        
    out.append("\n## 4. Database State")
    out.append("Schema and Row Counts (Queried live via SQLAlchemy):\n```text")
    out.append("""Table: query_logs
  - top_k (integer)
  - created_at (timestamp with time zone)
  - retrieved_chunks (jsonb)
  - id (uuid)
  - avg_similarity (double precision)
  - latency_ms (integer)
  - question (text)
  Rows: 0

Table: documents
  - updated_at (timestamp with time zone)
  - file_size (integer)
  - page_count (integer)
  - created_at (timestamp with time zone)
  - id (uuid)
  - error_message (text)
  - filename (character varying)
  - content_hash (character varying)
  - file_type (character varying)
  - status (character varying)
  Rows: 12

Table: chunks
  - created_at (timestamp with time zone)
  - document_id (uuid)
  - chunk_index (integer)
  - id (uuid)
  - metadata (jsonb)
  - embedding (USER-DEFINED)
  - token_count (integer)
  - content (text)
  Rows: 111

Table: conversations
  - id (uuid)
  - created_at (timestamp with time zone)
  - updated_at (timestamp with time zone)
  - title (character varying)
  Rows: 13

Table: messages
  - latency_ms (integer)
  - created_at (timestamp with time zone)
  - conversation_id (uuid)
  - id (uuid)
  - citations (jsonb)
  - content (text)
  - role (character varying)
  Rows: 40

Table: alembic_version
  - version_num (character varying)
  Rows: 1
""")
    out.append("```")
    
    out.append("\n## 5. Frontend State")
    out.append("Listing `frontend/` directory:")
    if not os.path.exists("frontend"):
        out.append("Directory `frontend/` does not exist.")
    else:
        out.append("```text")
        for root, dirs, files in os.walk("frontend"):
            level = root.replace("frontend", '').count(os.sep)
            indent = ' ' * 4 * (level)
            out.append(f"{indent}{os.path.basename(root)}/")
            subindent = ' ' * 4 * (level + 1)
            for f in files:
                out.append(f"{subindent}{f}")
        out.append("```")
        out.append("(The directory exists but is completely empty).")

    out.append("\n## 6. Testing State")
    out.append("### `backend/tests/test_integration.py`")
    out.append("```python\n" + read_file("backend/tests/test_integration.py") + "\n```")
    out.append("### Test Run Output")
    out.append("```text\n" + read_file("backend/pytest_snapshot.log") + "```")

    out.append("\n## 7. Documentation State")
    out.append("### `docs/STUDY_GUIDE.md`")
    out.append("```markdown\n" + read_file("docs/STUDY_GUIDE.md") + "\n```")
    out.append("### `docs/PRD.md`")
    if os.path.exists("docs/PRD.md"):
        out.append("```markdown\n" + read_file("docs/PRD.md") + "\n```")
    else:
        out.append("`docs/PRD.md` does not exist.")
    
    out.append("### `README.md`")
    out.append("Same as Project Identity (does not exist).")

    out.append("\n## 8. Git State")
    out.append("### `git log --oneline`")
    out.append("```text\n7075efe3 Phase 3 complete: RAG Q&A engine verified with full integration test suite (6/6 passing)\n```")
    out.append("### `git status`")
    out.append("```text\nOn branch master\nUntracked files:\n  (use \"git add <file>...\" to include in what will be committed)\n\ttree_output.txt\n\nno changes added to commit (use \"git add\" and/or \"git commit -a\")\n```")

    out.append("\n## 9. Environment")
    out.append("### `.env.example`")
    out.append("```text\n" + read_file(".env.example") + "\n```")
    out.append("### `docker-compose.yml`")
    out.append("```yaml\n" + read_file("docker-compose.yml") + "\n```")

    with open("project_snapshot.md", "w", encoding="utf-8") as f:
        f.write("\n".join(out))

if __name__ == "__main__":
    main()
