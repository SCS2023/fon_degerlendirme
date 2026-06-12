import re
import sqlite3
import hashlib
import os
from pathlib import Path
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
import streamlit as st
import pandas as pd
import plotly.express as px

BES_BASE_URL = "https://www.besfongetirileri.com/fon-karti/{}"
TEFAS_URL = "https://www.tefas.gov.tr/api/DB/BindHistoryInfo"
CACHE_TTL_SECONDS = 6 * 60 * 60
DB_DIR = Path("data")
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "bes_fon_app.db"
POPULAR_FUNDS = ["AMZ","AGH","GHO","FFC","AZY","AZL","ALI","AUA","AEG","AEL","AEP","AET","AFA","AFO","BPA","BPE","BPG","BPH","FBA","FBB","FBC","FBD","GBH","GEH","GHH","GHK","HEA","HEH","HHH","HHT","KAT","KHT","KPA","KPT","MGE","MHE","MHK","MHT","VBA","VBE","VBH","VEH","YBE","YHB","ZBE"]
PERIOD_COLUMNS = ["Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "1 Yıl"]

st.set_page_config(page_title="BES Fon Takip", page_icon="📈", layout="wide")


def get_connection():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def hash_password(password):
    salt = os.environ.get("APP_PASSWORD_SALT", "bes-fon-local-salt")
    return hashlib.sha256(f"{salt}:{password}".encode("utf-8")).hexdigest()


def init_db():
    conn = get_connection(); cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS portfolios (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, fund_code TEXT NOT NULL, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, fund_code))""")
    conn.commit(); conn.close()


def create_user(username, password):
    username = username.strip().lower()
    if not username or not password:
        return False, "Kullanıcı adı ve şifre boş olamaz."
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit(); return True, "Kullanıcı oluşturuldu."
    except sqlite3.IntegrityError:
        return False, "Bu kullanıcı adı zaten var."
    finally:
        conn.close()


def verify_user(username, password):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ? AND password_hash = ?", (username.strip().lower(), hash_password(password)))
    row = cur.fetchone(); conn.close()
    return row[0] if row else None


def get_user_portfolio(user_id):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("SELECT fund_code FROM portfolios WHERE user_id = ? ORDER BY fund_code", (user_id,))
    rows = cur.fetchall(); conn.close()
    return [r[0] for r in rows]


def add_fund_to_user(user_id, fund_code):
    fund_code = fund_code.strip().upper()
    if not fund_code:
        return False, "Fon kodu boş olamaz."
    conn = get_connection(); cur = conn.cursor()
    try:
        cur.execute("INSERT INTO portfolios (user_id, fund_code) VALUES (?, ?)", (user_id, fund_code))
        conn.commit(); return True, f"{fund_code} portföyüne eklendi."
    except sqlite3.IntegrityError:
        return False, f"{fund_code} zaten portföyünde var."
    finally:
        conn.close()


def remove_fund_from_user(user_id, fund_code):
    conn = get_connection(); cur = conn.cursor()
    cur.execute("DELETE FROM portfolios WHERE user_id = ? AND fund_code = ?", (user_id, fund_code.strip().upper()))
    conn.commit(); ok = cur.rowcount > 0; conn.close()
    return (True, f"{fund_code} portföyünden çıkarıldı.") if ok else (False, "Fon bulunamadı.")


def clean(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def parse_tr_float(value):
    if value is None: return None
    s = str(value).strip().replace("%", "").replace("−", "-")
    if not s: return None
    if "," in s: s = s.replace(".", "").replace(",", ".")
    try: return float(s)
    except Exception: return None


def fmt_percent(value):
    return "" if value is None else f"{value:.2f}%".replace(".", ",")


def fmt_price(value):
    return "" if value is None else f"{value:.6f}".replace(".", ",")


def is_number_line(value):
    return bool(re.fullmatch(r"%?\s*[+\-−]?\d+(?:[.,]\d+)*(?:\s*%)?", clean(value)))


def get_lines(soup):
    lines = [clean(x) for x in soup.get_text("\n").splitlines()]
    return [x for x in lines if x]


def value_after_label(lines, labels, max_lookahead=4):
    labels_lower = [x.lower() for x in labels]
    for i, line in enumerate(lines):
        if any(label in line.lower() for label in labels_lower):
            for j in range(i + 1, min(i + 1 + max_lookahead, len(lines))):
                if is_number_line(lines[j]):
                    return lines[j].replace("%", "").strip()
    return ""


def parse_date_value(tarih):
    if not isinstance(tarih, str): return None
    short = tarih[:10]
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try: return datetime.strptime(short, fmt).date()
        except Exception: pass
    m = re.search(r"\d{10,13}", tarih)
    if m:
        ts = int(m.group(0))
        if ts > 10_000_000_000: ts = ts / 1000
        return datetime.fromtimestamp(ts).date()
    return None


def normalize_tefas_rows(payload):
    if isinstance(payload, dict):
        rows = payload.get("data") or payload.get("Data") or payload.get("value") or payload.get("Value") or payload.get("aaData") or []
    elif isinstance(payload, list): rows = payload
    else: rows = []
    normalized = []
    for row in rows:
        if not isinstance(row, dict): continue
        tarih = row.get("TARIH") or row.get("Tarih") or row.get("tarih") or row.get("date") or row.get("Date")
        fiyat = row.get("FIYAT") or row.get("FİYAT") or row.get("Fiyat") or row.get("fiyat") or row.get("PRICE") or row.get("price")
        fon_adi = row.get("FONUNVAN") or row.get("FONUNVANI") or row.get("FON_ADI") or row.get("FonUnvan") or row.get("Fon Adı") or ""
        parsed_date = parse_date_value(tarih); parsed_price = parse_tr_float(fiyat)
        if parsed_date is not None and parsed_price is not None:
            normalized.append({"Tarih": parsed_date, "Fiyat": parsed_price, "Fon Adı": clean(fon_adi)})
    normalized.sort(key=lambda x: x["Tarih"])
    return normalized


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_price_history(code, days_back=400):
    code = clean(code).upper(); end_date = datetime.today().date(); start_date = end_date - timedelta(days=days_back)
    headers = {"User-Agent":"Mozilla/5.0","Accept":"application/json, text/javascript, */*; q=0.01","Content-Type":"application/x-www-form-urlencoded; charset=UTF-8","Origin":"https://www.tefas.gov.tr","Referer":"https://www.tefas.gov.tr/TarihselVeriler.aspx","X-Requested-With":"XMLHttpRequest"}
    data = {"fontip":"EMK","fonkod":code,"bastarih":start_date.strftime("%d.%m.%Y"),"bittarih":end_date.strftime("%d.%m.%Y")}
    try:
        r = requests.post(TEFAS_URL, headers=headers, data=data, timeout=30); r.raise_for_status()
        return normalize_tefas_rows(r.json())
    except Exception:
        return []


def return_from_history(history, days):
    if not history or len(history) < 2: return None
    latest = history[-1]; target_date = latest["Tarih"] - timedelta(days=days)
    candidates = [x for x in history if x["Tarih"] <= target_date]
    if not candidates: candidates = history[:-1]
    previous = candidates[-1]
    if not previous["Fiyat"]: return None
    return (latest["Fiyat"] / previous["Fiyat"] - 1) * 100


def latest_price_from_history(history):
    return history[-1]["Fiyat"] if history else None


def fund_name_from_history(history):
    for row in reversed(history or []):
        if row.get("Fon Adı"): return row["Fon Adı"]
    return ""


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_static_card_data(code):
    code = clean(code).upper(); url = BES_BASE_URL.format(code)
    try:
        response = requests.get(url, headers={"User-Agent":"Mozilla/5.0"}, timeout=20); response.raise_for_status()
    except Exception:
        return {}
    soup = BeautifulSoup(response.text, "html.parser"); lines = get_lines(soup); result = {}
    for line in lines:
        if line.startswith(f"{code} - "):
            result["Fon Adı"] = line.replace(f"{code} - ", "").strip(); break
    result["Son Fiyat"] = value_after_label(lines, ["Son Fiyat (TL)", "Son Fiyat"])
    result["1 Ay"] = value_after_label(lines, ["Son 1 Ay Getirisi", "1 Ay Getirisi"])
    result["3 Ay"] = value_after_label(lines, ["Son 3 Ay Getirisi", "3 Ay Getirisi"])
    result["6 Ay"] = value_after_label(lines, ["Son 6 Ay Getirisi", "6 Ay Getirisi"])
    result["1 Yıl"] = value_after_label(lines, ["Son 1 Yıl Getirisi", "1 Yıl Getirisi"])
    return result


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_fund_data(code):
    code = clean(code).upper(); history = get_price_history(code, days_back=400); card = get_static_card_data(code)
    latest_price = latest_price_from_history(history); fund_name = fund_name_from_history(history) or card.get("Fon Adı", "")
    result = {"Fon":code,"Fon Adı":fund_name,"Son Fiyat":fmt_price(latest_price) or card.get("Son Fiyat", ""),"Günlük":fmt_percent(return_from_history(history,1)),"Haftalık":fmt_percent(return_from_history(history,7)),"1 Ay":fmt_percent(return_from_history(history,30)) or (card.get("1 Ay", "") + "%" if card.get("1 Ay") else ""),"3 Ay":fmt_percent(return_from_history(history,90)) or (card.get("3 Ay", "") + "%" if card.get("3 Ay") else ""),"6 Ay":fmt_percent(return_from_history(history,180)) or (card.get("6 Ay", "") + "%" if card.get("6 Ay") else ""),"1 Yıl":fmt_percent(return_from_history(history,365)) or (card.get("1 Yıl", "") + "%" if card.get("1 Yıl") else ""),"Kaynak":BES_BASE_URL.format(code)}
    if not history and not any([result["Son Fiyat"], result["1 Ay"], result["3 Ay"], result["6 Ay"], result["1 Yıl"]]): return None
    return result


@st.cache_data(ttl=CACHE_TTL_SECONDS, show_spinner=False)
def get_many_funds(funds):
    rows=[]
    for fund in funds:
        code = clean(fund).upper()
        if not code: continue
        data = get_fund_data(code)
        rows.append(data if data else {"Fon":code,"Fon Adı":"","Son Fiyat":"Veri yok","Günlük":"","Haftalık":"","1 Ay":"","3 Ay":"","6 Ay":"","1 Yıl":"","Kaynak":BES_BASE_URL.format(code)})
    return rows


def init_session_state():
    init_db(); st.session_state.setdefault("logged_in", False); st.session_state.setdefault("username", ""); st.session_state.setdefault("user_id", None)


def normalize_fund_code(code): return str(code).strip().upper()


def login_register_screen():
    st.title("📈 BES Fon Takip Uygulaması"); st.caption("Kullanıcı bazlı kalıcı BES fon portföyü.")
    tab_login, tab_register = st.tabs(["Giriş Yap", "Yeni Kullanıcı Oluştur"])
    with tab_login:
        username = st.text_input("Kullanıcı adı", key="login_username"); password = st.text_input("Şifre", type="password", key="login_password")
        if st.button("Giriş Yap", type="primary"):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.logged_in=True; st.session_state.username=username.strip().lower(); st.session_state.user_id=user_id; st.rerun()
            else: st.error("Kullanıcı adı veya şifre hatalı.")
    with tab_register:
        new_username = st.text_input("Yeni kullanıcı adı", key="register_username"); new_password = st.text_input("Yeni şifre", type="password", key="register_password"); new_password_2 = st.text_input("Şifre tekrar", type="password", key="register_password_2")
        if st.button("Kullanıcı Oluştur"):
            if not new_username.strip() or not new_password.strip(): st.error("Kullanıcı adı ve şifre boş olamaz.")
            elif new_password != new_password_2: st.error("Şifreler eşleşmiyor.")
            else:
                ok, message = create_user(new_username, new_password); st.success(message + " Şimdi giriş yapabilirsin.") if ok else st.error(message)


def to_numeric_percent(series):
    return series.astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False).str.replace("+", "", regex=False).replace("", pd.NA).pipe(pd.to_numeric, errors="coerce")


def show_fund_dataframe(rows):
    df = pd.DataFrame(rows); cols = ["Fon", "Fon Adı", "Son Fiyat", "Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Kaynak"]; df = df[[c for c in cols if c in df.columns]]
    st.dataframe(df, use_container_width=True, hide_index=True)
    chart_periods = [c for c in PERIOD_COLUMNS if c in df.columns and df[c].astype(str).str.strip().ne("").any()]
    if chart_periods:
        selected_period = st.selectbox("Grafik dönemi", chart_periods, index=len(chart_periods)-1)
        chart_df = df.copy(); chart_df[selected_period] = to_numeric_percent(chart_df[selected_period])
        fig = px.bar(chart_df.dropna(subset=[selected_period]), x="Fon", y=selected_period, hover_data=[c for c in ["Fon Adı", "Son Fiyat"] if c in chart_df.columns], title=f"{selected_period} Getiri Karşılaştırması (%)")
        st.plotly_chart(fig, use_container_width=True)


def show_history_chart(code):
    history = get_price_history(code, days_back=45)
    if not history:
        st.info("Tarihsel fiyat serisi çekilemediği için grafik gösterilemiyor."); return
    hist_df = pd.DataFrame(history); fig = px.line(hist_df, x="Tarih", y="Fiyat", title=f"{code} Son 45 Gün Fiyat Grafiği"); st.plotly_chart(fig, use_container_width=True)


def add_current_user_fund(code):
    code = normalize_fund_code(code)
    if not code: st.error("Fon kodu boş olamaz."); return
    ok, message = add_fund_to_user(st.session_state.user_id, code); st.success(message) if ok else st.info(message)


def page_portfolio():
    st.subheader("👤 Benim Portföyüm")
    col1, col2 = st.columns([2, 1]); selected_fund = col1.selectbox("Listeden fon seç", options=[""] + sorted(set(POPULAR_FUNDS))); manual_fund = col2.text_input("Veya fon kodu yaz", placeholder="Örn: AMZ")
    if st.button("Portföyüme Ekle", type="primary"):
        add_current_user_fund(manual_fund or selected_fund); st.rerun()
    portfolio = get_user_portfolio(st.session_state.user_id)
    if not portfolio: st.info("Henüz portföyüne fon eklenmedi."); return
    st.markdown("### Kayıtlı Portföyüm"); st.write(", ".join(portfolio)); show_fund_dataframe(get_many_funds(portfolio))
    with st.expander("Fon fiyat grafiği göster"):
        chart_code = st.selectbox("Grafik fonu seç", options=portfolio); show_history_chart(chart_code)
    st.markdown("### Portföyden Fon Çıkar"); remove_code = st.selectbox("Çıkarılacak fon", options=portfolio)
    if st.button("Seçili Fonu Çıkar"):
        ok, message = remove_fund_from_user(st.session_state.user_id, remove_code); st.success(message) if ok else st.error(message); st.rerun()


def page_query():
    st.subheader("🔎 Fon Sorgula"); code = st.text_input("Fon kodu giriniz", placeholder="Örn: AMZ").upper().strip(); c1, c2 = st.columns(2); query_clicked = c1.button("Sorgula", type="primary"); add_clicked = c2.button("Sorgula ve Portföyüme Ekle")
    if query_clicked or add_clicked:
        if not code: st.error("Fon kodu giriniz."); return
        data = get_fund_data(code)
        if not data: st.error("Fon verisi çekilemedi."); return
        show_fund_dataframe([data]); show_history_chart(code)
        if add_clicked: add_current_user_fund(code)


def page_bulk():
    st.subheader("📋 Toplu Fon Ekle"); text = st.text_area("Fon kodları", placeholder="AMZ, AGH, GHO, FFC")
    if st.button("Toplu Ekle", type="primary"):
        for code in [normalize_fund_code(x) for x in text.split(",") if x.strip()]: add_fund_to_user(st.session_state.user_id, code)
        st.success("Fonlar eklendi."); st.rerun()


def main_app():
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username}**"); page = st.sidebar.radio("Sayfa", ["Benim Portföyüm", "Fon Sorgula", "Toplu Fon Ekle"])
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in=False; st.session_state.username=""; st.session_state.user_id=None; st.rerun()
    st.title("📈 BES Fon Takip Paneli"); st.caption("Günlük/haftalık getiri tarihsel fiyat serisinden hesaplanır. Veriler 6 saatte bir yenilenir.")
    if page == "Benim Portföyüm": page_portfolio()
    elif page == "Fon Sorgula": page_query()
    else: page_bulk()


init_session_state()
login_register_screen() if not st.session_state.logged_in else main_app()
