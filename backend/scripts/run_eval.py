#!/usr/bin/env python3
"""
DocuMind AI - Retrieval Eval CLI (Phase 1, plan v3, Step 6)

Actions:
  python scripts/run_eval.py --validate-golden
  python scripts/run_eval.py --seed
  python scripts/run_eval.py --run [--sample N] [knob flags]
  python scripts/run_eval.py --diff A.json B.json

--validate-golden: schema check only (no DB, no LLM calls).
--seed:            ingests the golden corpus through the real document upload
                   path (Document row + file on disk + Services.ingestion
                   pipeline) and is idempotent (re-seeding replaces the prior
                   seed for the eval user).
--run:             runs the generation + judge pipeline over the golden set
                   (or a sampled subset), writes results/eval_<ts>.json and
                   prints a markdown summary with the negative controls
                   called out explicitly.
--sample N:        first N pass-type entries + ALL negative controls
                   (controls validate the judge on every run, regardless of
                   N). Budget is printed up front.
--diff A B:        compares two saved report JSON files - per-dimension pass
                   rate deltas over shared entries + regression counts.
                   Entries only in one file are reported, not an error.

Exit codes: 0 success; 1 config/validation failure; 2 negative-control
violation (harness validity bug - loudly, never a silent regression).
"""

import argparse
import asyncio
import hashlib
import json
import secrets
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import delete, func, select

from app.config import get_settings
from app.core.security import hash_password
from app.database import async_session, engine, init_db
from app.models import Document, User
from app.services import retrieval
from app.services.evaluation import (
    EvaluationConfigError,
    GoldenEntry,
    QuestionResult,
    load_golden_set,
    run_evaluation,
)
from app.services.ingestion import ingest_document

settings = get_settings()

BACKEND_DIR = Path(__file__).resolve().parents[1]
GOLDEN_FILE_DEFAULT = BACKEND_DIR / "tests" / "eval" / "golden_set.json"
CORPUS_FILE_DEFAULT = BACKEND_DIR / "tests" / "eval" / "eval_corpus.md"
RESULTS_DIR = BACKEND_DIR / "results"
BASELINE_PATH = RESULTS_DIR / "baseline.json"
EVAL_USER_EMAIL = "eval@documind.local"

# (cli flag -> retrieval module constant)
KNOB_FLAG_TO_CONSTANT = {
    "rrf_k": "RRF_K",
    "vector_top_n": "VECTOR_TOP_N",
    "lexical_top_n": "LEXICAL_TOP_N",
    "rrf_fused_top_k": "RRF_FUSED_TOP_K",
    "final_top_k": "FINAL_TOP_K",
    "weight_vector": "WEIGHT_VECTOR_NORM",
    "weight_lexical": "WEIGHT_LEXICAL_NORM",
    "weight_phrase": "WEIGHT_PHRASE_NORM",
}


# ----------------------------------------------------------------------------
# Pure helpers
# ----------------------------------------------------------------------------


def select_entries(entries: List[GoldenEntry], n: int) -> tuple:
    """
    First n pass-type entries + ALL negative controls (controls always run).
    Returns (selected, stats).
    """
    pass_type = [e for e in entries if e.expect_verdict != "fail"]
    controls = [e for e in entries if e.expect_verdict == "fail"]
    sampled = pass_type[:n]
    selected = sampled + controls
    stats = {
        "pass_total": len(pass_type),
        "control_total": len(controls),
        "sample_size": n,
        "selected_pass": len(sampled),
        "selected_controls": len(controls),
    }
    return selected, stats


def collect_knob_overrides(args) -> Dict[str, Any]:
    """Map CLI knob flags to retrieval module constants; only provided ones."""
    overrides: Dict[str, Any] = {}
    for flag, constant in KNOB_FLAG_TO_CONSTANT.items():
        value = getattr(args, flag, None)
        if value is not None:
            overrides[constant] = value
    return overrides


def forecast_calls(selected_count: int, rewrite_count: int = 0) -> str:
    """Budget visibility: 2 per question (generation + judge) plus one
    follow-up rewrite per multi-turn entry, worst case +1 retry per entry
    for malformed judge JSON."""
    base = (2 * selected_count) + rewrite_count
    return (
        f"budget: base {base} LLM calls "
        f"({selected_count} generation + {selected_count} judge"
        + (f" + {rewrite_count} rewrite" if rewrite_count else "")
        + f"), worst case {base + selected_count} (one retry per entry)"
    )


