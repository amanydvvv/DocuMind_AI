"""
DocuMind AI — Eval CLI Tests (Step 6)

Arg-parsing/routing, --sample entry math (controls always included),
knob-override mapping, and --diff on fixture result files (including the
mismatched-subsets case). The pipeline call itself is stubbed - no real
LLM/DB calls in this suite.
"""

import json
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import run_eval as cli
from app.services.evaluation import EvalReport, GoldenEntry, QuestionResult


def _entry(eid, verdict="pass"):
    return GoldenEntry(
        id=eid,
        question=f"Q {eid}",
        expected_chunk_markers=["m"] if verdict != "fail" else [],
        answer_facts=["f"] if verdict != "fail" else [],
        docs=["eval_corpus.md"],
        expect_verdict=verdict,
    )


def _sample_fixture():
    """27 pass + 3 controls, like the real golden set."""
    return [_entry(f"EVAL-{i:03d}", "pass") for i in range(1, 28)] + [
        _entry("NEG-001", "fail"),
        _entry("NEG-002", "fail"),
        _entry("NEG-003", "fail"),
    ]


# ---------------------------------------------------------------------------
# Arg parsing / routing
# ---------------------------------------------------------------------------


def test_parser_requires_exactly_one_action():
    with pytest.raises(SystemExit):
        cli.main(["--validate-golden", "--seed"])


def test_validate_golden_routes():
    args = cli.build_parser().parse_args(["--validate-golden"])
    assert args.validate_golden is True
    assert args.run is False


def test_sample_requires_run():
    with pytest.raises(SystemExit):
        cli.main(["--sample", "5"])


def test_sample_parses():
    args = cli.build_parser().parse_args(["--run", "--sample", "7"])
    assert args.sample == 7


def test_invalid_knob_values_rejected():
    with pytest.raises(SystemExit):
        cli.main(["--run", "--rrf-k", "0"])
    with pytest.raises(SystemExit):
        cli.main(["--run", "--weight-vector", "1.5"])


def test_diff_requires_two_files():
    with pytest.raises(SystemExit):
        cli.main(["--diff", "only-one.json"])


def test_validate_golden_reports_ok():
    rc = cli.main(["--validate-golden"])
    assert rc == 0


# ---------------------------------------------------------------------------
# Sample entry math (negative controls always included)
# ---------------------------------------------------------------------------


def test_sample_zero_keeps_only_controls():
    entries = _sample_fixture()
    selected, stats = cli.select_entries(entries, 0)
    assert [e.id for e in selected] == ["NEG-001", "NEG-002", "NEG-003"]
    assert stats == {
        "pass_total": 27,
        "control_total": 3,
        "sample_size": 0,
        "selected_pass": 0,
        "selected_controls": 3,
    }


def test_sample_5_is_5_pass_plus_all_controls():
    entries = _sample_fixture()
    selected, stats = cli.select_entries(entries, 5)
    assert len(selected) == 5 + 3
    assert selected[0].id == "EVAL-001"
    assert selected[-1].id == "NEG-003"
    assert stats["selected_pass"] == 5
    assert stats["selected_controls"] == 3


def test_sample_larger_than_pass_total_clamps():
    entries = _sample_fixture()
    selected, stats = cli.select_entries(entries, 100)
    assert len(selected) == 30
    assert stats["selected_pass"] == 27


def test_sample_2_with_2_controls():
    entries = [_entry("E1", "pass"), _entry("E2", "pass"),
               _entry("N1", "fail"), _entry("N2", "fail")]
    selected, _ = cli.select_entries(entries, 1)
    assert [e.id for e in selected] == ["E1", "N1", "N2"]


# ---------------------------------------------------------------------------
# Knob overrides
# ---------------------------------------------------------------------------


def test_collect_knob_overrides_partial():
    args = cli.build_parser().parse_args(
        ["--run", "--rrf-k", "80", "--final-top-k", "3", "--weight-phrase", "0.1"]
    )
    overrides = cli.collect_knob_overrides(args)
    assert overrides == {"RRF_K": 80, "FINAL_TOP_K": 3, "WEIGHT_PHRASE_NORM": 0.1}


def test_collect_knob_overrides_empty():
    args = cli.build_parser().parse_args(["--run"])
    assert cli.collect_knob_overrides(args) == {}


def test_forecast_calls_reports_base_and_worst_case():
    text = cli.forecast_calls(10)
    assert "base 20" in text
    assert "worst case 30" in text


# ---------------------------------------------------------------------------
# Diff
# ---------------------------------------------------------------------------


def _q(id_, rp=True, gp=True, cp=True, mr=True):
    return {
        "id": id_,
        "retrieval_pass": rp,
        "groundedness_pass": gp,
        "completeness_pass": cp,
        "marker_recall": mr,
    }


