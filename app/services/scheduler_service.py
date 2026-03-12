"""
Scheduler Service - Runs periodic background tasks

Currently runs:
- Daily conversation report at 7:00 AM
"""

import os
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime

# Global scheduler instance
_scheduler = None


def start_scheduler():
    """
    Zažene scheduler za periodične naloge.
    Kliče se ob startup aplikacije v main.py
    """
    global _scheduler

    if _scheduler is not None:
        print("[SCHEDULER] Že zagnan, preskakujem")
        return

    # Check if scheduler should be enabled
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    if not scheduler_enabled:
        print("[SCHEDULER] Onemogočen (SCHEDULER_ENABLED=false)")
        return

    _scheduler = AsyncIOScheduler(timezone="Europe/Ljubljana")

    # Daily report at 7:00 AM
    daily_report_time = os.getenv("DAILY_REPORT_TIME", "7:00")  # Format: "HH:MM"
    hour, minute = map(int, daily_report_time.split(":"))

    _scheduler.add_job(
        func=_run_daily_report,
        trigger=CronTrigger(hour=hour, minute=minute),
        id="daily_conversation_report",
        name="Daily Conversation Report",
        replace_existing=True,
    )

    _scheduler.start()
    print(f"[SCHEDULER] Zagnan - dnevno poročilo ob {daily_report_time}")


def stop_scheduler():
    """Ustavi scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        print("[SCHEDULER] Ustavljen")


def _run_daily_report():
    """Wrapper za zagon dnevnega poročila."""
    from app.services.daily_report_service import generate_and_send_daily_report

    print(f"[SCHEDULER] Zaganjalnik dnevnega poročila: {datetime.now()}")
    try:
        success = generate_and_send_daily_report()
        if success:
            print("[SCHEDULER] Dnevno poročilo uspešno poslano")
        else:
            print("[SCHEDULER] Dnevno poročilo ni bilo poslano")
    except Exception as e:
        print(f"[SCHEDULER] Napaka pri dnevnem poročilu: {e}")
        import traceback
        traceback.print_exc()


def trigger_daily_report_now():
    """
    Ročno sproži dnevno poročilo (za testiranje).

    Uporaba:
        from app.services.scheduler_service import trigger_daily_report_now
        trigger_daily_report_now()
    """
    print("[SCHEDULER] Ročno sproženo dnevno poročilo")
    _run_daily_report()


# For testing
if __name__ == "__main__":
    print("Testing scheduler...")
    trigger_daily_report_now()
