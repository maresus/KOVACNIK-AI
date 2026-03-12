"""
Email Draft Generator Service

Automatically generates draft email responses using GPT-4 and saves them to IMAP Drafts folder.
Filters out advertising/spam emails and generates contextual responses based on knowledge base.
"""

import os
import re
import imaplib
from email import message_from_bytes
from email.header import decode_header
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional, List

from app.core.llm_client import get_llm_client
from app.rag.knowledge_base import search_knowledge

# IMAP Configuration
IMAP_HOST = os.getenv("IMAP_HOST", "").strip()
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER = os.getenv("IMAP_USER", "").strip()
IMAP_PASSWORD = os.getenv("IMAP_PASSWORD", "").strip()
IMAP_SSL = os.getenv("IMAP_SSL", "").strip().lower() in {"1", "true", "yes"}

# Draft generation settings
DRAFT_GENERATION_ENABLED = os.getenv("DRAFT_GENERATION_ENABLED", "true").lower() == "true"

# Spam/advertising detection patterns
SPAM_PATTERNS = [
    r"unsubscribe",
    r"newsletter",
    r"marketing@",
    r"noreply@",
    r"no-reply@",
    r"automated",
    r"notifications@",
    r"support@",
    r"invoice",
    r"payment confirmation",
    r"order confirmation",
]


def _decode_header(value: Optional[str]) -> str:
    """Decode email header (subject, from, etc.)."""
    if not value:
        return ""
    decoded_parts = decode_header(value)
    parts = []
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            try:
                parts.append(part.decode(encoding or "utf-8", errors="ignore"))
            except Exception:
                parts.append(part.decode("utf-8", errors="ignore"))
        else:
            parts.append(part)
    return "".join(parts)


def _extract_text(msg) -> str:
    """Extract plain text content from email message."""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = (part.get("Content-Disposition") or "").lower()
            if content_type == "text/plain" and "attachment" not in content_disposition:
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                return payload.decode(charset, errors="ignore").strip()
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True) or b""
                charset = part.get_content_charset() or "utf-8"
                html = payload.decode(charset, errors="ignore")
                return re.sub(r"<[^>]+>", " ", html).strip()
    payload = msg.get_payload(decode=True) or b""
    charset = msg.get_content_charset() or "utf-8"
    return payload.decode(charset, errors="ignore").strip()


def _is_spam_or_advertising(subject: str, from_email: str, body: str) -> bool:
    """
    Detect if email is spam/advertising.

    Returns True if email should be filtered out (spam/advertising).
    """
    combined = f"{subject} {from_email} {body}".lower()

    for pattern in SPAM_PATTERNS:
        if re.search(pattern, combined, re.IGNORECASE):
            return True

    return False


def _extract_email_address(from_field: str) -> str:
    """Extract email address from 'From' field."""
    match = re.search(r"<(.+?)>", from_field)
    if match:
        return match.group(1)
    # If no <>, assume the whole string is the email
    if "@" in from_field:
        return from_field.strip()
    return ""


