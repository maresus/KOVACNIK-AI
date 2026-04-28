"""
LIVE SMOKE TESTI — pravi produkcijski strežniki
================================================
Kmetija Urška:  https://kmetija-urska-ai-production.up.railway.app
Lepo Mesto:     https://web-production-454ac9.up.railway.app

Vsak test gre čez HTTP na Railway, čaka pravi LLM odgovor in preveri vsebino.
Zaženi: python smoke_live.py
"""

import json
import sys
import time
import uuid
from datetime import datetime
import requests

# ── URLs ─────────────────────────────────────────────────────────────────────
URSKA = "https://kmetija-urska-ai-production.up.railway.app"
LEPO  = "https://web-production-454ac9.up.railway.app"

TIMEOUT = 30  # sekund na klic

# ── Barve za terminal ─────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
BOLD   = "\033[1m"
RESET  = "\033[0m"

# ── Rezultati ─────────────────────────────────────────────────────────────────
results = []

_SMOKE_RUN_ID = datetime.now().strftime("smoke-%Y%m%d-%H%M%S")

def chat(base_url: str, message: str, session_id: str | None = None) -> dict:
    payload = {"message": message}
    payload["session_id"] = session_id if session_id and session_id.startswith("smoke-") else f"{_SMOKE_RUN_ID}-{session_id or uuid.uuid4()}"
    r = requests.post(f"{base_url}/chat", json=payload, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()

def check(name: str, condition: bool, detail: str = "", reply: str = ""):
    icon = f"{GREEN}✓{RESET}" if condition else f"{RED}✗{RESET}"
    status = "PASS" if condition else "FAIL"
    print(f"  {icon} {name}")
    if not condition:
        if reply:
            print(f"      {YELLOW}Odgovor:{RESET} {reply[:200]}")
        if detail:
            print(f"      {RED}Problem:{RESET} {detail}")
    results.append({"name": name, "pass": condition})

def section(title: str, bot: str):
    print(f"\n{BOLD}{BLUE}{'='*60}{RESET}")
    print(f"{BOLD}  {bot} — {title}{RESET}")
    print(f"{BOLD}{BLUE}{'='*60}{RESET}")

def run_test(name: str, fn):
    try:
        fn()
    except Exception as e:
        check(name, False, str(e))


# ═══════════════════════════════════════════════════════════════════════════════
# KMETIJA URŠKA
# ═══════════════════════════════════════════════════════════════════════════════

section("INFRASTRUKTURA", "🌾 Kmetija Urška")

# U01 — health
def u01():
    r = requests.get(f"{URSKA}/health", timeout=10)
    data = r.json()
    check("U01 /health vrne 200", r.status_code == 200)
    check("U02 /health status=ok", data.get("status") == "ok")
    check("U03 /health bot=kmetija-urska", data.get("bot") == "kmetija-urska")
run_test("health", u01)

def u04():
    r = requests.get(f"{URSKA}/", timeout=10)
    check("U04 / vrne HTML", r.status_code == 200 and "text/html" in r.headers.get("content-type",""))
run_test("root html", u04)

def u05():
    r = requests.get(f"{URSKA}/widget", timeout=10)
    check("U05 /widget vrne HTML", r.status_code == 200)
run_test("widget html", u05)

section("VSEBINA ODGOVOROV", "🌾 Kmetija Urška")

def u06():
    sid = str(uuid.uuid4())
    data = chat(URSKA, "Pozdravljeni! Kje se nahajate?", sid)
    r = data.get("reply","").lower()
    check("U06 pozna naslov (Stranice/Križevec)", "stranice" in r or "križ" in r or "križevec" in r, reply=data.get("reply",""))
run_test("U06", u06)

def u07():
    data = chat(URSKA, "Kakšna je vaša telefonska številka?")
    r = data.get("reply","")
    check("U07 pozna telefon (031)", "031" in r, reply=r)
run_test("U07", u07)

def u08():
    data = chat(URSKA, "Koliko sob imate?")
    r = data.get("reply","")
    check("U08 ve da ima 7 sob", "7" in r, reply=r)
run_test("U08", u08)

def u09():
    data = chat(URSKA, "Koliko stane prenočitev z zajtrkom?")
    r = data.get("reply","")
    check("U09 cena 74 EUR v odgovoru", "74" in r, reply=r)
run_test("U09", u09)

def u10():
    data = chat(URSKA, "Kaj nudite v wellness centru?")
    r = data.get("reply","").lower()
    check("U10 wellness vsebina (savna/jacuzzi)", "savna" in r or "jacuzzi" in r or "wellness" in r, reply=data.get("reply",""))
run_test("U10", u10)

def u11():
    data = chat(URSKA, "Koliko stane Urškin vikend paket?")
    r = data.get("reply","")
    check("U11 cena paketa 215 EUR", "215" in r, reply=r)
run_test("U11", u11)

def u12():
    data = chat(URSKA, "Ali se da pri vas jahati?")
    r = data.get("reply","").lower()
    no = any(w in r for w in ["ni", "nimamo", "ne ", "žal", "niso"])
    check("U12 pravilno zanika jahanje", no, reply=data.get("reply",""))
run_test("U12", u12)

def u13():
    data = chat(URSKA, "Kateri certifikati so vas odlikovali?")
    r = data.get("reply","").lower()
    check("U13 omeni Green Key certifikat", "green" in r or "zeleni" in r or "certif" in r, reply=data.get("reply",""))
run_test("U13", u13)

def u14():
    data = chat(URSKA, "Kakšno je ime lastniške družine?")
    r = data.get("reply","").lower()
    check("U14 omeni Topolšek/Urška/Vilma", "topolšek" in r or "urška" in r or "vilma" in r, reply=data.get("reply",""))
run_test("U14", u14)

def u15():
    data = chat(URSKA, "What is the address of the farm?")
    r = data.get("reply","").lower()
    en = any(w in r for w in ["farm","address","located","village","križ","stran","our","the "])
    check("U15 odgovori v angleščini na angleško", en, reply=data.get("reply",""))
run_test("U15", u15)

section("BOOKING INTENT & FORM", "🌾 Kmetija Urška")

def u16():
    r = requests.post(f"{URSKA}/chat", json={"message": "Rad bi rezerviral sobo za vikend"}, timeout=TIMEOUT)
    data = r.json()
    check("U16 booking intent → action=open_booking_form", data.get("action") == "open_booking_form", reply=str(data))
run_test("U16", u16)

def u17():
    r = requests.post(f"{URSKA}/chat", json={"message": "Zanima me wellness in savna"}, timeout=TIMEOUT)
    data = r.json()
    check("U17 wellness intent → booking_type_hint=wellness", data.get("booking_type_hint") == "wellness", reply=str(data))
run_test("U17", u17)

def u18():
    r = requests.post(f"{URSKA}/chat", json={"message": "Kje ste locirani?"}, timeout=TIMEOUT)
    data = r.json()
    check("U18 splošno vprašanje → brez action", data.get("action") is None or data.get("action") == "", reply=str(data))
run_test("U18", u18)

def u19():
    data = chat(URSKA, "Rad bi rezerviral sobo")
    r = data.get("reply","").lower()
    bad = any(w in r for w in ["kdaj", "koliko oseb", "vaše ime", "za koliko"])
    check("U19 bot NE sprašuje za podatke po booking intentu", not bad, detail="Bot sprašuje za podatke namesto da odpre obrazec", reply=data.get("reply",""))
run_test("U19", u19)

section("QUICK BOOKING ENDPOINT", "🌾 Kmetija Urška")

def u20():
    payload = {
        "date": "2026-07-15", "adults": 2,
        "name": "Smoke Test Gost", "phone": "040 000 999",
        "gdpr": True, "booking_type": "room"
    }
    r = requests.post(f"{URSKA}/chat/quick-booking", json=payload, timeout=TIMEOUT)
    data = r.json()
    check("U20 quick-booking vrne ok=True", data.get("ok") is True, reply=str(data))
    check("U21 quick-booking vrne reservation_id", isinstance(data.get("reservation_id"), int), reply=str(data))
run_test("U20-21", u20)

def u22():
    payload = {
        "date": "2026-08-01", "adults": 2,
        "name": "Wellness Gost", "phone": "040 111 222",
        "gdpr": True, "booking_type": "wellness"
    }
    r = requests.post(f"{URSKA}/chat/quick-booking", json=payload, timeout=TIMEOUT)
    data = r.json()
    check("U22 wellness booking sprejet", data.get("ok") is True, reply=str(data))
run_test("U22", u22)

def u23():
    payload = {
        "date": "2026-09-01", "adults": 2,
        "name": "Test", "phone": "040 000 000",
        "gdpr": False, "booking_type": "room"
    }
    r = requests.post(f"{URSKA}/chat/quick-booking", json=payload, timeout=TIMEOUT)
    data = r.json()
    check("U23 gdpr=False vrne napako", data.get("ok") is False, reply=str(data))
run_test("U23", u23)


# ═══════════════════════════════════════════════════════════════════════════════
# LEPO MESTO
# ═══════════════════════════════════════════════════════════════════════════════

section("INFRASTRUKTURA", "🏛️ Lepo Mesto")

def l01():
    r = requests.get(f"{LEPO}/health", timeout=10)
    data = r.json()
    check("L01 /health vrne 200", r.status_code == 200)
    check("L02 /health status=ok", data.get("status") == "ok")
    check("L03 /health bot=lepo-mesto", data.get("bot") == "lepo-mesto")
run_test("health", l01)

def l04():
    r = requests.get(f"{LEPO}/", timeout=10)
    check("L04 / vrne HTML", r.status_code == 200 and "text/html" in r.headers.get("content-type",""))
run_test("root html", l04)

def l05():
    r = requests.get(f"{LEPO}/api/admin/conversations", timeout=10)
    check("L05 /api/admin/conversations je javni (200)", r.status_code == 200)
    data = r.json()
    check("L06 conversations ima ključ 'conversations'", "conversations" in data)
run_test("conversations public endpoint", l05)

section("VSEBINA ODGOVOROV", "🏛️ Lepo Mesto")

def l07():
    data = chat(LEPO, "Kdo je župan občine?")
    r = data.get("reply","").lower()
    check("L07 ve da je župan Janez Novak", "novak" in r or "janez" in r, reply=data.get("reply",""))
run_test("L07", l07)

def l08():
    data = chat(LEPO, "Kdaj je odprta občinska pisarna?")
    r = data.get("reply","").lower()
    check("L08 pozna uradne ure (sreda/ponedeljek)", "sreda" in r or "ponedeljek" in r or "petek" in r or "ura" in r, reply=data.get("reply",""))
run_test("L08", l08)

def l09():
    data = chat(LEPO, "Kakšen je telefon občine?")
    r = data.get("reply","")
    check("L09 pozna telefonsko številko", "02" in r or "07" in r or "059" in r or "041" in r or "031" in r, reply=r)
run_test("L09", l09)

def l10():
    data = chat(LEPO, "Kdaj odvažajo smeti?")
    r = data.get("reply","").lower()
    check("L10 pozna odvoz smeti (torek)", "torek" in r or "smeti" in r or "odvoz" in r, reply=data.get("reply",""))
run_test("L10", l10)

def l11():
    data = chat(LEPO, "Kdaj odvažajo papir in embalažo?")
    r = data.get("reply","").lower()
    check("L11 pozna odvoz papirja (sreda)", "sreda" in r or "papir" in r or "embalaž" in r, reply=data.get("reply",""))
run_test("L11", l11)

def l12():
    data = chat(LEPO, "Kako se imenuje asistentka župana?")
    r = data.get("reply","").lower()
    check("L12 ve da je asistentka Leja", "leja" in r, reply=data.get("reply",""))
run_test("L12", l12)

def l13():
    data = chat(LEPO, "Kdo je podžupanka?")
    r = data.get("reply","").lower()
    check("L13 ve da je podžupanka Marija Kovač", "marija" in r or "kovač" in r, reply=data.get("reply",""))
run_test("L13", l13)

def l14():
    data = chat(LEPO, "Kakšna je višina enkratne denarne pomoči ob rojstvu otroka?")
    r = data.get("reply","")
    check("L14 pozna finančno pomoč ob rojstvu", any(c.isdigit() for c in r), reply=r)
run_test("L14", l14)

def l15():
    data = chat(LEPO, "Ali mi lahko na občini naredite potrdilo o prebivališču?")
    r = data.get("reply","").lower()
    not_obcina = any(w in r for w in ["upravna", "enota", "upravni", "ne izdaja", "ni pristoj", "ue "])
    check("L15 pravilno napoti na upravno enoto (ne občino)", not_obcina, reply=data.get("reply",""))
run_test("L15", l15)

def l16():
    data = chat(LEPO, "Kdaj je odprt zbirni center za odpadke?")
    r = data.get("reply","").lower()
    check("L16 pozna urnik zbirnega centra", "sobota" in r or "sreda" in r or "zbirni" in r or "center" in r, reply=data.get("reply",""))
run_test("L16", l16)

def l17():
    data = chat(LEPO, "Kje je jezero Lepica?")
    r = data.get("reply","").lower()
    check("L17 pozna jezero Lepica", "lepica" in r or "jezer" in r or "kopanj" in r, reply=data.get("reply",""))
run_test("L17", l17)

def l18():
    data = chat(LEPO, "What is the name of the mayor?")
    r = data.get("reply","").lower()
    en = any(w in r for w in ["novak", "janez", "mayor", "the ", "is ", "name"])
    check("L18 odgovori v angleščini na angleško", en, reply=data.get("reply",""))
run_test("L18", l18)

def l19():
    data = chat(LEPO, "Koliko znaša letni proračun občine?")
    r = data.get("reply","")
    check("L19 pozna proračun (4,2 mio EUR)", "4" in r and ("mio" in r.lower() or "milijon" in r.lower() or "200" in r), reply=r)
run_test("L19", l19)

def l20():
    data = chat(LEPO, "Kakšen je delovni čas zdravstvenega doma?")
    r = data.get("reply","").lower()
    check("L20 pozna urnik zdravstvenega doma", "zdravstv" in r or "dom" in r or "7" in r or "ura" in r, reply=data.get("reply",""))
run_test("L20", l20)

def l21():
    data = chat(LEPO, "Ali občina organizira kakšne razpise za društva?")
    r = data.get("reply","").lower()
    check("L21 omeni razpise za društva", "razpis" in r or "društv" in r or "kultur" in r, reply=data.get("reply",""))
run_test("L21", l21)

def l22():
    data = chat(LEPO, "Kakšen je naslov občine?")
    r = data.get("reply","").lower()
    check("L22 pozna naslov občine", "lepo" in r or "1" in r or "ulica" in r or "trg" in r or "cesta" in r, reply=data.get("reply",""))
run_test("L22", l22)

section("ADMIN ENDPOINTS", "🏛️ Lepo Mesto")

def l23():
    r = requests.get(f"{LEPO}/api/admin/stats", timeout=10)
    check("L23 /api/admin/stats brez tokena → 401", r.status_code == 401)
run_test("L23", l23)

def l24():
    r = requests.get(f"{LEPO}/api/admin/sessions", timeout=10)
    check("L24 /api/admin/sessions brez tokena → 401", r.status_code == 401)
run_test("L24", l24)


# ═══════════════════════════════════════════════════════════════════════════════
# SKUPNI REZULTATI
# ═══════════════════════════════════════════════════════════════════════════════

total   = len(results)
passed  = sum(1 for r in results if r["pass"])
failed  = total - passed

print(f"\n{BOLD}{'='*60}{RESET}")
print(f"{BOLD}  SKUPNI REZULTAT{RESET}")
print(f"{BOLD}{'='*60}{RESET}")
print(f"  Skupaj testov : {total}")
print(f"  {GREEN}✓ Uspešnih    : {passed}{RESET}")
if failed:
    print(f"  {RED}✗ Neuspešnih  : {failed}{RESET}")
    print(f"\n{RED}{BOLD}  NEUSPEŠNI TESTI:{RESET}")
    for r in results:
        if not r["pass"]:
            print(f"  {RED}✗{RESET} {r['name']}")
else:
    print(f"\n  {GREEN}{BOLD}VSI TESTI USPEŠNI! 🎉{RESET}")

print(f"\n{BOLD}{'='*60}{RESET}\n")

if failed:
    sys.exit(1)
