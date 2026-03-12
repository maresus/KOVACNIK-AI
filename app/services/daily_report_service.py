"""
Daily Conversation Report Service - Kovačnik AI

Generates and sends daily email reports of all chatbot conversations
to marko@creative-media.si every morning at 7:00.

FEATURES:
- Aggregates conversations since last report
- Groups messages by session
- Shows full conversation transcripts
- Highlights potential bugs/issues
- Provides summary statistics
"""

import os
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from app.services.email_service import _send_email, _email_wrapper, BRAND_COLOR, BORDER_COLOR, MUTED_COLOR

# Configuration
REPORT_EMAIL = os.getenv("DAILY_REPORT_EMAIL", "marko@creative-media.si")
REPORT_STATE_FILE = Path(__file__).resolve().parent.parent.parent / "data" / "last_report.txt"


def get_last_report_time() -> datetime:
    """
    Prebere čas zadnjega poročila iz datoteke.
    Če datoteka ne obstaja, vrne čas pred 24 urami.
    """
    if REPORT_STATE_FILE.exists():
        try:
            timestamp_str = REPORT_STATE_FILE.read_text().strip()
            return datetime.fromisoformat(timestamp_str)
        except Exception:
            pass

    # Default: 24 ur nazaj
    return datetime.now() - timedelta(hours=24)


def save_report_time(timestamp: datetime) -> None:
    """Shrani čas zadnjega poročila."""
    REPORT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    REPORT_STATE_FILE.write_text(timestamp.isoformat())


def get_new_conversations(service, since: datetime) -> List[Dict[str, Any]]:
    """
    Pridobi vse pogovore od določenega časa naprej.

    Args:
        service: ReservationService instance
        since: Datum/čas od katerega naprej iščemo

    Returns:
        List of conversation dicts with session grouping
    """
    # Get all conversations since timestamp
    conn = service._conn()
    cursor = conn.cursor()
    ph = service._placeholder()

    query = f"""
        SELECT session_id, user_message, bot_response, intent,
               needs_followup, followup_email, created_at
        FROM conversations
        WHERE created_at >= {ph}
        ORDER BY created_at ASC
    """

    cursor.execute(query, (since.isoformat(),))
    rows = cursor.fetchall()

    # Group by session
    sessions = {}
    for row in rows:
        session_id = row[0]
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "messages": [],
                "intents": set(),
                "needs_followup": False,
                "email": None,
                "first_message_time": row[6],
            }

        sessions[session_id]["messages"].append({
            "user": row[1],
            "bot": row[2],
            "intent": row[3],
            "time": row[6],
        })

        if row[3]:
            sessions[session_id]["intents"].add(row[3])

        if row[4]:  # needs_followup
            sessions[session_id]["needs_followup"] = True

        if row[5]:  # followup_email
            sessions[session_id]["email"] = row[5]

    cursor.close()
    conn.close()

    return list(sessions.values())