DRAFT_GENERATION_PROMPT = """
Ti si Barbara Štern - lastnica Domačije Kovačnik na Pohorju. Pišeš oseben odgovor na email gosta.

TVOJ TON:
- Topel, prijazen, pristnen - kot da pišeš osebni email znancu
- Naravno, človeško - ne robotsko ali preveč uradno
- Osebno ("Pri nas je to zelo priljubljeno", "Vesela sem, da vas lahko gostimo")
- Uporabljaj "vi" obliko (vikaš)
- Emoji zmerno (0-2 max)

STRUKTURA ODGOVORA:
1. Pozdrav: "Pozdravljeni" / "Dober dan" / variiraj
2. Zahvala: "Hvala za vaše vprašanje / povpraševanje"
3. Odgovor: Kratek, jedrnat odgovor na vprašanje
4. Akcija: Konkretna napotitev ("Za rezervacijo me pokličite", "Več si lahko preberete na kovacnik.com/...", ipd.)
5. Podpis: "Prijazen pozdrav, Barbara Štern & družina, Domačija Kovačnik, www.kovacnik.com"

POMEMBNO:
- Odgovor naj bo kratek (3-5 stavkov)
- Ne izmišljaj si podatkov, ki jih nimaš
- Če so linki v kontekstu, jih uporabi
- Če nimaš informacije, pošlji nanje osebno ("Pokličite me na 02 601 54 00, da vse skupaj preverimo")
- Vedno zaključi z jasno akcijo za gosta

PRIMERI DOBRIH ODGOVOROV:

Email: "Zanima me, ali imate proste sobe 15.4.2026 za 2 osebi?"
Odgovor:
Pozdravljeni,

hvala za vaše povpraševanje! Za 15.4.2026 imam še proste sobe. Minimalno število noči je 2, cena pa je 50€/osebo/noč z zajtrkom vključno.

Če želite rezervirati, me pokličite na 02 601 54 00 ali 031 330 113, da preverim točno razpoložljivost.

Prijazen pozdrav,
Barbara Štern & družina
Domačija Kovačnik
www.kovacnik.com

---

Email: "Ali prodajate pohorsko bunko?"
Odgovor:
Pozdravljeni,

seveda! Pohorsko bunko pripravljamo sami po tradicionalnem receptu. Prodajamo jo v naši domači trgovini, lahko pa si jo ogledate tudi na spletni strani: www.kovacnik.com/izdelek/bunka/

Če želite večjo količino, me prosim pokličite vnaprej, da vam pripravim zadosti.

Prijazen pozdrav,
Barbara Štern & družina
Domačija Kovačnik
www.kovacnik.com

---

Email: "Hvala za informacije!"
Odgovor:
Pozdravljeni,

ni za kaj! Če boste potrebovali še kaj, sem vedno na voljo.

Prijazen pozdrav,
Barbara Štern & družina
Domačija Kovačnik
www.kovacnik.com

---

GENERIRAJ SEDAJ ODGOVOR NA EMAIL GOSTA.
"""