def _question_dict(q) -> Dict[str, Any]:
    return {
        "entry_id": q.entry_id,
        "expect_verdict": q.expect_verdict,
        "is_negative_control": q.is_negative_control,
        "marker_recall": q.marker_recall,
        "retrieval_pass": q.retrieval_pass,
        "groundedness_pass": q.groundedness_pass,
        "completeness_pass": q.completeness_pass,
        "judge_error": q.judge_error,
        "topic_leak": q.topic_leak,
        "rewritten_query": q.rewritten_query,
        "generated_answer_truncated": q.generated_answer[:200],
    }


def build_report_payload(
    report, entries: List[GoldenEntry], *, mode: str, knobs_overridden: Dict[str, Any]
) -> dict:
    constants = {name: getattr(retrieval, name) for name in ALL_RETRIEVAL_CONSTANTS}
    return {
        "header": {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "mode": mode,
            "total_entries": len(entries),
            "generation_model": settings.GENERATIVE_MODEL,
            "judge_model": settings.EVAL_JUDGE_MODEL,
            "retrieval_constants": constants,
            "knobs_overridden": knobs_overridden,
        },
        "summary": report.summary(),
        "questions": [_question_dict(q) for q in report.questions],
    }


def _rate_from(entries: List[dict], dim: str) -> Optional[float]:
    if not entries:
        return None
    hits = sum(1 for e in entries if e[dim])
    return hits / len(entries)


def diff_results(a: dict, b: dict) -> dict:
    """Compare two saved result payloads. Shared-entry rates, per-dim
    deltas, regression lists, and gracefully reported missing entries."""
    def index(payload):
        return {q["entry_id"]: q for q in payload["questions"]}

    qa, qb = index(a), index(b)
    shared = [eid for eid in qa if eid in qb]
    only_a = [eid for eid in qa if eid not in qb]
    only_b = [eid for eid in qb if eid not in qa]

    dims = ("marker_recall", "retrieval_pass", "groundedness_pass", "completeness_pass")
    dim_results = {}
    for dim in dims:
        shared_entries = [qa[eid] for eid in shared]
        shared_entries_b = [qb[eid] for eid in shared]
        rate_a = _rate_from(shared_entries, dim)
        rate_b = _rate_from(shared_entries_b, dim)
        regressions = sorted(eid for eid in shared if qa[eid][dim] and not qb[eid][dim])
        dim_results[dim] = {
            "rate_a": rate_a,
            "rate_b": rate_b,
            "delta": None if rate_a is None or rate_b is None else rate_b - rate_a,
            "regressions": regressions,
        }

    overall = {
        "regressions": sorted(
            eid
            for eid in shared
            if all(qa[eid][d] for d in dims) and not all(qb[eid][d] for d in dims)
        )
    }
    return {
        "shared": shared,
        "only_in_a": only_a,
        "only_in_b": only_b,
        "dimensions": dim_results,
        "overall": overall,
    }


# ----------------------------------------------------------------------------
# Markdown renderers
# ----------------------------------------------------------------------------


def _pct(value):
    return "n/a" if value is None else f"{value * 100:.1f}%"


def render_summary_markdown(payload: dict) -> str:
    header = payload["header"]
    summary = payload["summary"]
    lines = [
        "# DocuMind Eval Run",
        "",
        f"- mode: {header['mode']} ({header['total_entries']} entries)",
        f"- generation model: {header['generation_model']}",
        f"- judge model: {header['judge_model']}",
        f"- llm_calls: {summary['llm_calls']}",
        f"- created at: {header['created_at']}",
        "",
        "## Pass rates (per pass-type entry, judged)",
        "",
        "| dimension | rate |",
        "|---|---|",
    ]
    for dim, rate in summary["pass_rates"].items():
        lines.append(f"| {dim} | {_pct(rate)} |")

    lines += ["", "## Marker recall (deterministic)",
              "", "| entry | marker_recall |", "|---|---|"]
    for q in payload["questions"]:
        lines.append(f"| {q['entry_id']} | {q['marker_recall']} |")

    leak_entries = [q for q in payload["questions"] if q["topic_leak"]]
    if leak_entries:
        lines += ["", "## Topic leaks (forbidden topics named in answers)", ""]
        for q in leak_entries:
            lines.append(f"> - {q['entry_id']}: {q['generated_answer_truncated']!r}")

    lines += ["", "## Negative controls (must all fail)", "", "| id | dims |", "|---|---|"]
    for cid, dims in summary["negative_controls"].items():
        lines.append(f"| {cid} | {dims} |")
    violations = summary["negative_control_violations"]
    if violations:
        lines.append("")
        lines.append("> **HARNESS-VALIDITY PROBLEM**: negative control(s) PASSED:")
        for cid in violations:
            lines.append(f"> - {cid}")
    if summary["judge_errors"]:
        lines.append("")
        lines.append(f"> judge_error entries: {summary['judge_errors']}")
    return "\n".join(lines)


