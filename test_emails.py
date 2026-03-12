#!/usr/bin/env python
"""Test script za preverjanje email funkcionalnosti"""
from pathlib import Path
from dotenv import load_dotenv

# Load .env FIRST before any other imports
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Now import the services
from app.services.scheduler_service import (
    trigger_daily_report_now,
    trigger_weekly_reminder_now,
    trigger_draft_generator_now
)

if __name__ == "__main__":
    print("=" * 60)
    print("TEST DNEVNEGA POROČILA")
    print("=" * 60)
    trigger_daily_report_now()

    print("\n" + "=" * 60)
    print("TEST TEDENSKEGA REMINDERJA")
    print("=" * 60)
    trigger_weekly_reminder_now()

    print("\n" + "=" * 60)
    print("TEST EMAIL DRAFT GENERATORJA")
    print("=" * 60)
    trigger_draft_generator_now()

    print("\n✅ Test končan")