def _write_payload(path, entries):
    payload = {
        "header": {
            "created_at": "2026-08-08T00:00:00+00:00",
            "mode": "full",
            "total_entries": len(entries),
        },
        "summary": {"llm_calls": 0, "negative_control_violations": []},
        "questions": [
            {
                "entry_id": e["id"],
                "retrieval_pass": e["retrieval_pass"],
                "groundedness_pass": e["groundedness_pass"],
                "completeness_pass": e["completeness_pass"],
                "marker_recall": e["marker_recall"],
            }
            for e in entries
        ],
    }
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_diff_reports_deltas_regressions_and_missing_entries(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_payload(
        a,
        [
            _q("E1"),
            _q("E2", gp=False, cp=False),
            _q("only-in-a"),
        ],
    )
    _write_payload(
        b,
        [
            _q("E1", cp=False),              # completeness regression on E1
            _q("E2", gp=False, cp=False),
            _q("only-in-b"),
        ],
    )

    diff = cli.diff_results(json.loads(a.read_text()), json.loads(b.read_text()))
    assert diff["shared"] == ["E1", "E2"]
    assert diff["only_in_a"] == ["only-in-a"]
    assert diff["only_in_b"] == ["only-in-b"]

    completeness = diff["dimensions"]["completeness_pass"]
    assert completeness["regressions"] == ["E1"]
    assert completeness["rate_a"] == pytest.approx(0.5)
    assert completeness["rate_b"] == pytest.approx(0.0)
    assert completeness["delta"] == pytest.approx(-0.5)

    assert diff["dimensions"]["retrieval_pass"]["regressions"] == []
    assert diff["overall"]["regressions"] == ["E1"]  # all-passed in A, missed in B


def test_diff_different_entry_counts_graceful(tmp_path):
    a = tmp_path / "a.json"
    b = tmp_path / "b.json"
    _write_payload(a, [_q("shared"), _q("a-only")])
    _write_payload(b, [_q("shared")])

    diff = cli.diff_results(json.loads(a.read_text()), json.loads(b.read_text()))
    assert diff["only_in_b"] == []
    assert diff["only_in_a"] == ["a-only"]
    assert diff["dimensions"]["retrieval_pass"]["rate_a"] == 1.0
    assert diff["dimensions"]["retrieval_pass"]["regressions"] == []


# ---------------------------------------------------------------------------
# Run path with stubbed pipeline (no LLM / DB)
# ---------------------------------------------------------------------------


class FakeSession:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


def _fake_report():
    q = QuestionResult(
        entry_id="EVAL-001",
        expect_verdict="pass",
        is_negative_control=False,
        marker_recall=True,
        retrieval_pass=True,
        groundedness_pass=True,
        completeness_pass=True,
        judge_error=False,
        generated_answer="stub",
        knobs_applied={},
    )
    neg = QuestionResult(
        entry_id="NEG-001",
        expect_verdict="fail",
        is_negative_control=True,
        marker_recall=False,
        retrieval_pass=False,
        groundedness_pass=False,
        completeness_pass=False,
        judge_error=False,
        generated_answer="stub",
        knobs_applied={},
    )
    return EvalReport(questions=[q, neg], llm_calls=4)


def test_run_action_writes_report_with_mocked_pipeline(
    monkeypatch, tmp_path, capsys
):
    async def fake_run_evaluation(entries, session, **kwargs):
        assert kwargs["user_id"] is not None
        assert kwargs["overrides"] == {"FINAL_TOP_K": 4}
        return _fake_report()

    async def fake_ensure_user(db):
        return SimpleNamespace(id=uuid.UUID(int=1))

    monkeypatch.setattr(cli, "async_session", lambda: FakeSession())
    monkeypatch.setattr(cli, "run_evaluation", fake_run_evaluation)
    monkeypatch.setattr(cli, "_ensure_eval_user", fake_ensure_user)

    out = tmp_path / "report.json"
    rc = cli.main(["--run", "--sample", "1", "--final-top-k", "4", "--output", str(out)])

    assert rc == 0
    assert out.is_file()
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["summary"]["llm_calls"] == 4
    assert payload["header"]["knobs_overridden"] == {"FINAL_TOP_K": 4}
    printed = capsys.readouterr().out
    assert "budget: base 8" in printed  # 2 calls x (1 pass + 3 controls)
    assert "NEG-001" in printed  # negative controls rendered in the summary


def test_run_action_exit_2_on_negative_control_violation(monkeypatch, tmp_path):
    def violating_report():
        q = QuestionResult(
            entry_id="NEG-001",
            expect_verdict="fail",
            is_negative_control=True,
            marker_recall=False,
            retrieval_pass=True,
            groundedness_pass=False,
            completeness_pass=False,
            judge_error=False,
            generated_answer="stub",
            knobs_applied={},
        )
        return EvalReport(questions=[q], llm_calls=1)

    async def fake_run_evaluation(entries, session, **kwargs):
        return violating_report()

    async def fake_ensure_user(db):
        return SimpleNamespace(id=uuid.UUID(int=1))

    monkeypatch.setattr(cli, "async_session", lambda: FakeSession())
    monkeypatch.setattr(cli, "run_evaluation", fake_run_evaluation)
    monkeypatch.setattr(cli, "_ensure_eval_user", fake_ensure_user)

    out = tmp_path / "bad.json"
    rc = cli.main(["--run", "--output", str(out)])
    assert rc == 2  # harness-validity bug: a control scored pass