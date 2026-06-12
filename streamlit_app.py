import streamlit as st
import pandas as pd
import plotly.express as px

from scraper import get_fund_data, get_many_funds
from database import (
    init_db,
    create_user,
    verify_user,
    get_user_portfolio,
    add_fund_to_user,
    remove_fund_from_user,
)

st.set_page_config(
    page_title="BES Fon Takip",
    page_icon="📈",
    layout="wide"
)

POPULAR_FUNDS = [
    "AMZ", "AGH", "GHO", "FFC", "AZY", "AZL", "ALI", "AUA",
    "AEG", "AEL", "AEP", "AET", "AFA", "AFO", "AH5", "AH6",
    "AH8", "AH9", "AJG", "AKU", "ALR", "APT", "ATA", "ATK",
    "BPA", "BPE", "BPG", "BPH", "BPI", "BPK", "BPL", "BPN",
    "BPO", "BPP", "BPR", "BPS", "BPU", "BVT", "BVV", "BZY",
    "FBA", "FBB", "FBC", "FBD", "FBE", "FBF", "FBG", "FBH",
    "GBH", "GEH", "GHH", "GHK", "GHT", "GZH", "HEA", "HEH",
    "HHH", "HHT", "HSA", "HST", "KAT", "KHT", "KPA", "KPT",
    "MGE", "MHE", "MHK", "MHT", "MTA", "NBE", "NHE", "NHT",
    "VBA", "VBE", "VBH", "VEH", "VHT", "YBE", "YHB", "ZBE"
]

