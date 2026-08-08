# Implementation Plan v3 — Retrieval Eval Harness + I/O Guardrails

Status: APPROVED (2026-08-08) — planning artifact; gating decisions recorded in Appendix A.
Scope: two features only. Everything else from the enterprise-RAG review is explicitly out of scope (dynamic tool compression, human-in-the-loop approval, LLM-gateway semantic caching) as noted in the originating task.

---

## Sequencing

Eval harness first (baseline), guardrails second (regression check against baseline). Guardrail changes get measured, not asserted-from-hindsight.

---

## Part 1 — Retrieval Evaluation Harness (LLM-as-judge)

### 1.1 Scope

- Golden dataset (32 Q/A pairs, incl. 3 negative controls) + runnable harness scoring each RAG run on **retrieval relevance**, **groundedness**, **completeness** — binary pass/fail per dimension, plus a deterministic marker-recall@k check as a non-flaky arbiter.
- Two run modes:
  - **Full mode (default, baseline/final):** retrieval + answer generation + judge — 2 real LLM calls per question.
  - **`--retrieval-only`:** retrieval + judge on retrieval relevance only — for fast dev iteration.
- Out of scope: ELO/continuous scores, per-turn memory, RAGAS or any eval framework dependency (judge reuses the existing `get_llm()` cascade).

### 1.2 Golden dataset

Location: `backend/tests/eval/` — `eval_corpus.md` (authored corpus, one file ~2.5k words, realistic content with identifiable facts) + `golden_set.json`.

Entry schema:

```json
{
  "id": "EVAL-001",
  "question": "How many days of PTO accrue per year?",
  "expected_chunk_markers": ["25 days", "annual … "],
  "answer_facts": ["annual PTO accrual cap is 25 days"],
  "docs": ["eval_corpus.md"],
  "intent": "lexical-exact",                 // lexical-exact | semantic-paraphrase | cross-section | multi-fact
  "expect_verdict": "pass",
  "notes": "tests FTS strength on a numeric fact"
}
```

- Chunk UUIDs are unstable across re-ingests → references are **phrase markers + doc filename**, never chunk IDs.
- **Negative controls (3):** `expect_verdict: "fail"` entries with deliberately wrong `answer_facts` / markers from an unrelated region of the corpus. The harness report must present negative controls in a separate block; **any control that is judged fully passing is a harness-broken bug**, reported as such (exit code 2), not a silent regression.
- **Maintenance rule:** markers change only when the corpus intentionally changes; marker failure on an unchanged corpus = retrieval regression. Re-run at upload/delete milestones; expand with new intents (negation, cross-doc, out-of-scope refusal) in later iterations.

### 1.3 Judge pipeline + call budget

```
golden_set.json
  1. --seed ingests eval_corpus.md (reuses document upload path)
  2. per question: hybrid retrieval via stage-1 internals + RRF + re-rank
     (cache-bypassed by direct composition — no query_cache involvement)
  3. deterministic: marker recall@k
  4. full mode: generate_answer(query, chunks) [stream-free variant, temp 0.3]
  5. judge call (temp 0, EVAL_JUDGE_MODEL, strict JSON):
       input: {question, generated_answer, reference_facts, retrieved_chunks}
       output: {"retrieval_pass": bool, "groundedness_pass": bool, "completeness_pass": bool}
     malformed JSON → retry once, then fail the dimension (fail-closed) + mark judge_error
  6. aggregate → results/<config>.json + markdown table
  7. --diff a b → per-dimension pass-rate delta + regression count
```

- **Call budget (explicit):** full 32-entry run = 32 generation + 32 judge = **64 calls**, worst case +32 (one retry per entry on malformed judge JSON) = **≤96 calls**. `--sample N` = ≤ 2N+2N calls (dev iter). Against Groq free tier (order of magnitude: `llama-3.1-8b-instant` ~30 RPM / 14,400 RPD; `qwen3-32b` ~30-60 RPM / 1,000 RPD; org-level limits — verify on dashboard), a full run fits comfortably within one free-tier day. Full-32 runs are for baseline/final results only; `--sample 5-10` for iteration.

### 1.4 Judge model — verification

`qwen3-32b` (Groq model ID `qwen3-32b`) confirmed **real and free-tier available** via Groq's supported-models catalog (console.groq.com/docs/models), 131K context, in a different family (Qwen3) than the Llama-family generator. It is already a member of the existing fallback cascade (generation.py:78-81). Config default: `EVAL_JUDGE_MODEL=qwen3-32b`.
Caveat: third-party trackers occasionally list it "Preview/Legacy." If Groq announces deprecation, migrate `EVAL_JUDGE_MODEL` to `openai/gpt-oss-20b` (production status, different family, same Groq key — one-line config change).

### 1.5 CI integration

