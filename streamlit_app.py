import streamlit as st
import pandas as pd
import plotly.express as px

from scraper import get_fund_data, get_many_funds

DEFAULT_FUNDS = ["AMZ", "AGH", "GHO", "FFC", "AZY", "AZL", "ALI", "AUA"]

st.set_page_config(
    page_title="BES Fon Takip",
    page_icon="📈",
    layout="wide"
)

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "favorite_funds" not in st.session_state:
    st.session_state.favorite_funds = DEFAULT_FUNDS.copy()


def login_screen():
    st.title("📈 BES Fon Takip Uygulaması")
    st.caption("Türkiye BES fonlarını takip etmek için basit Streamlit paneli.")

    username = st.text_input("Kullanıcı adı")
    password = st.text_input("Şifre", type="password")

    if st.button("Giriş Yap"):
        if username.strip() and password.strip():
            st.session_state.logged_in = True
            st.session_state.username = username.strip()
            st.success("Giriş başarılı.")
            st.rerun()
        else:
            st.error("Kullanıcı adı ve şifre giriniz.")


def fund_table(funds):
    with st.spinner("Fon verileri çekiliyor..."):
        data = get_many_funds(funds)

    if not data:
        st.warning("Veri çekilemedi. Fon kodlarını veya site erişimini kontrol edin.")
        return

    df = pd.DataFrame(data)

    st.subheader("Kayıtlı Fonlarım")
    st.dataframe(df, use_container_width=True)

    numeric_columns = ["1 Ay", "3 Ay", "6 Ay", "1 Yıl"]
    chart_df = df.copy()

    for col in numeric_columns:
        if col in chart_df.columns:
            chart_df[col] = (
                chart_df[col]
                .astype(str)
                .str.replace("%", "", regex=False)
                .str.replace(",", ".", regex=False)
            )
            chart_df[col] = pd.to_numeric(chart_df[col], errors="coerce")

    selected_period = st.selectbox(
        "Grafik dönemi",
        ["1 Ay", "3 Ay", "6 Ay", "1 Yıl"],
        index=3
    )

    if selected_period in chart_df.columns:
        fig = px.bar(
            chart_df,
            x="Fon",
            y=selected_period,
            title=f"{selected_period} Getiri Karşılaştırması"
        )
        st.plotly_chart(fig, use_container_width=True)


def main_app():
    st.sidebar.title("Menü")
    st.sidebar.write(f"Kullanıcı: **{st.session_state.username}**")

    if st.sidebar.button("Çıkış Yap"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    page = st.sidebar.radio(
        "Sayfa",
        ["Fonlarım", "Fon Sorgula", "Favori Fon Yönetimi"]
    )

    st.title("📈 BES Fon Takip Paneli")
    st.caption("Veriler 6 saat cache ile yenilenir.")

    if page == "Fonlarım":
        fund_table(st.session_state.favorite_funds)

    elif page == "Fon Sorgula":
        code = st.text_input("Fon kodu giriniz", placeholder="Örn: AMZ").upper().strip()

        if st.button("Sorgula"):
            if not code:
                st.error("Fon kodu giriniz.")
            else:
                data = get_fund_data(code)
                if data:
                    st.success(f"{code} fonu bulundu.")
                    st.dataframe(pd.DataFrame([data]), use_container_width=True)
                else:
                    st.error("Fon verisi çekilemedi.")

    elif page == "Favori Fon Yönetimi":
        st.subheader("Favori Fonlar")

        current = ", ".join(st.session_state.favorite_funds)
        funds_text = st.text_area(
            "Fon kodlarını virgülle yaz",
            value=current,
            help="Örnek: AMZ, AGH, GHO, FFC, AZY, AZL, ALI, AUA"
        )

        if st.button("Kaydet"):
            funds = [
                x.strip().upper()
                for x in funds_text.split(",")
                if x.strip()
            ]
            if funds:
                st.session_state.favorite_funds = funds
                st.success("Favori fonlar güncellendi.")
                st.rerun()
            else:
                st.error("En az bir fon kodu yazmalısınız.")


if not st.session_state.logged_in:
    login_screen()
else:
    main_app()