PERIOD_COLUMNS = ["Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "Yılbaşından", "1 Yıl"]


def init_session_state():
    init_db()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if "username" not in st.session_state:
        st.session_state.username = ""

    if "user_id" not in st.session_state:
        st.session_state.user_id = None


def normalize_fund_code(code: str) -> str:
    return code.strip().upper()


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
                st.success("Giriş başarılı.")
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
                if ok:
                    st.success(message + " Şimdi giriş yapabilirsin.")
                else:
                    st.error(message)


def to_numeric_percent(series):
    return (
        series.astype(str)
        .str.replace("%", "", regex=False)
        .str.replace(",", ".", regex=False)
        .str.replace("+", "", regex=False)
        .replace("", pd.NA)
        .pipe(pd.to_numeric, errors="coerce")
    )


def show_fund_dataframe(rows):
    if not rows:
        st.warning("Gösterilecek veri yok.")
        return

    df = pd.DataFrame(rows)

    ordered_columns = [
        "Fon", "Fon Adı", "Son Fiyat",
        "Günlük", "Haftalık", "1 Ay", "3 Ay", "6 Ay", "Yılbaşından", "1 Yıl",
        "Kaynak"
    ]
    existing_columns = [c for c in ordered_columns if c in df.columns]
    df = df[existing_columns]

    st.dataframe(df, use_container_width=True, hide_index=True)

    chart_periods = [
        c for c in PERIOD_COLUMNS
        if c in df.columns and df[c].astype(str).str.strip().ne("").any()
    ]

    if chart_periods:
        selected_period = st.selectbox("Grafik dönemi", chart_periods, index=len(chart_periods) - 1)
        chart_df = df.copy()
        chart_df[selected_period] = to_numeric_percent(chart_df[selected_period])

        fig = px.bar(
            chart_df.dropna(subset=[selected_period]),
            x="Fon",
            y=selected_period,
            hover_data=[c for c in ["Fon Adı", "Son Fiyat"] if c in chart_df.columns],
            title=f"{selected_period} Getiri Karşılaştırması"
        )
        st.plotly_chart(fig, use_container_width=True)


def add_current_user_fund(code):
    code = normalize_fund_code(code)
    if not code:
        st.error("Fon kodu boş olamaz.")
        return

    ok, message = add_fund_to_user(st.session_state.user_id, code)
    if ok:
        st.success(message)
    else:
        st.info(message)


def page_portfolio():
    st.subheader("👤 Benim Portföyüm")
    st.caption(f"Kullanıcı: {st.session_state.username}")

    st.markdown("### Fon Seç ve Portföye Ekle")

    col1, col2 = st.columns([2, 1])

    with col1:
        selected_fund = st.selectbox(
            "Listeden fon seç",
            options=[""] + sorted(set(POPULAR_FUNDS)),
            index=0
        )

    with col2:
        manual_fund = st.text_input("Veya fon kodu yaz", placeholder="Örn: AMZ")

    fund_to_add = normalize_fund_code(manual_fund or selected_fund)

    if st.button("Portföyüme Ekle", type="primary"):
        add_current_user_fund(fund_to_add)
        st.rerun()

    st.markdown("---")

    portfolio = get_user_portfolio(st.session_state.user_id)

    if not portfolio:
        st.info("Henüz portföyüne fon eklenmedi.")
        return

    st.markdown("### Kayıtlı Portföyüm")
    st.write(", ".join(portfolio))

    rows = get_many_funds(portfolio)
    show_fund_dataframe(rows)

    st.markdown("### Portföyden Fon Çıkar")
    remove_code = st.selectbox("Çıkarılacak fon", options=portfolio)

    if st.button("Seçili Fonu Çıkar"):
        ok, message = remove_fund_from_user(st.session_state.user_id, remove_code)
        if ok:
            st.success(message)
        else:
            st.error(message)
        st.rerun()


def page_query():
    st.subheader("🔎 Fon Sorgula")
    code = st.text_input("Fon kodu giriniz", placeholder="Örn: AMZ").upper().strip()

    col1, col2 = st.columns([1, 1])

    with col1:
        query_clicked = st.button("Sorgula", type="primary")

    with col2:
        add_clicked = st.button("Sorgula ve Portföyüme Ekle")

    if query_clicked or add_clicked:
        if not code:
            st.error("Fon kodu giriniz.")
            return

        data = get_fund_data(code)

        if not data:
            st.error("Fon verisi çekilemedi. Fon kodunu kontrol edin veya site erişimini tekrar deneyin.")
            return

        st.success(f"{code} fonu sorgulandı.")
        show_fund_dataframe([data])

        if add_clicked:
            add_current_user_fund(code)


def page_bulk():
    st.subheader("📋 Toplu Fon Ekle")
    st.caption("Birden fazla fonu virgülle yazıp kendi portföyüne ekleyebilirsin.")

    text = st.text_area("Fon kodları", placeholder="AMZ, AGH, GHO, FFC")

    if st.button("Toplu Ekle", type="primary"):
        codes = [normalize_fund_code(x) for x in text.split(",") if x.strip()]
        added = []
        existing = []

        for code in codes:
            ok, message = add_fund_to_user(st.session_state.user_id, code)
            if ok:
                added.append(code)
            else:
                existing.append(code)

        if added:
            st.success(f"Eklenen fonlar: {', '.join(added)}")
        if existing:
            st.info(f"Zaten kayıtlı olanlar: {', '.join(existing)}")


def main_app():
    st.sidebar.title("Menü")
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username}**")

    page = st.sidebar.radio(
        "Sayfa",
        ["Benim Portföyüm", "Fon Sorgula", "Toplu Fon Ekle"]
    )

    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.session_state.user_id = None
        st.rerun()

    st.title("📈 BES Fon Takip Paneli")
    st.caption("Portföyler kullanıcı bazlı SQLite veritabanına kaydedilir. Fon verileri 6 saatte bir yenilenir.")

    if page == "Benim Portföyüm":
        page_portfolio()
    elif page == "Fon Sorgula":
        page_query()
    elif page == "Toplu Fon Ekle":
        page_bulk()


init_session_state()

if not st.session_state.logged_in:
    login_register_screen()
else:
    main_app()
