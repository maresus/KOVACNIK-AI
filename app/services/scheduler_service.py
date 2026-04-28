"""
Scheduler Service - Runs periodic background tasks

Currently runs:
- Daily multi-bot report at 05:00 (Europe/Ljubljana)
- Hourly new-conversation alert at :02 (only if new convos exist)
- Weekly table reservation reminder (Thursday 18:00)
- Email draft generator (every hour)
"""

import os
import requests as _requests
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

    # Multi-bot dnevno poročilo ob 05:00
    _scheduler.add_job(
        func=lambda: _trigger_report("daily"),
        trigger=CronTrigger(hour=5, minute=0, timezone="Europe/Ljubljana"),
        id="daily_conversation_report",
        name="Daily Multi-Bot Report (05:00)",
        replace_existing=True,
    )

    # Urni alert — ob :02, samo če so novi pogovori
    _scheduler.add_job(
        func=lambda: _trigger_report("hourly"),
        trigger=CronTrigger(minute=2, timezone="Europe/Ljubljana"),
        id="hourly_alert",
        name="Hourly New Conversation Alert",
        replace_existing=True,
    )

    # Weekly table reservation reminder - every Thursday at 18:00
    weekly_reminder_time = os.getenv("WEEKLY_REMINDER_TIME", "18:00")
    w_hour, w_minute = map(int, weekly_reminder_time.split(":"))

    _scheduler.add_job(
        func=_run_weekly_reminder,
        trigger=CronTrigger(day_of_week="thu", hour=w_hour, minute=w_minute),
        id="weekly_table_reminder",
        name="Weekly Table Reservation Reminder",
        replace_existing=True,
    )

    # Email draft generation - every hour
    _scheduler.add_job(
        func=_run_draft_generator,
        trigger=CronTrigger(minute=0),
        id="email_draft_generator",
        name="Email Draft Generator",
        replace_existing=True,
    )

    _scheduler.start()
    print("[SCHEDULER] Zagnan: dnevno ob 05:00, urno ob :02, tedenski reminder, draft generator")


def stop_scheduler():
    """Ustavi scheduler."""
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown()
        _scheduler = None
        print("[SCHEDULER] Ustavljen")


def _trigger_report(mode: str) -> None:
    """Pokliče multi-bot report endpoint lokalno."""
    try:
        port = int(os.environ.get("PORT", 8000))
        r = _requests.get(
            f"http://localhost:{port}/api/admin/notify/daily-report",
            params={"mode": mode},
            timeout=120,
        )
        print(f"[SCHEDULER] {mode} report: {r.text[:120]}")
    except Exception as e:
        print(f"[SCHEDULER] {mode} report error: {e}")


def _run_daily_report():
    """Wrapper za zagon dnevnega poročila (staro - ne uporablja se več)."""
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


def _run_weekly_reminder():
    """Wrapper za zagon tedenskega reminderja rezervacij."""
    from app.services.daily_report_service import generate_and_send_weekly_reminder

    print(f"[SCHEDULER] Zaganjalnik tedenskega reminderja: {datetime.now()}")
    try:
        success = generate_and_send_weekly_reminder()
        if success:
            print("[SCHEDULER] Tedenski reminder uspešno poslan")
        else:
            print("[SCHEDULER] Tedenski reminder ni bil poslan")
    except Exception as e:
        print(f"[SCHEDULER] Napaka pri tedenskem reminderju: {e}")
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


def trigger_weekly_reminder_now():
    """
    Ročno sproži tedenski reminder (za testiranje).

    Uporaba:
        from app.services.scheduler_service import trigger_weekly_reminder_now
        trigger_weekly_reminder_now()
    """
    print("[SCHEDULER] Ročno sprožen tedenski reminder")
    _run_weekly_reminder()


def _run_draft_generator():
    """Wrapper za zagon email draft generatorja."""
    from app.services.draft_generator_service import process_unread_emails

    print(f"[SCHEDULER] Zaganjalnik email draft generatorja: {datetime.now()}")
    try:
        stats = process_unread_emails()
        print(f"[SCHEDULER] Draft generator rezultati: {stats}")
    except Exception as e:
        print(f"[SCHEDULER] Napaka pri draft generatorju: {e}")
        import traceback
        traceback.print_exc()


def trigger_draft_generator_now():
    """
    Ročno sproži draft generator (za testiranje).

    Uporaba:
        from app.services.scheduler_service import trigger_draft_generator_now
        trigger_draft_generator_now()
    """
    print("[SCHEDULER] Ročno sprožen draft generator")
    _run_draft_generator()


# For testing
if __name__ == "__main__":
    print("Testing scheduler...")
    trigger_daily_report_now()
    print("\n")
    trigger_weekly_reminder_now()
