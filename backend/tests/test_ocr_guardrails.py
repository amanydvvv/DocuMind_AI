"""
KueryCore AI — OCR Guardrail Tests
Covers the two defensive layers added for Part 6:
  1. Pre-flight image-quality gate (blank / structureless-noise pages never
     reach the Groq vision API call).
  2. [UNREADABLE] sentinel token: an exact whole-response match is treated as
     OCR failure; loose substring matches are NOT (no false positives).
"""

import numpy as np
import pymupdf
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services import ingestion
from app.services.ingestion import (
    _gate_decision,
    _ocr_pdf_page,
    _page_metrics_from_samples,
)


class _FakeClient:
    """Minimal stand-in for ingestion.groq_client with a mockable completions call."""

    def __init__(self, content: str):
        self.chat = MagicMock()
        self.chat.completions.create = AsyncMock(
            return_value=MagicMock(
                choices=[MagicMock(message=MagicMock(content=content))]
            )
        )


@pytest.fixture
def blank_page():
    """A page with no content at all — renders to a pure white pixmap."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    yield page
    doc.close()


@pytest.fixture
def noise_page():
    """A page filled with uniform random RGB noise (like the sweep's noise.pdf)."""
    rng = np.random.default_rng(42)
    w, h = 160, 120
    pix = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, w, h), False)
    for y in range(h):
        for x in range(w):
            r, g, b = rng.integers(0, 256, size=3)
            pix.set_pixel(x, y, (int(r), int(g), int(b)))
    doc = pymupdf.open()
    page = doc.new_page(width=w, height=h)
    page.insert_image(page.rect, pixmap=pix)
    yield page
    doc.close()


@pytest.fixture
def text_page():
    """A real text page — must pass the gate so the mock OCR call is reached."""
    doc = pymupdf.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 72),
        "The quick brown fox jumps over the lazy dog. " * 5,
        fontname="helv",
        fontsize=12,
    )
    yield page
    doc.close()


# --- Layer 1: pre-flight gate ----------------------------------------------

@pytest.mark.asyncio
async def test_blank_page_never_reaches_groq_api(blank_page, monkeypatch):
    client = _FakeClient("should never be returned")
    monkeypatch.setattr(ingestion, "groq_client", client)
    assert await _ocr_pdf_page(blank_page) == ""
    client.chat.completions.create.assert_not_called()


@pytest.mark.asyncio
async def test_noise_page_never_reaches_groq_api(noise_page, monkeypatch):
    client = _FakeClient("should never be returned")
    monkeypatch.setattr(ingestion, "groq_client", client)
    assert await _ocr_pdf_page(noise_page) == ""
    client.chat.completions.create.assert_not_called()


def test_gate_decision_uses_calibrated_regression_values():
    # blank.pdf regression values from the Part 6 sweep
    assert _gate_decision(0.0, 0.0, 0.0) == (True, False)
    # noise.pdf regression values
    assert _gate_decision(61.2, 8.25, 0.1233) == (False, True)
    # live_scan.pdf regression values (must NOT be rejected)
    assert _gate_decision(31.0, 1.66, 0.0158) == (False, False)


def test_page_metrics_blank_noise_and_content_arrays():
    blank = np.zeros((100, 100), dtype=np.uint8)
    noise = np.random.default_rng(0).integers(0, 256, size=(100, 100), dtype=np.uint8)
    content = np.zeros((100, 100), dtype=np.uint8)
    content[20:80, 10] = 255  # one sparse strong vertical edge: text-like

    blank_std, blank_gm, blank_ef = _page_metrics_from_samples(blank)
    assert _gate_decision(blank_std, blank_gm, blank_ef) == (True, False)

    noise_std, noise_gm, noise_ef = _page_metrics_from_samples(noise)
    assert _gate_decision(noise_std, noise_gm, noise_ef) == (False, True)

    cont_std, cont_gm, cont_ef = _page_metrics_from_samples(content)
    assert _gate_decision(cont_std, cont_gm, cont_ef) == (False, False)


# --- Layer 2: [UNREADABLE] sentinel token ----------------------------------

@pytest.mark.asyncio
async def test_unreadable_token_treated_as_failure(text_page, monkeypatch):
    client = _FakeClient("[UNREADABLE]")
    monkeypatch.setattr(ingestion, "groq_client", client)
    assert await _ocr_pdf_page(text_page) == ""
    client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_normal_ocr_response_unaffected(text_page, monkeypatch):
    client = _FakeClient("Hello world line one\nline two")
    monkeypatch.setattr(ingestion, "groq_client", client)
    assert await _ocr_pdf_page(text_page) == "Hello world line one\nline two"
    client.chat.completions.create.assert_called_once()


@pytest.mark.asyncio
async def test_sentinel_is_exact_match_not_substring(text_page, monkeypatch):
    client = _FakeClient("Some text [UNREADABLE] appears inline and is real content")
    monkeypatch.setattr(ingestion, "groq_client", client)
    assert await _ocr_pdf_page(text_page) == (
        "Some text [UNREADABLE] appears inline and is real content"
    )