def _format_session_html(session: Dict[str, Any], index: int) -> str:
    """Formatira en session pogovora v HTML."""
    session_id = session["session_id"]
    messages = session["messages"]
    intents = ", ".join(sorted(session["intents"])) if session["intents"] else "—"
    email = session.get("email") or "—"
    needs_followup = session.get("needs_followup", False)
    first_time = datetime.fromisoformat(session["first_message_time"]).strftime("%d.%m.%Y %H:%M")

    # Warning badge if needs followup
    warning = ""
    if needs_followup:
        warning = f"""
        <span style="display:inline-block; background:#ef4444; color:#fff; padding:4px 10px; border-radius:6px; font-size:12px; font-weight:700; margin-left:8px;">
            ⚠️ POTREBUJE ODGOVOR
        </span>
        """

    # Message transcript
    transcript = ""
    for msg in messages:
        msg_time = datetime.fromisoformat(msg["time"]).strftime("%H:%M")
        user_msg = msg["user"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        bot_msg = msg["bot"].replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        intent_tag = f" <code style='font-size:11px; color:#888;'>[{msg['intent']}]</code>" if msg["intent"] else ""

        transcript += f"""
        <div style="margin:12px 0; padding:10px; background:#f9fafb; border-left:3px solid #e5e7eb; border-radius:6px;">
            <div style="color:#6b7280; font-size:12px; margin-bottom:6px;">
                <strong>Gost</strong> · {msg_time}
            </div>
            <div style="color:#111827; line-height:1.6;">
                {user_msg}
            </div>
        </div>

        <div style="margin:12px 0 12px 20px; padding:10px; background:#fef3c7; border-left:3px solid {BRAND_COLOR}; border-radius:6px;">
            <div style="color:#92400e; font-size:12px; margin-bottom:6px;">
                <strong>Bot</strong> · {msg_time}{intent_tag}
            </div>
            <div style="color:#451a03; line-height:1.6;">
                {bot_msg}
            </div>
        </div>
        """

    return f"""
    <div style="margin:24px 0; padding:20px; background:#fff; border:2px solid {BORDER_COLOR}; border-radius:12px;">
        <div style="margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid {BORDER_COLOR};">
            <h3 style="margin:0; color:{BRAND_COLOR}; font-size:16px;">
                Pogovor #{index} {warning}
            </h3>
            <div style="margin-top:8px; font-size:13px; color:{MUTED_COLOR};">
                <strong>Session ID:</strong> {session_id}<br>
                <strong>Prvi kontakt:</strong> {first_time}<br>
                <strong>Intenti:</strong> {intents}<br>
                <strong>Email:</strong> {email}
            </div>
        </div>

        {transcript}
    </div>
    """


def _generate_report_html(conversations: List[Dict[str, Any]], since: datetime, now: datetime) -> str:
    """Generira HTML report vseh pogovorov."""
    total_conversations = len(conversations)
    total_messages = sum(len(c["messages"]) for c in conversations)
    needs_followup = sum(1 for c in conversations if c.get("needs_followup"))

    # Intent statistics
    intent_counts = {}
    for conv in conversations:
        for intent in conv["intents"]:
            intent_counts[intent] = intent_counts.get(intent, 0) + 1

    top_intents = sorted(intent_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    intent_list = "<br>".join([f"• {intent}: {count}x" for intent, count in top_intents]) if top_intents else "—"

    # Period formatting
    since_str = since.strftime("%d.%m.%Y %H:%M")
    now_str = now.strftime("%d.%m.%Y %H:%M")

    # Summary box
    summary = f"""
    <div style="background:{BRAND_COLOR}; color:#fff; padding:20px; border-radius:10px; margin-bottom:24px;">
        <h2 style="margin:0 0 16px 0; font-size:20px;">📊 Dnevno poročilo - Kovačnik AI</h2>
        <div style="font-size:14px; line-height:1.8;">
            <strong>Obdobje:</strong> {since_str} → {now_str}<br>
            <strong>Skupaj pogovorov:</strong> {total_conversations}<br>
            <strong>Skupaj sporočil:</strong> {total_messages}<br>
            <strong>Potrebuje odgovor:</strong> {needs_followup}
        </div>
    </div>

    <div style="background:#fef3c7; border-left:4px solid #f59e0b; padding:16px; border-radius:8px; margin-bottom:24px;">
        <div style="font-size:14px; color:#92400e;">
            <strong>Najbolj pogosti intenti:</strong><br>
            <div style="margin-top:8px; line-height:1.8;">
                {intent_list}
            </div>
        </div>
    </div>
    """

    # No conversations
    if total_conversations == 0:
        content = summary + f"""
        <div style="padding:40px; text-align:center; background:#f9fafb; border-radius:10px; color:{MUTED_COLOR};">
            <p style="margin:0; font-size:16px;">Ni novih pogovorov v tem obdobju.</p>
        </div>
        """
        return _email_wrapper(content)

    # Conversations
    conversations_html = ""
    for i, conv in enumerate(conversations, start=1):
        conversations_html += _format_session_html(conv, i)

    content = f"""
    {summary}

    <h2 style="color:{BRAND_COLOR}; font-size:18px; margin:32px 0 16px 0; padding-bottom:8px; border-bottom:2px solid {BORDER_COLOR};">
        💬 Vsi pogovori
    </h2>

    {conversations_html}

    <div style="margin-top:32px; padding:16px; background:#f0fdf4; border:1px solid #86efac; border-radius:8px; font-size:13px; color:#166534;">
        <strong>Naslednje poročilo:</strong> Jutri ob 7:00<br>
        <strong>Admin panel:</strong> <a href="https://kovacnik-ai.up.railway.app/admin" style="color:{BRAND_COLOR};">Ogled vseh rezervacij</a>
    </div>
    """

    return _email_wrapper(content)


def generate_and_send_daily_report() -> bool:
    """
    Glavna funkcija za generiranje in pošiljanje dnevnega poročila.

    Returns:
        True če uspešno poslano
    """
    from app.services.reservation_service import ReservationService

    try:
        service = ReservationService()
        now = datetime.now()
        since = get_last_report_time()

        print(f"[DAILY REPORT] Generiram poročilo: {since.isoformat()} → {now.isoformat()}")

        # Get conversations
        conversations = get_new_conversations(service, since)

        print(f"[DAILY REPORT] Najdenih {len(conversations)} pogovorov")

        # Generate HTML
        html = _generate_report_html(conversations, since, now)

        # Send email
        subject = f"Kovačnik AI - Dnevno poročilo ({now.strftime('%d.%m.%Y')})"
        success = _send_email(REPORT_EMAIL, subject, html)

        if success:
            # Save report time
            save_report_time(now)
            print(f"[DAILY REPORT] Poročilo uspešno poslano na {REPORT_EMAIL}")
        else:
            print(f"[DAILY REPORT] Napaka pri pošiljanju poročila")

        return success

    except Exception as e:
        print(f"[DAILY REPORT] Napaka: {e}")
        import traceback
        traceback.print_exc()
        return False


# Test function
if __name__ == "__main__":
    print("Testing daily report generation...")
    generate_and_send_daily_report()
