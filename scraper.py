import re
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import streamlit as st

BES_BASE_URL = "https://www.besfongetirileri.com/fon-karti/{}"
TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
CACHE_TTL_SECONDS = 6 * 60 * 60

def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()

def parse_tr_float(value):
    if value is None:
        return None
    s = str(value).strip().replace("%", "").replace("−", "-")
    if not s:
        return None
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return None

def fmt_percent(value):
    return "" if value is None else f"{value:.2f}%".replace(".", ",")

def fmt_price(value):
    return "" if value is None else f"{value:.6f}".replace(".", ",")

def get_lines(soup):
    lines = [clean(x) for x in soup.get_text("\n").splitlines()]
    return [x for x in lines if x]

def is_number_line(value):
    return bool(re.fullmatch(r"%?\s*[+\-−]?\d+(?:[.,]\d+)*(?:\s*%)?", clean(value)))

def value_after_label(lines, labels, max_lookahead=4):
    labels_lower = [x.lower() for x in labels]
    for i, line in enumerate(lines):
        if any(label in line.lower() for label in labels_lower):
            for j in range(i + 1, min(i + 1 + max_lookahead, len(lines))):
                if is_number_line(lines[j]):
                    return lines[j].replace("%", "").strip()
    return ""

def parse_date_value(tarih):
    if not isinstance(tarih, str):
        return None
    short = tarih[:10]
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(short, fmt).date()
        except Exception:
            pass
    m = re.search(r"\d{10,13}", tarih)
    if m:
        ts = int(m.group(0))
        if ts > 10000000000:
            ts = ts / 1000
        return datetime.fromtimestamp(ts).date()
    return None

def normalize_tefas_rows(payload):
    if isinstance(payload, dict):
        rows = payload.get("data") or payload.get("Data") or payload.get("value") or payload.get("Value") or payload.get("aaData") or []
    elif isinstance(payload, list):
        rows = payload
    else:
        rows = []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        tarih = row.get("TARIH") or row.get("Tarih") or row.get("tarih") or row.get("date") or row.get("Date")
        fiyat = row.get("FIYAT") or row.get("FİYAT") or row.get("Fiyat") or row.get("fiyat") or row.get("PRICE") or row.get("price")
        fon_adi = row.get("FONUNVAN") or row.get("FONUNVANI") or row.get("FON_ADI") or row.get("FonUnvan") or row.get("Fon Adı") or ""
        parsed_date = parse_date_value(tarih)
        parsed_price = parse_tr_float(fiyat)
        if parsed_date is not None and parsed_price is not None:
            normalized.append({"Tarih": parsed_date, "Fiyat": parsed_price, "Fon Adı": clean(fon_adi)})
    normalized.sort(key=lambda x: x["Tarih"])
    return normalized

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_price_history(code, days_back=400):
    code = clean(code).upper()
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=days_back)
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://www.tefas.gov.tr",
        "Referer": "https://www.tefas.gov.tr/TarihselVeriler.aspx",
        "X-Requested-With": "XMLHttpRequest",
    }
    data = {
        "fontip": "EMK",
        "fonkod": code,
        "bastarih": start_date.strftime("%d.%m.%Y"),
        "bittarih": end_date.strftime("%d.%m.%Y"),
    }
    try:
        r = requests.post(TEFAS_URL, headers=headers, data=data, timeout=30)
        r.raise_for_status()
        return normalize_tefas_rows(r.json())
    except Exception:
        return []

def return_from_history(history, days):
    if not history or len(history) < 2:
        return None
    latest = history[-1]
    target_date = latest["Tarih"] - timedelta(days=days)
    candidates = [x for x in history if x["Tarih"] <= target_date]
    if not candidates:
        candidates = history[:-1]
    previous = candidates[-1]
    if not previous["Fiyat"]:
        return None
    return (latest["Fiyat"] / previous["Fiyat"] - 1) * 100

def latest_price_from_history(history):
    return history[-1]["Fiyat"] if history else None

def fund_name_from_history(history):
    for row in reversed(history or []):
        if row.get("Fon Adı"):
            return row["Fon Adı"]
    return ""

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_static_card_data(code):
    code = clean(code).upper()
    url = BES_BASE_URL.format(code)
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
        response.raise_for_status()
    except Exception:
        return {}
    soup = BeautifulSoup(response.text, "html.parser")
    lines = get_lines(soup)
    result = {}
    for line in lines:
        if line.startswith(f"{code} - "):
            result["Fon Adı"] = line.replace(f"{code} - ", "").strip()
            break
    result["Son Fiyat"] = value_after_label(lines, ["Son Fiyat (TL)", "Son Fiyat"])
    result["1 Ay"] = value_after_label(lines, ["Son 1 Ay Getirisi", "1 Ay Getirisi"])
    result["3 Ay"] = value_after_label(lines, ["Son 3 Ay Getirisi", "3 Ay Getirisi"])
    result["6 Ay"] = value_after_label(lines, ["Son 6 Ay Getirisi", "6 Ay Getirisi"])
    result["1 Yıl"] = value_after_label(lines, ["Son 1 Yıl Getirisi", "1 Yıl Getirisi"])
    return result

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_fund_data(code):
    code = clean(code).upper()
    history = get_price_history(code, days_back=400)
    card = get_static_card_data(code)
    latest_price = latest_price_from_history(history)
    fund_name = fund_name_from_history(history) or card.get("Fon Adı", "")
    result = {
        "Fon": code,
        "Fon Adı": fund_name,
        "Son Fiyat": fmt_price(latest_price) or card.get("Son Fiyat", ""),
        "Günlük": fmt_percent(return_from_history(history, 1)),
        "Haftalık": fmt_percent(return_from_history(history, 7)),
        "1 Ay": fmt_percent(return_from_history(history, 30)) or (card.get("1 Ay", "") + "%" if card.get("1 Ay") else ""),
        "3 Ay": fmt_percent(return_from_history(history, 90)) or (card.get("3 Ay", "") + "%" if card.get("3 Ay") else ""),
        "6 Ay": fmt_percent(return_from_history(history, 180)) or (card.get("6 Ay", "") + "%" if card.get("6 Ay") else ""),
        "1 Yıl": fmt_percent(return_from_history(history, 365)) or (card.get("1 Yıl", "") + "%" if card.get("1 Yıl") else ""),
        "Kaynak": BES_BASE_URL.format(code),
    }
    if not history and not any([result["Son Fiyat"], result["1 Ay"], result["3 Ay"], result["6 Ay"], result["1 Yıl"]]):
        return None
    return result

@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_many_funds(funds):
    rows = []
    for fund in funds:
        code = clean(fund).upper()
        if not code:
            continue
        data = get_fund_data(code)
        rows.append(data if data else {
            "Fon": code, "Fon Adı": "", "Son Fiyat": "Veri yok",
            "Günlük": "", "Haftalık": "", "1 Ay": "", "3 Ay": "", "6 Ay": "", "1 Yıl": "",
            "Kaynak": BES_BASE_URL.format(code)
        })
    return rows