- Default `pytest`: plumbing only (schema validator, judge-prompt formatter, verdict parser incl. retry/malformed handling, marker-recall math, runner E2E against stubbed retrievers + stub judge on a 3-entry mini-golden) — zero LLM calls, zero DB (monkeypatch precedent: `test_query_cache._install_pipeline`).
- Full runs: `pytest -m eval_llm` (opt-in marker, requires keys + seeded DB) or `backend/scripts/run_eval.py`. **No GitHub Actions added** (repo has none today; decision recorded in Appendix A).

### 1.6 Knob matrix

In-process patchables (retrieval-time): `retrieval.RRF_K`, `VECTOR_TOP_N`, `LEXICAL_TOP_N`, `RRF_FUSED_TOP_K`, `FINAL_TOP_K` (retrieval.py:26-30) + re-rank blend weights (0.50/0.30/0.22) and phrase bonus. Chunk knobs (`CHUNK_SIZE/OVERLAP`) are **ingestion-time** — out of v1 (requires a re-seed path; backlog).

### 1.7 Files

- `backend/app/services/evaluation.py` (NEW; schema, metrics, judge, aggregate; no import side effects on chat)
- `backend/scripts/run_eval.py` (NEW; CLI: `--seed`, `--validate-golden`, `--run`, `--sample N`, `--mode full|retrieval-only`, `--diff a b`)
- `backend/tests/eval/golden_set.json` + `backend/tests/eval/eval_corpus.md` (NEW)
- `backend/tests/test_eval_harness.py` (NEW; default-suite)
- `backend/app/config.py` (+ `EVAL_JUDGE_MODEL`)
- `backend/app/services/generation.py` (1-line: `get_llm(temperature=0.3)` parameter)

### 1.8 Phased steps (build order)

| # | Step | Effort |
|---|---|---|
| 1 | Author eval corpus + 32 golden pairs (incl. 3 negative controls) | L |
| 2 | `evaluation.py`: schema/validator | S |
| 3 | Runner: retrieval composition, cache-bypass, knob overrides | M |
| 4 | Marker recall@k | S |
| 5 | Generation pass + judge (prompt, strict parse+retry, aggregation) | M |
| 6 | CLI + results archive + `--diff` | M |
| 7 | Plumbing tests (no LLM/DB) + baseline archival | M |

### 1.9 Groundedness coverage — known open gap

The harness has verified the judge correctly scores `retrieval_pass=False` when a fact is absent from the corpus (EVAL-028/029, grounded-decline), but has not yet observed or tested a case where the model hallucinates a specific fabricated value and whether the judge catches it as ungrounded — a known open gap, not a hidden one.

---

## Part 2 — Input/Output Guardrails

### 2.1 Scope and limitation (exact language)

Input side: PII detection/redaction on incoming queries (email addresses, phone numbers, SSN/credit-card patterns, UUIDs) **before** they reach retrieval or the LLM; prompt-injection pattern blocking. **Scope-accurate limitation:** the injection defense **blocks known literal-phrase patterns** (e.g. "ignore previous instructions" style attempts); it does **not** prevent prompt injection in general — obfuscated, adversarial, or novel injection techniques are out of scope for this feature. The same phrasing is mirrored in the checklist stub so the limitation cannot get lost in later doc transfers (incl. STUDY_GUIDE).

Output side: post-generation checks — system-prompt leakage (literal fragments of `RAG_PROMPT_TEMPLATE`) and an unsafe-content blocklist, plus a stream-safe handling path. Explicitly **guardrail is a safety net, not a moderation suite.**

Dependencies: **stdlib `re` only.** Presidio/spaCy deliberately rejected (over-engineering for this scope); documented as future work if the corpus scales.

### 2.2 Architecture / insertion points (chat.py)

Non-stream (`chat`) + stream (`chat_stream`) share the same hooks:

```
persist user message (sanitized text — see Appendix A.2)
  → input_guardrail(question)
      ├─ sanitize_query(): PII regex family → tokens like [REDACTED:email]
      └─ is_injection(): exact-phrase blocklist → if matched:
             refuse short-circuit: no retrieval, no LLM
             assistant answer = canned refusal
             citations=[], avg_similarity=0
             still persist assistant Message + QueryLog (shape preserved)
  → retrieval + generation use sanitized query exclusively
  → output guardrail(answer) post-generation:
       pass → ship
       fail + non-stream → replace answer, log flag
       fail + stream → append disclaimer delta before `done`
           (never mutates already-emitted tokens)
```

Contract invariants: citations shape / SSE event sequence (metadata → tokens → done) untouched; `GUARDRAILS_STRICT` (default false) toggles obfuscation-pattern checks (URL/base64) for false-positive control. Streaming integrity: input guardrail runs synchronously pre-stream; the only stream-time step is the post-hoc append, which is honest and non-destructive.

