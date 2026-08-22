#!/usr/bin/env python
"""
Rescue script: backfill raw_bytes for documents that still have PDF files on disk.

Run this ON THE CURRENTLY RUNNING INSTANCE (Render Shell) BEFORE deploying
the new upload/serve code. It reads any PDFs still present in the upload
directory and writes them into the `raw_bytes` column of the matching
`Document` rows.

Usage:
    python scripts/rescue_pdf_bytes.py

Requires DATABASE_URL in environment (same as the running app).
"""
import asyncio
import os
import sys
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add backend to path so we can import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models import Document
from app.config import get_settings


async def main():
    settings = get_settings()
    upload_dir = Path(settings.UPLOAD_DIR)

    if not upload_dir.exists():
        print(f"Upload directory does not exist: {upload_dir}")
        return

    # Find all PDF files in upload directory
    pdf_files = list(upload_dir.glob("*.pdf"))
    if not pdf_files:
        print("No PDF files found in upload directory.")
        return

    print(f"Found {len(pdf_files)} PDF file(s) in {upload_dir}")

    # Connect to database
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    updated = 0
    skipped = 0
    errors = 0

    async with async_session() as db:
        for pdf_path in pdf_files:
            # Extract document ID from filename (format: {uuid}.pdf)
            try:
                doc_id = UUID(pdf_path.stem)
            except ValueError:
                print(f"  SKIP: {pdf_path.name} - not a valid UUID filename")
                skipped += 1
                continue

            # Check if document exists and needs backfill
            result = await db.execute(select(Document).where(Document.id == doc_id))
            doc = result.scalar_one_or_none()

            if not doc:
                print(f"  SKIP: {pdf_path.name} - no matching Document row")
                skipped += 1
                continue

            if doc.raw_bytes is not None:
                print(f"  SKIP: {pdf_path.name} - raw_bytes already populated")
                skipped += 1
                continue

            # Read file and update document
            try:
                content = pdf_path.read_bytes()
                doc.raw_bytes = content
                await db.commit()
                print(f"  OK: {pdf_path.name} - backfilled {len(content)} bytes")
                updated += 1
            except Exception as e:
                await db.rollback()
                print(f"  ERROR: {pdf_path.name} - {e}")
                errors += 1

    await engine.dispose()

    print(f"\nSummary: {updated} updated, {skipped} skipped, {errors} errors")


if __name__ == "__main__":
    asyncio.run(main())