def _generate_draft_response(subject: str, body: str) -> Optional[str]:
    """
    Generate draft email response using GPT-4.

    Returns draft text or None if generation failed.
    """
    try:
        # Search knowledge base for relevant context
        knowledge_chunks = search_knowledge(body, top_k=3)

        context_parts = []
        for chunk in knowledge_chunks:
            ctx = f"Naslov: {chunk.title}\n"
            if chunk.url:
                ctx += f"URL: {chunk.url}\n"
            ctx += f"Vsebina: {chunk.paragraph}\n"
            context_parts.append(ctx)

        context_text = "\n---\n".join(context_parts) if context_parts else "Ni konteksta iz baze znanja."

        # Generate response with GPT-4
        client = get_llm_client()

        user_prompt = f"""
Prejeti email:
Zadeva: {subject}

Vsebina:
{body}

---

Kontekst iz baze znanja Kovačnik:
{context_text}

---

Generiraj kratek, oseben odgovor v Barbara's stilu.
"""

        response = client.responses.create(
            model="gpt-4.1",
            input=[
                {"role": "system", "content": DRAFT_GENERATION_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            max_output_tokens=500,
            temperature=0.8,
        )

        draft_text = getattr(response, "output_text", None)
        if not draft_text:
            # Try alternative output format
            outputs = []
            for block in getattr(response, "output", []) or []:
                for content in getattr(block, "content", []) or []:
                    text = getattr(content, "text", None)
                    if text:
                        outputs.append(text)
            draft_text = "\n".join(outputs).strip()

        return draft_text if draft_text else None

    except Exception as e:
        print(f"[DRAFT] Napaka pri generiranju odgovora: {e}")
        return None


def _save_draft_to_imap(
    to_email: str,
    subject: str,
    draft_body: str,
    in_reply_to: Optional[str] = None,
    references: Optional[str] = None
) -> bool:
    """
    Save draft email to IMAP Drafts folder.

    Returns True if successfully saved.
    """
    try:
        # Connect to IMAP
        if IMAP_SSL:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        else:
            mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

        mail.login(IMAP_USER, IMAP_PASSWORD)

        # Create email message
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Barbara Štern <{IMAP_USER}>"
        msg['To'] = to_email
        msg['Subject'] = f"Re: {subject}" if not subject.lower().startswith("re:") else subject
        msg['Date'] = datetime.now().strftime("%a, %d %b %Y %H:%M:%S %z")

        # Add reply headers for threading
        if in_reply_to:
            msg['In-Reply-To'] = in_reply_to
        if references:
            msg['References'] = references

        # Add body as plain text
        msg.attach(MIMEText(draft_body, 'plain', 'utf-8'))

        # Save to Drafts folder
        # Common Drafts folder names: "Drafts", "INBOX.Drafts", "[Gmail]/Drafts"
        drafts_folders = ["Drafts", "INBOX.Drafts", "[Gmail]/Drafts", "INBOX/Drafts"]

        saved = False
        for folder in drafts_folders:
            try:
                status = mail.append(folder, '\\Draft', None, msg.as_bytes())
                if status[0] == 'OK':
                    print(f"[DRAFT] Shranjen v mapo: {folder}")
                    saved = True
                    break
            except Exception:
                continue

        if not saved:
            # List available folders for debugging
            status, folders_list = mail.list()
            if status == 'OK':
                print(f"[DRAFT] Razpoložljive mape: {folders_list}")
            raise Exception("Ni bilo mogoče najti Drafts mape")

        mail.logout()
        return saved

    except Exception as e:
        print(f"[DRAFT] Napaka pri shranjevanju drafta: {e}")
        return False


def process_unread_emails() -> dict:
    """
    Process all unread emails and generate drafts.

    Returns summary statistics.
    """
    if not DRAFT_GENERATION_ENABLED:
        return {"enabled": False, "processed": 0, "drafts_created": 0, "filtered": 0}

    if not (IMAP_HOST and IMAP_USER and IMAP_PASSWORD):
        return {"error": "IMAP credentials missing", "processed": 0}

    stats = {
        "processed": 0,
        "drafts_created": 0,
        "filtered": 0,
        "errors": 0,
        "enabled": True
    }

    try:
        # Connect to IMAP
        if IMAP_SSL:
            mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        else:
            mail = imaplib.IMAP4(IMAP_HOST, IMAP_PORT)

        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select("INBOX")

        # Search for unread emails
        status, data = mail.search(None, "UNSEEN")
        if status != "OK" or not data or not data[0]:
            mail.logout()
            return stats

        email_ids = data[0].split()

        for email_id in email_ids:
            try:
                # Fetch email
                status, msg_data = mail.fetch(email_id, "(RFC822)")
                if status != "OK" or not msg_data:
                    continue

                msg = message_from_bytes(msg_data[0][1])

                # Extract email details
                subject = _decode_header(msg.get("Subject", ""))
                from_email = _decode_header(msg.get("From", ""))
                body = _extract_text(msg)
                message_id = _decode_header(msg.get("Message-ID", ""))
                references = _decode_header(msg.get("References", ""))

                stats["processed"] += 1

                # Filter spam/advertising
                if _is_spam_or_advertising(subject, from_email, body):
                    print(f"[DRAFT] Filtrirano (spam/advertising): {subject}")
                    stats["filtered"] += 1
                    # Mark as read
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    continue

                # Generate draft response
                draft_text = _generate_draft_response(subject, body)
                if not draft_text:
                    print(f"[DRAFT] Ni uspelo generirati odgovora za: {subject}")
                    stats["errors"] += 1
                    continue

                # Extract recipient email
                to_email = _extract_email_address(from_email)
                if not to_email:
                    print(f"[DRAFT] Ni bilo mogoče ekstraktirati email naslova iz: {from_email}")
                    stats["errors"] += 1
                    continue

                # Save draft
                saved = _save_draft_to_imap(
                    to_email=to_email,
                    subject=subject,
                    draft_body=draft_text,
                    in_reply_to=message_id,
                    references=f"{references} {message_id}".strip()
                )

                if saved:
                    stats["drafts_created"] += 1
                    print(f"[DRAFT] Ustvarjen draft za: {subject}")
                    # Mark original as read
                    mail.store(email_id, '+FLAGS', '\\Seen')
                else:
                    stats["errors"] += 1

            except Exception as e:
                print(f"[DRAFT] Napaka pri procesiranju emaila: {e}")
                stats["errors"] += 1
                continue

        mail.logout()
        return stats

    except Exception as e:
        stats["error"] = str(e)
        print(f"[DRAFT] Napaka pri povezovanju na IMAP: {e}")
        return stats


def generate_draft_for_email_now() -> None:
    """
    Manually trigger draft generation (for testing).

    Usage:
        from app.services.draft_generator_service import generate_draft_for_email_now
        generate_draft_for_email_now()
    """
    print(f"[DRAFT] Ročno sproženo generiranje draftov: {datetime.now()}")
    stats = process_unread_emails()
    print(f"[DRAFT] Rezultati: {stats}")


if __name__ == "__main__":
    # Test
    print("Testing draft generator...")
    generate_draft_for_email_now()