### 2.3 Config

`GUARDRAILS_ENABLED: bool = true` (kill switch), `GUARDRAILS_STRICT: bool = false`. No schema migration, no new DB columns.

### 2.4 Files

- `backend/app/services/guardrails.py` (NEW; `sanitize_query()`, `is_injection()`, `validate_output()` — pure, no I/O)
- `backend/app/routers/chat.py` (both routes, ~25 lines total)
- `backend/app/config.py` (+2 boolean settings)
- `backend/tests/test_guardrails.py` (NEW; table-driven + E2E with mocked `generate_answer`)
- `docs/FRONTEND_API_CONTRACT.md` — intentionally untouched (contract unchanged)

### 2.5 Phased steps

| # | Step | Effort |
|---|---|---|
| 1 | `guardrails.py` rules: PII regex set, injection literal patterns, output checks | M |
| 2 | Wire non-streamed route: sanitize-at-persist + refusal path | S |
| 3 | Wire stream route (same + post-stream append) | M |
| 4 | Tests: table-driven + E2E with mocked generation | M |
| 5 | Eval no-regression gate: on-demand harness run vs baseline (sanitization only; judge-failure buffer) | S |
| 6 | Checklist + STUDY_GUIDE hook | S |

---

## Phase 2 closed — regression-gate verification (Step 2.6)

Gate run: `scripts/run_eval.py --seed && --run` (full 32 entries, post-guardrail
code) then `--diff baseline.json eval_20260808_235555.json` (2026-08-08).

**Verdict: pass — zero regressions, entry-level identical to baseline.**

| dimension | baseline | post-guardrail | delta |
|---|---|---|---|
| marker_recall | 81.2% | 81.2% | 0.0% |
| retrieval_pass | 78.1% | 78.1% | 0.0% |
| groundedness_pass | 96.9% | 96.9% | 0.0% |
| completeness_pass | 90.6% | 90.6% | 0.0% |

- Shared entries 32/32; **zero per-entry flag changes** across all four
  dimensions (including the three known misses EVAL-014/016/024 — same rows
  in both runs).
- Negative controls NEG-001/002/003: fabricated info not retrievable in both
  runs (marker_recall/retrieval_pass False) — **zero violations**; groundedness
  True on controls is the honest-refusal path, not a validity hit
  (evaluation.py violations semantics).
- Groundedness-stress EVAL-028/029: identical decline pattern (marker True →
  retrieval False → groundedness True), same in both runs.
- No judge errors, same models (generation + judge) and retrieval constants
  in both headers.

**Why a guardrail false positive cannot explain any future delta:** the harness
invokes `app.services.retrieval` / `generation` / `evaluation` **directly** —
guardrails exist only in `app/routers/chat.py` (verified by import search), so
`sanitize_pii` / `is_injection` / `validate_output` never touch golden
questions or their answers. Any future per-entry difference on this gate is
retrieval re-ranking or judge LLM noise, not guardrail interference.

Part 2 is complete and closed: Steps 1-4 (rules, routing wiring, tests — 63
cases in `backend/tests/test_guardrails.py`, full suite 153 passed) plus this
regression gate (Step 5). Step 6 (checklist + STUDY_GUIDE hook) covered by
`docs/PROJECT_CHECKLIST.md` (Part 2 fully marked done).

---

## Risks

- Judge flakiness → temperature-0, strict parsing, retry-once, recall co-arbiter.
- Judge-model bias (same-family scoring) → EVAL_JUDGE_MODEL in different family; migration path documented.
- Corpus authoring is the true cost driver → 30 entries floor, `--sample` for iteration.
- Golden-drift maintenance burden → marker-change rule + milestone re-runs.
- Sanitization is one-way → raw text intentionally not stored (decided; see Appendix A).

## Appendix A — Decisions recorded

- A.1 Eval scope: **full mode default** (retrieval+generation+judge); `--retrieval-only` for dev. (From orig. pending Q1.)
- A.2 PII storage: **sanitize-once — redacted text is the single source of truth** for Message, history, cache keys, and LLM input. Raw queries are never stored. If raw-text audit logging is ever needed later, it will be a separate isolated table with no read path back into generation/history — explicitly not this feature.
- A.3 CI: **no GitHub Actions added currently** — repo has no CI today; default suite is plumbing-only, full runs opt-in via marker/script.
- A.4 Golden count: **30** (user-specified "full-30").
- A.5 Judge model: `qwen3-32b` verfitted viable (see §1.4).
- A.6 Chunk-size knobs deferred (ingestion-time, needs re-index path) — backlog.

---

build order for phase 1-2: eval harness (Steps 1-7) then guardrails (Steps 1-6), then regression gate.