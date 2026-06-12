import streamlit as st
import pandas as pd
import plotly.express as px

from scraper import get_fund_data, get_many_funds, get_price_history
from database import init_db, create_user, verify_user, get_user_portfolio, add_fund_to_user, remove_fund_from_user

st.set_page_config(page_title="BES Fon Takip", page_icon="📈", layout="wide")

POPULAR_FUNDS = ["AMZ","AGH","GHO","FFC","AZY","AZL","ALI","AUA","AEG","AEL","AEP","AET","AFA","AFO","BPA","BPE","BPG","BPH","FBA","FBB","FBC","FBD","GBH","GEH","GHH","GHK","HEA","HEH","HHH","HHT","KAT","KHT","KPA","KPT","MGE","MHE","MHK","MHT","VBA","VBE","VBH","VEH","YBE","YHB","ZBE"]
PERIOD_COLUMNS = ["Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "1 Yıl"]

def init_session_state():
    init_db()
    st.session_state.setdefault("logged_in", False)
    st.session_state.setdefault("username", "")
    st.session_state.setdefault("user_id", None)

def normalize_fund_code(code):
    return str(code).strip().upper()

def login_register_screen():
    st.title("📈 BES Fon Takip Uygulaması")
    st.caption("Kullanıcı bazlı kalıcı BES fon portföyü.")
    tab_login, tab_register = st.tabs(["Giriş Yap", "Yeni Kullanıcı Oluştur"])

    with tab_login:
        username = st.text_input("Kullanıcı adı", key="login_username")
        password = st.text_input("Şifre", type="password", key="login_password")
        if st.button("Giriş Yap", type="primary"):
            user_id = verify_user(username, password)
            if user_id:
                st.session_state.logged_in = True
                st.session_state.username = username.strip().lower()
                st.session_state.user_id = user_id
                st.rerun()
            else:
                st.error("Kullanıcı adı veya şifre hatalı.")

    with tab_register:
        new_username = st.text_input("Yeni kullanıcı adı", key="register_username")
        new_password = st.text_input("Yeni şifre", type="password", key="register_password")
        new_password_2 = st.text_input("Şifre tekrar", type="password", key="register_password_2")
        if st.button("Kullanıcı Oluştur"):
            if not new_username.strip() or not new_password.strip():
                st.error("Kullanıcı adı ve şifre boş olamaz.")
            elif new_password != new_password_2:
                st.error("Şifreler eşleşmiyor.")
            else:
                ok, message = create_user(new_username, new_password)
                st.success(message + " Şimdi giriş yapabilirsin.") if ok else st.error(message)

def to_numeric_percent(series):
    return (series.astype(str).str.replace("%", "", regex=False).str.replace(",", ".", regex=False).str.replace("+", "", regex=False).replace("", pd.NA).pipe(pd.to_numeric, errors="coerce"))

def show_fund_dataframe(rows):
    df = pd.DataFrame(rows)
    cols = ["Fon", "Fon Adı", "Son Fiyat", "Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "1 Yıl", "Kaynak"]
    df = df[[c for c in cols if c in df.columns]]
    st.dataframe(df, use_container_width=True, hide_index=True)

    chart_periods = [c for c in PERIOD_COLUMNS if c in df.columns and df[c].astype(str).str.strip().ne("").any()]
    if chart_periods:
        selected_period = st.selectbox("Grafik dönemi", chart_periods, index=len(chart_periods)-1)
        chart_df = df.copy()
        chart_df[selected_period] = to_numeric_percent(chart_df[selected_period])
        fig = px.bar(chart_df.dropna(subset=[selected_period]), x="Fon", y=selected_period, hover_data=[c for c in ["Fon Adı", "Son Fiyat"] if c in chart_df.columns], title=f"{selected_period} Getiri Karşılaştırması (%)")
        st.plotly_chart(fig, use_container_width=True)

def show_history_chart(code):
    history = get_price_history(code, days_back=45)
    if not history:
        st.info("Tarihsel fiyat serisi çekilemediği için grafik gösterilemiyor.")
        return
    hist_df = pd.DataFrame(history)
    fig = px.line(hist_df, x="Tarih", y="Fiyat", title=f"{code} Son 45 Gün Fiyat Grafiği")
    st.plotly_chart(fig, use_container_width=True)

def add_current_user_fund(code):
    code = normalize_fund_code(code)
    if not code:
        st.error("Fon kodu boş olamaz.")
        return
    ok, message = add_fund_to_user(st.session_state.user_id, code)
    st.success(message) if ok else st.info(message)

def page_portfolio():
    st.subheader("👤 Benim Portföyüm")
    col1, col2 = st.columns([2, 1])
    selected_fund = col1.selectbox("Listeden fon seç", options=[""] + sorted(set(POPULAR_FUNDS)))
    manual_fund = col2.text_input("Veya fon kodu yaz", placeholder="Örn: AMZ")
    if st.button("Portföyüme Ekle", type="primary"):
        add_current_user_fund(manual_fund or selected_fund)
        st.rerun()

    portfolio = get_user_portfolio(st.session_state.user_id)
    if not portfolio:
        st.info("Henüz portföyüne fon eklenmedi.")
        return

    st.markdown("### Kayıtlı Portföyüm")
    st.write(", ".join(portfolio))
    show_fund_dataframe(get_many_funds(portfolio))

    with st.expander("Fon fiyat grafiği göster"):
        chart_code = st.selectbox("Grafik fonu seç", options=portfolio)
        show_history_chart(chart_code)

    st.markdown("### Portföyden Fon Çıkar")
    remove_code = st.selectbox("Çıkarılacak fon", options=portfolio)
    if st.button("Seçili Fonu Çıkar"):
        ok, message = remove_fund_from_user(st.session_state.user_id, remove_code)
        st.success(message) if ok else st.error(message)
        st.rerun()

def page_query():
    st.subheader("🔎 Fon Sorgula")
    code = st.text_input("Fon kodu giriniz", placeholder="Örn: AMZ").upper().strip()
    c1, c2 = st.columns(2)
    query_clicked = c1.button("Sorgula", type="primary")
    add_clicked = c2.button("Sorgula ve Portföyüme Ekle")
    if query_clicked or add_clicked:
        if not code:
            st.error("Fon kodu giriniz.")
            return
        data = get_fund_data(code)
        if not data:
            st.error("Fon verisi çekilemedi.")
            return
        show_fund_dataframe([data])
        show_history_chart(code)
        if add_clicked:
            add_current_user_fund(code)

def page_bulk():
    st.subheader("📋 Toplu Fon Ekle")
    text = st.text_area("Fon kodları", placeholder="AMZ, AGH, GHO, FFC")
    if st.button("Toplu Ekle", type="primary"):
        for code in [normalize_fund_code(x) for x in text.split(",") if x.strip()]:
            add_fund_to_user(st.session_state.user_id, code)
        st.success("Fonlar eklendi.")
        st.rerun()

def main_app():
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username}**")
    page = st.sidebar.radio("Sayfa", ["Benim Portföyüm", "Fon Sorgula", "Toplu Fon Ekle"])
    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_id = None
        st.rerun()

    st.title("📈 BES Fon Takip Paneli")
    st.caption("Günlük/haftalık getiri tarihsel fiyat serisinden hesaplanır. Veriler 6 saatte bir yenilenir.")
    if page == "Benim Portföyüm":
        page_portfolio()
    elif page == "Fon Sorgula":
        page_query()
    else:
        page_bulk()

init_session_state()
login_register_screen() if not st.session_state.logged_in else main_app()
