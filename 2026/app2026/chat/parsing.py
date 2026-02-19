from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional


def extract_people_count(message: str) -> Optional[int]:
    """
    Ekstrahira skupno število oseb iz sporočila.
    Podpira formate:
      - "2+2" ali "2 + 2"
      - "2 odrasla in 2 otroka"
      - "4 osebe"
    """
    explicit_match = re.search(r"za\s+(\d+)", message, re.IGNORECASE)
    if explicit_match:
        return int(explicit_match.group(1))

    cleaned = re.sub(r"\d{1,2}\.\d{1,2}\.\d{2,4}", " ", message)
    cleaned = re.sub(r"\d{1,2}:\d{2}", " ", cleaned)
    nums = re.findall(r"\d+", cleaned)
    if not nums:
        return None
    # če najdemo več števil, jih seštejemo (uporabno za "2 odrasla in 2 otroka"),
    # a če je naveden skupni "za X oseb", uporabimo zadnjo številko
    if len(nums) > 1:
        tail_people = re.search(r"(\d+)\s*(oseb|osbe|osob|people|persons)", cleaned, re.IGNORECASE)
        if tail_people:
            return int(tail_people.group(1))
        if "za" in message.lower():
            return int(nums[-1])
        return sum(int(n) for n in nums)
    return int(nums[0])


