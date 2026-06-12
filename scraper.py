import re
import requests
from bs4 import BeautifulSoup
import streamlit as st

BASE_URL = "https://www.besfongetirileri.com/fon-karti/{}"
CACHE_TTL_SECONDS = 6 * 60 * 60


def clean_text(value):
    if value is None:
        return ""
    return re.sub(r"\s+", " ", value).strip()


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_fund_data(code):
    code = code.upper().strip()
    url = BASE_URL.format(code)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
    except Exception:
        return None

    soup = BeautifulSoup(response.text, "html.parser")
    text = clean_text(soup.get_text(" "))

    result = {
        "Fon": code,
        "Son Fiyat": "",
        "1 Ay": "",
        "3 Ay": "",
        "6 Ay": "",
        "1 Yıl": "",
        "Kaynak": url
    }

    # Sayfadaki metin yapısı zamanla değişebileceği için esnek regex kullanıyoruz.
    patterns = {
        "Son Fiyat": r"(?:Son Fiyat|Fon Fiyatı|Fiyat)\s*[:\-]?\s*([0-9]+[,.][0-9]+)",
        "1 Ay": r"(?:1 Ay|Son 1 Ay)\s*[:\-]?\s*([+\-]?[0-9]+[,.][0-9]+\s*%)",
        "3 Ay": r"(?:3 Ay|Son 3 Ay)\s*[:\-]?\s*([+\-]?[0-9]+[,.][0-9]+\s*%)",
        "6 Ay": r"(?:6 Ay|Son 6 Ay)\s*[:\-]?\s*([+\-]?[0-9]+[,.][0-9]+\s*%)",
        "1 Yıl": r"(?:1 Yıl|Son 1 Yıl|Yıllık)\s*[:\-]?\s*([+\-]?[0-9]+[,.][0-9]+\s*%)",
    }

    for key, pattern in patterns.items():
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match:
            result[key] = clean_text(match.group(1))

    # Alternatif yöntem: yüzde değerlerini sırayla yakala.
    # Site tasarımı değişirse en azından getiri sütunları boş kalmasın.
    percentages = re.findall(r"[+\-]?[0-9]+[,.][0-9]+\s*%", text)
    if percentages:
        for key, idx in [("1 Ay", 0), ("3 Ay", 1), ("6 Ay", 2), ("1 Yıl", 3)]:
            if not result[key] and len(percentages) > idx:
                result[key] = percentages[idx]

    if not any(result[x] for x in ["Son Fiyat", "1 Ay", "3 Ay", "6 Ay", "1 Yıl"]):
        return None

    return result


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_many_funds(funds):
    rows = []
    for fund in funds:
        data = get_fund_data(fund)
        if data:
            rows.append(data)
        else:
            rows.append({
                "Fon": fund,
                "Son Fiyat": "Veri yok",
                "1 Ay": "",
                "3 Ay": "",
                "6 Ay": "",
                "1 Yıl": "",
                "Kaynak": BASE_URL.format(fund)
            })
    return rows