def render_diff_markdown(diff: dict) -> str:
    lines = [
        "# Eval Diff",
        "",
        f"- shared entries: {len(diff['shared'])}",
    ]
    if diff["only_in_a"]:
        lines.append(f"- only in A: {diff['only_in_a']}")
    if diff["only_in_b"]:
        lines.append(f"- only in B: {diff['only_in_b']}")
    lines += ["", "| dimension | A | B | delta | regressions |", "|---|---|---|---|---|"]
    for dim, d in diff["dimensions"].items():
        lines.append(
            f"| {dim} | {_pct(d['rate_a'])} | {_pct(d['rate_b'])} | "
            f"{_pct(d['delta'])} | {len(d['regressions'])} {d['regressions']} |"
        )
    if diff["overall"]["regressions"]:
        lines.append("")
        lines.append(f"> regressions (all-passed in A, any-failed in B): "
                     f"{diff['overall']['regressions']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# DB / async actions
# ---------------------------------------------------------------------------


async def _ensure_eval_user(db) -> User:
    result = await db.execute(select(User).where(User.email == EVAL_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user is not None:
        return user
    user = User(
        email=EVAL_USER_EMAIL,
        hashed_password=hash_password(secrets.token_hex(16)),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def seed_corpus() -> dict:
    """Idempotently ingest the golden corpus for the eval user via the real
    upload artifacts + ingestion pipeline."""
    if not CORPUS_FILE_DEFAULT.is_file():
        raise EvaluationConfigError(f"corpus file missing: {CORPUS_FILE_DEFAULT}")
    content = CORPUS_FILE_DEFAULT.read_bytes()
    content_hash = hashlib.sha256(content).hexdigest()

    await init_db()
    async with async_session() as db:
        user = await _ensure_eval_user(db)

        existing = await db.execute(
            select(Document).where(
                Document.filename == "eval_corpus.md",
                Document.user_id == user.id,
            )
        )
        for doc in existing.scalars():
            path = Path(settings.UPLOAD_DIR) / f"{doc.id}.md"
            if path.exists():
                path.unlink()
            await db.execute(delete(Document).where(Document.id == doc.id))
        await db.commit()

        doc_id = uuid.uuid4()
        upload_dir = Path(settings.UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{doc_id}.md"
        file_path.write_bytes(content)

        doc = Document(
            id=doc_id,
            user_id=user.id,
            filename="eval_corpus.md",
            content_hash=content_hash,
            file_type="markdown",
            file_size=len(content),
            status="pending",
        )
        db.add(doc)
        await db.commit()

        await ingest_document(str(doc_id), str(file_path))

        refreshed = await db.get(Document, doc_id)
        if refreshed is None:
            raise EvaluationConfigError("seed document lost after ingestion")
        await db.refresh(refreshed)
        return {
            "document_id": str(refreshed.id),
            "status": refreshed.status,
            "error_message": refreshed.error_message,
            "user_id": str(user.id),
        }


async def run_cmd(args, golden_file: Path) -> dict:
    entries = load_golden_set(golden_file)
    selected, stats = select_entries(entries, args.sample if args.sample is not None else len(entries))
    if args.sample is not None:
        print(f"sample: first {stats['sample_size']} of {stats['pass_total']} pass entries "
              f"+ all {stats['control_total']} negative controls = {len(selected)} total")
    rewrite_count = sum(1 for e in selected if e.prior_turns)
    print(forecast_calls(len(selected), rewrite_count))

    overrides = collect_knob_overrides(args)
    if overrides:
        print("knob overrides:", overrides)

    mode = "sample" if args.sample is not None else "full"
    async with async_session() as db:
        user = await _ensure_eval_user(db)
        report = await run_evaluation(
            selected, db, user_id=user.id, overrides=overrides
        )

    payload = build_report_payload(report, selected, mode=mode, knobs_overridden=overrides)

    output_path = Path(args.output) if args.output else RESULTS_DIR / f"eval_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(render_summary_markdown(payload))
    print(f"\nreport written: {output_path}")

    return payload


def run_diff(a: str, b: str) -> int:
    pa = Path(a)
    pb = Path(b)
    for path in (pa, pb):
        if not path.is_file():
            print(f"missing result file: {path}", file=sys.stderr)
            return 1
    payload_a = json.loads(pa.read_text(encoding="utf-8"))
    payload_b = json.loads(pb.read_text(encoding="utf-8"))
    print(render_diff_markdown(diff_results(payload_a, payload_b)))
    return 0


# ----------------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------------

ALL_RETRIEVAL_CONSTANTS = (
    "VECTOR_TOP_N",
    "LEXICAL_TOP_N",
    "RRF_K",
    "RRF_FUSED_TOP_K",
    "FINAL_TOP_K",
    "WEIGHT_VECTOR_NORM",
    "WEIGHT_LEXICAL_NORM",
    "WEIGHT_PHRASE_NORM",
)


def build_parser():
    parser = argparse.ArgumentParser(prog="run_eval", description=__doc__)
    parser.add_argument("--validate-golden", action="store_true", help="schema check only (no DB/LLM)")
    parser.add_argument("--seed", action="store_true", help="ingest the golden corpus via the real ingest path")
    parser.add_argument("--run", action="store_true", help="run the generation+judge pipeline and save the report")
    parser.add_argument("--sample", type=int, metavar="N", help="with --run: first N pass entries + all controls")
    parser.add_argument("--diff", nargs=2, metavar=("A", "B"), help="compare two saved result JSON files")
    parser.add_argument("--golden-file", default=str(GOLDEN_FILE_DEFAULT), help="override golden set file")
    parser.add_argument("--output", default=None, help="override report output path")
    parser.add_argument("--rrf-k", type=int)
    parser.add_argument("--vector-top-n", type=int)
    parser.add_argument("--lexical-top-n", type=int)
    parser.add_argument("--rrf-fused-top-k", type=int)
    parser.add_argument("--final-top-k", type=int)
    parser.add_argument("--weight-vector", type=float)
    parser.add_argument("--weight-lexical", type=float)
    parser.add_argument("--weight-phrase", type=float)
    return parser


async def _run_async(coro):
    """Run an async command and dispose the engine so process exit is quiet
    (avoids asyncpg SSL-teardown noise on loop close)."""
    try:
        return await coro
    finally:
        await engine.dispose()


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    actions = sum(bool(v) for v in (args.validate_golden, args.seed, args.run, args.diff))
    if actions != 1:
        parser.error("exactly one action required: --validate-golden, --seed, --run, or --diff A B")
    if args.sample is not None and not args.run:
        parser.error("--sample requires --run")
    for name, value in (
        ("--rrf-k", getattr(args, "rrf_k", None)),
        ("--vector-top-n", getattr(args, "vector_top_n", None)),
        ("--lexical-top-n", getattr(args, "lexical_top_n", None)),
        ("--rrf-fused-top-k", getattr(args, "rrf_fused_top_k", None)),
        ("--final-top-k", getattr(args, "final_top_k", None)),
    ):
        if value is not None and value <= 0:
            parser.error(f"{name} must be > 0, got {value}")
    for name in ("weight_vector", "weight_lexical", "weight_phrase"):
        value = getattr(args, name, None)
        if value is not None and not (0.0 <= value <= 1.0):
            parser.error(f"--{name} must be in [0, 1], got {value}")

    if args.validate_golden:
        try:
            entries = load_golden_set(Path(args.golden_file))
        except EvaluationConfigError as exc:
            print(f"validate-golden: FAIL - {exc}", file=sys.stderr)
            return 1
        print(f"validate-golden: OK - {len(entries)} entries "
              f"({sum(1 for e in entries if e.expect_verdict != 'fail')} pass, "
              f"{sum(1 for e in entries if e.expect_verdict == 'fail')} controls)")
        return 0

    if args.diff:
        return run_diff(args.diff[0], args.diff[1])

    if args.seed:
        try:
            result = asyncio.run(_run_async(seed_corpus()))
        except Exception as exc:
            print(f"seed: FAIL - {exc}", file=sys.stderr)
            return 1
        print("seed: OK")
        for key, value in result.items():
            print(f"  {key}: {value}")
        return 0

    if args.run:
        try:
            payload = asyncio.run(_run_async(run_cmd(args, Path(args.golden_file))))
        except Exception as exc:
            print(f"run: FAIL - {exc}", file=sys.stderr)
            return 1
        violations = payload["summary"]["negative_control_violations"]
        if violations:
            print("\nEXIT 2: negative control(s) scored PASS - fabricated info "
                  "was retrievable; harness validity bug", file=sys.stderr)
            return 2
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())