def parse_people_count(message: str) -> dict[str, Optional[str | int]]:
    """
    Vrne slovar: {total, adults, kids, ages}
    Podpira formate:
      - "4 osebe"
      - "2+2" ali "2 + 2"
      - "2 odrasla + 2 otroka"
      - "2 odrasla, 2 otroka (3 in 7 let)"
    """
    result: dict[str, Optional[str | int]] = {"total": None, "adults": None, "kids": None, "ages": None}
    ages_match = re.search(r"\(([^)]*let[^)]*)\)", message)
    if ages_match:
        result["ages"] = ages_match.group(1).strip()

    plus_match = re.search(r"(\d+)\s*\+\s*(\d+)", message)
    if plus_match:
        adults = int(plus_match.group(1))
        kids = int(plus_match.group(2))
        result["adults"] = adults
        result["kids"] = kids
        result["total"] = adults + kids
        return result

    adults_match = re.search(r"(\d+)\s*odrasl", message, re.IGNORECASE)
    kids_match = re.search(r"(\d+)\s*otrok", message, re.IGNORECASE)
    if adults_match:
        result["adults"] = int(adults_match.group(1))
    if kids_match:
        result["kids"] = int(kids_match.group(1))
    if result["adults"] is not None or result["kids"] is not None:
        result["total"] = (result["adults"] or 0) + (result["kids"] or 0)
        # Also try to extract ages from plain text "6 in 9 let" (without parentheses)
        if not result["ages"]:
            ages_plain = re.search(r"\b(\d{1,2})\s*(?:in|,)\s*(\d{1,2})\s*let\b", message, re.IGNORECASE)
            if ages_plain:
                result["ages"] = f"{ages_plain.group(1)} in {ages_plain.group(2)} let"
        return result

    cleaned = re.sub(r"\d{1,2}\.\d{1,2}\.\d{2,4}", " ", message)
    cleaned = re.sub(r"\d{1,2}:\d{2}", " ", cleaned)
    # Remove "DD. month" and "month DD" patterns so day numbers aren't counted as people
    cleaned = re.sub(
        r"\b\d{1,2}\s*(?:ga|\.)\s*(?:januar|februar|marc|april|maj|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\b",
        " ", cleaned, flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b(?:januar|februar|marc|april|maj|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\s+\d{1,2}\b",
        " ", cleaned, flags=re.IGNORECASE,
    )
    # Strip time patterns like "12h", "ob 12" so day/hour numbers aren't counted as people
    cleaned = re.sub(r"\b\d{1,2}\s*h\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bob\s+\d{1,2}\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip night count patterns so "2 noci" / "3n" / "2 noči" don't become people count
    cleaned = re.sub(r"\b\d+\s*noč\w*\b|\b\d+\s*noci\w*\b|\b\d+\s*nocit\w*\b|\b\d+n\b|\b\d+\s*nights?\b", " ", cleaned, flags=re.IGNORECASE)
    # Strip English month+day patterns so "August 12th" doesn't leave stray digit "12"
    cleaned = re.sub(
        r"\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\w*\s+\d{1,2}(?:st|nd|rd|th)?\b",
        " ", cleaned, flags=re.IGNORECASE,
    )
    cleaned = re.sub(
        r"\b\d{1,2}(?:st|nd|rd|th)?\s*(?:of\s+)?(?:january|february|march|april|may|june|july|august|september|october|november|december)\w*\b",
        " ", cleaned, flags=re.IGNORECASE,
    )

    total_match = re.search(r"(\d+)\s*(oseb|osbe)", cleaned, re.IGNORECASE)
    if total_match:
        result["total"] = int(total_match.group(1))
        return result

    digits = re.findall(r"\d+", cleaned)
    if len(digits) == 1:
        result["total"] = int(digits[0])
    elif len(digits) == 2:
        adults = int(digits[0])
        kids = int(digits[1])
        result["adults"] = adults
        result["kids"] = kids
        result["total"] = adults + kids

    return result


def parse_kids_response(message: str) -> dict[str, Optional[str | int]]:
    """
    Parsira odgovor na vprašanje o otrocih.
    Podpira formate:
    - "2 otroka, 8 in 6 let"
    - "2...8 in 6"
    - "2, stari 8 in 6"
    - "da, 2 otroka"
    - "2 (8 in 6 let)"
    - "nimam" / "ne" / "brez"
    """
    result: dict[str, Optional[str | int]] = {"kids": None, "ages": None}
    text = message.lower().strip()

    if any(w in text for w in ["ne", "nimam", "brez", "0"]):
        result["kids"] = 0
        result["ages"] = ""
        return result

    numbers = re.findall(r"\d+", message)
    if numbers:
        result["kids"] = int(numbers[0])

    ages_patterns = [
        r"(\d+)\s*(?:in|,|&)\s*(\d+)\s*let",
        r"star[ia]?\s+(\d+)\s*(?:in|,|&)?\s*(\d+)?",
        r"let[^0-9]*(\d+)",
    ]
    for pattern in ages_patterns:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            groups = [g for g in match.groups() if g]
            if groups:
                result["ages"] = " in ".join(groups) + " let"
                break

    if not result["ages"] and len(numbers) > 1:
        age_nums = numbers[1:]
        result["ages"] = " in ".join(age_nums) + " let"

    if not result["ages"]:
        dots_match = re.search(r"(\d+)\.+(\d+)", message)
        if dots_match:
            result["kids"] = int(dots_match.group(1))
            rest = message[dots_match.end():]
            rest_nums = re.findall(r"\d+", rest)
            if rest_nums:
                all_ages = [dots_match.group(2)] + rest_nums
                result["ages"] = " in ".join(all_ages) + " let"
            else:
                result["ages"] = dots_match.group(2) + " let"

    return result


def extract_nights(message: str) -> Optional[int]:
    """Ekstraktira število nočitev iz sporočila."""
    cleaned = re.sub(r"\d{1,2}\.\d{1,2}\.\d{2,4}", " ", message)
    cleaned = re.sub(r"(vikend|weekend|sobota|nedelja)", " ", cleaned, flags=re.IGNORECASE)

    # 1) številka ob besedi noč/nočitev
    match = re.search(r"(\d+)\s*(noč|noc|noči|noci|nočit|nocit|nočitev|nights?)", cleaned, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # 2) kratko sporočilo samo s številko
    stripped = cleaned.strip()
    if stripped.isdigit():
        num = int(stripped)
        if 1 <= num <= 30:
            return num

    # 3) prvo število v kratkem sporočilu (<20 znakov)
    if len(message.strip()) < 20:
        # Remove DD.MM (numeric date) patterns so date numbers aren't counted as nights
        _cl2 = re.sub(r"\b\d{1,2}[./-]\d{1,2}(?:[./-]\d{2,4})?\b", " ", cleaned)
        # Remove "DD. month" and "month DD" patterns so day numbers aren't counted as nights
        _cl2 = re.sub(
            r"\b\d{1,2}\s*(?:ga|\.)\s*(?:januar|februar|marc|april|maj|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\b",
            " ", _cl2, flags=re.IGNORECASE,
        )
        _cl2 = re.sub(
            r"\b(?:januar|februar|marc|april|maj|junij|julij|avgust|septemb|oktob|novemb|decemb)\w*\s+\d{1,2}\b",
            " ", _cl2, flags=re.IGNORECASE,
        )
        nums = re.findall(r"\d+", _cl2)
        if nums:
            num = int(nums[0])
            if 1 <= num <= 30:
                return num

    # 4) števila z besedo (eno, dve, tri, štiri ...)
    word_map = {
        "ena": 1,
        "eno": 1,
        "en": 1,
        "dve": 2,
        "dva": 2,
        "tri": 3,
        "štiri": 4,
        "stiri": 4,
        "pet": 5,
        "šest": 6,
        "sest": 6,
        "sedem": 7,
        "osem": 8,
        "devet": 9,
        "deset": 10,
    }
    for word, num in word_map.items():
        if re.search(rf"\\b{word}\\b", cleaned, re.IGNORECASE):
            return num

    return None


def extract_date(text: str) -> Optional[str]:
    """
    Vrne prvi datum v formatu d.m.yyyy / dd.mm.yyyy ali d/m/yyyy, normaliziran na DD.MM.YYYY.
    Podpira tudi 'danes', 'jutri', 'pojutri'.
    """
    today = datetime.now()
    lowered = text.lower()

    match = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", text)
    if match:
        day, month, year = match.groups()
        return f"{int(day):02d}.{int(month):02d}.{int(year):04d}"

    short_match = re.search(r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})(?!\s*[./-]\s*\d{2,4})\b", text)
    if short_match:
        day, month = short_match.groups()
        try:
            candidate = datetime(today.year, int(month), int(day))
        except ValueError:
            candidate = None
        if candidate is None:
            return None
        if candidate.date() < today.date():
            candidate = datetime(today.year + 1, int(month), int(day))
        return candidate.strftime("%d.%m.%Y")

    if "danes" in lowered:
        return today.strftime("%d.%m.%Y")
    if "jutri" in lowered:
        return (today + timedelta(days=1)).strftime("%d.%m.%Y")
    if "pojutri" in lowered:
        return (today + timedelta(days=2)).strftime("%d.%m.%Y")

    weekday_map = {
        "ponedeljek": 0,
        "torek": 1,
        "sreda": 2,
        "sredo": 2,
        "četrtek": 3,
        "cetrtek": 3,
        "petek": 4,
        "sobota": 5,
        "soboto": 5,
        "nedelja": 6,
        "nedeljo": 6,
    }

    def _next_weekday(base: datetime, target: int, include_today: bool) -> datetime:
        days_ahead = (target - base.weekday()) % 7
        if days_ahead == 0 and not include_today:
            days_ahead = 7
        return base + timedelta(days=days_ahead)

    next_match = re.search(
        r"\bnaslednj\w*\s+(ponedeljek|torek|sredo|sreda|četrtek|cetrtek|petek|soboto|sobota|nedeljo|nedelja)\b",
        lowered,
    )
    if next_match:
        day_word = next_match.group(1)
        target = weekday_map.get(day_word)
        if target is not None:
            days_ahead = (target - today.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7
            extra_week = 0 if days_ahead == 7 else 7
            candidate = today + timedelta(days=days_ahead + extra_week)
            return candidate.strftime("%d.%m.%Y")

    this_match = re.search(
        r"\b(ta|to|tej)\s+(ponedeljek|torek|sredo|sreda|četrtek|cetrtek|petek|soboto|sobota|nedeljo|nedelja)\b",
        lowered,
    )
    if this_match:
        day_word = this_match.group(2)
        target = weekday_map.get(day_word)
        if target is not None:
            candidate = _next_weekday(today, target, include_today=True)
            return candidate.strftime("%d.%m.%Y")

    return None


def extract_date_with_months(text: str) -> Optional[str]:
    """
    Like extract_date() but also recognises Slovene month-name patterns such as
    "15. avgusta", "20ga avguste", "20. marca", "1. septembra", "julij 25",
    and English patterns like "August 10th".
    Falls back to extract_date() if no month-name found.
    """
    today = datetime.now()
    lowered = text.lower().strip()

    # Month-name maps (nominative + genitive forms)
    _SL_MONTHS: dict[str, int] = {
        "januar": 1, "januarja": 1,
        "februar": 2, "februarja": 2,
        "marec": 3, "marca": 3,
        "april": 4, "aprila": 4,
        "maj": 5, "maja": 5,
        "junij": 6, "junija": 6,
        "julij": 7, "julija": 7,
        "avgust": 8, "avgusta": 8, "avguste": 8,
        "september": 9, "septembra": 9,
        "oktober": 10, "oktobra": 10,
        "november": 11, "novembra": 11,
        "december": 12, "decembra": 12,
    }
    _EN_MONTHS: dict[str, int] = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }

    def _candidate_date(day: int, month: int) -> Optional[str]:
        try:
            dt = datetime(today.year, month, day)
        except ValueError:
            return None
        if dt.date() < today.date():
            try:
                dt = datetime(today.year + 1, month, day)
            except ValueError:
                return None
        return dt.strftime("%d.%m.%Y")

    # Pattern: "15. avgusta" / "15ga avgusta" / "15 avgusta"
    for word, month in _SL_MONTHS.items():
        m = re.search(rf"\b(\d{{1,2}})\s*(?:ga|\.?)\s*{re.escape(word)}\b", lowered)
        if m:
            result = _candidate_date(int(m.group(1)), month)
            if result:
                return result
    # Pattern: "julij 25" / "julija 25"
    for word, month in _SL_MONTHS.items():
        m = re.search(rf"\b{re.escape(word)}\s+(\d{{1,2}})\b", lowered)
        if m:
            result = _candidate_date(int(m.group(1)), month)
            if result:
                return result
    # English: "August 10th" / "10 August"
    for word, month in _EN_MONTHS.items():
        m = re.search(rf"\b(\d{{1,2}})\s*(?:st|nd|rd|th)?\s*{re.escape(word)}\b", lowered)
        if m:
            result = _candidate_date(int(m.group(1)), month)
            if result:
                return result
        m2 = re.search(rf"\b{re.escape(word)}\s+(\d{{1,2}})\s*(?:st|nd|rd|th)?\b", lowered)
        if m2:
            result = _candidate_date(int(m2.group(1)), month)
            if result:
                return result

    return extract_date(text)


def extract_date_from_text(message: str) -> Optional[str]:
    return extract_date(message)


def extract_date_range(text: str) -> Optional[tuple[str, str]]:
    """
    Vrne (start, end) datum v obliki DD.MM.YYYY, če zazna interval (npr. "23. 1. do 26. 1.").
    """
    today = datetime.now()
    match = re.search(
        r"\b(\d{1,2})\s*[./-]\s*(\d{1,2})(?:\s*[./-]\s*(\d{2,4}))?\s*\.?\s*(?:do|–|—|-|to)\s*(\d{1,2})\s*[./-]\s*(\d{1,2})(?:\s*[./-]\s*(\d{2,4}))?\b",
        text,
        re.IGNORECASE,
    )
    if not match:
        return None
    day1, month1, year1, day2, month2, year2 = match.groups()
    if year2 and not year1:
        year1 = year2
    year1_val = int(year1) if year1 else today.year
    year2_val = int(year2) if year2 else year1_val
    try:
        start_dt = datetime(year1_val, int(month1), int(day1))
        end_dt = datetime(year2_val, int(month2), int(day2))
    except ValueError:
        return None
    if end_dt <= start_dt:
        end_dt = datetime(year2_val + 1, int(month2), int(day2))
    start = start_dt.strftime("%d.%m.%Y")
    end = end_dt.strftime("%d.%m.%Y")
    return (start, end)


def nights_from_range(start: str, end: str) -> Optional[int]:
    try:
        start_dt = datetime.strptime(start, "%d.%m.%Y")
        end_dt = datetime.strptime(end, "%d.%m.%Y")
    except ValueError:
        return None
    nights = (end_dt - start_dt).days
    return nights if nights > 0 else None


def extract_time(text: str) -> Optional[str]:
    """
    Vrne prvi čas v formatu HH:MM (sprejme 13:00, 13.00, 1300, "ob 12", "12h").
    """
    match = re.search(r"\b(\d{1,2})[:](\d{2})\b", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour <= 23 and minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    # "12h" / "13h" pattern
    hm = re.search(r"\b(\d{1,2})\s*h\b", text, re.IGNORECASE)
    if hm:
        hour = int(hm.group(1))
        if hour <= 23:
            return f"{hour:02d}:00"

    # "ob 12" / "ob 13 ura" — only a bare hour, no minutes
    ob_m = re.search(r"\bob\s+(\d{1,2})(?:\s*ura)?\b", text, re.IGNORECASE)
    if ob_m:
        hour = int(ob_m.group(1))
        if hour <= 23:
            return f"{hour:02d}:00"

    for match in re.finditer(r"\b(\d{1,2})\.(\d{2})\b", text):
        tail = text[match.end():]
        if tail.lstrip().startswith(".") and re.match(r"\.\d{2,4}", tail.lstrip()):
            continue
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour <= 23 and minute <= 59:
            return f"{hour:02d}:{minute:02d}"

    match = re.search(r"\b(\d{1,2})(\d{2})\b", text)
    if match:
        hour, minute = int(match.group(1)), int(match.group(2))
        if hour <= 23 and minute <= 59:
            return f"{hour:02d}:{minute:02d}"
    return None
