# BES Fon Takip Streamlit Uygulaması

## Streamlit Cloud Ayarı

Main file path:

```text
streamlit_app.py
```

## requirements.txt

```text
streamlit
requests
beautifulsoup4
pandas
plotly
```

## 6 Saat Güncelleme

`scraper.py` içinde:

```python
CACHE_TTL_SECONDS = 6 * 60 * 60
```

Bu ayar Streamlit cache verisini 6 saatte bir yeniler.

## Varsayılan Fonlar

AMZ, AGH, GHO, FFC, AZY, AZL, ALI, AUA
