import re
import requests
from bs4 import BeautifulSoup
import streamlit as st

BASE_URL = "https://www.besfongetirileri.com/fon-karti/{}"
CACHE_TTL_SECONDS = 6 * 60 * 60


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_number(value, percent=False):
    value = clean_text(value)
    if not value:
        return ""
    value = value.replace("−", "-")
    value = value.replace(".", ",")
    if percent and not value.endswith("%"):
        value += "%"
    return value


def extract_after_label(text, labels, percent=False):
    # Etiketten sonra gelen ilk sayıyı yakalar.
    # Örn: "Son 1 Ay Getirisi -10.57" => -10,57%
    for label in labels:
        pattern = rf"{label}\s*[:\-]?\s*([+\-−]?\d+(?:[,.]\d+)?)"
        m = re.search(pattern, text, flags=re.IGNORECASE)
        if m:
            return normalize_number(m.group(1), percent=percent)
    return ""


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_fund_data(code):
    code = clean_text(code).upper()
    url = BASE_URL.format(code)

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)
        r.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(r.text, "html.parser")
    text = clean_text(soup.get_text(" "))

    result = {
        "Fon": code,
        "Fon Adı": "",
        "Son Fiyat": "",
        "Günlük": "",
        "Haftalık": "",
        "1 Ay": "",
        "3 Ay": "",
        "6 Ay": "",
        "Yılbaşından": "",
        "1 Yıl": "",
        "Kaynak": url
    }

    title = soup.find("h1") or soup.find("h2")
    if title:
        result["Fon Adı"] = clean_text(title.get_text(" "))

    # ÖNEMLİ:
    # Son fiyat için rastgele ilk sayı alınmıyor.
    # Bu yüzden 13.743 gibi getiri/değer rakamları fiyat sütununa düşmez.
    result["Son Fiyat"] = extract_after_label(
        text,
        [
            r"Son Fiyat",
            r"Fon Fiyatı",
            r"Birim Pay Değeri",
            r"Pay Değeri",
            r"Fiyat"
        ],
        percent=False
    )

    result["Günlük"] = extract_after_label(
        text,
        [r"Günlük Getiri", r"Son 1 Gün Getirisi", r"1 Gün Getirisi", r"Günlük"],
        percent=True
    )

    result["Haftalık"] = extract_after_label(
        text,
        [r"Haftalık Getiri", r"Son 1 Hafta Getirisi", r"1 Hafta Getirisi", r"Haftalık"],
        percent=True
    )

    result["1 Ay"] = extract_after_label(
        text,
        [r"Son 1 Ay Getirisi", r"1 Ay Getirisi", r"Aylık Getiri", r"1 Ay"],
        percent=True
    )

    result["3 Ay"] = extract_after_label(
        text,
        [r"Son 3 Ay Getirisi", r"3 Ay Getirisi", r"3 Ay"],
        percent=True
    )

    result["6 Ay"] = extract_after_label(
        text,
        [r"Son 6 Ay Getirisi", r"6 Ay Getirisi", r"6 Ay"],
        percent=True
    )

    result["Yılbaşından"] = extract_after_label(
        text,
        [r"Yılbaşından Bugüne Getiri", r"Yılbaşından", r"Yılbaşı Getirisi", r"YTD"],
        percent=True
    )

    result["1 Yıl"] = extract_after_label(
        text,
        [r"Son 1 Yıl Getirisi", r"1 Yıl Getirisi", r"Yıllık Getiri", r"1 Yıl"],
        percent=True
    )

    # Bazı sayfalarda fiyat etiketi farklı olabilir. Fiyat boşsa, sadece çok ondalıklı küçük değeri arar.
    # Getiri gibi 13.743 değerini almamak için bu fallback 0 ile başlayan fiyatlara öncelik verir.
    if not result["Son Fiyat"]:
        price_candidates = re.findall(r"\b0[,.]\d{4,}\b", text)
        if price_candidates:
            result["Son Fiyat"] = normalize_number(price_candidates[0], percent=False)

    return result


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_many_funds(funds):
    rows = []
    for fund in funds:
        code = clean_text(fund).upper()
        if not code:
            continue
        data = get_fund_data(code)
        rows.append(data if data else {
            "Fon": code,
            "Fon Adı": "",
            "Son Fiyat": "Veri yok",
            "Günlük": "",
            "Haftalık": "",
            "1 Ay": "",
            "3 Ay": "",
            "6 Ay": "",
            "Yılbaşından": "",
            "1 Yıl": "",
            "Kaynak": BASE_URL.format(code)
        })
    return rows
