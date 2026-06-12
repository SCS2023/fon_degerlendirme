# BES Fon Takip - V8 TEFAS Tarihsel Veri

## Ana dosya

Streamlit Cloud Main file path:

```text
streamlit_app.py
```

## Bu sürümdeki ana düzeltme

Günlük ve haftalık getiriler artık fon kartı HTML'inden beklenmez.

Bunlar TEFAS tarihsel fiyat serisinden hesaplanır:

- Günlük getiri = son fiyat / önceki işlem günü fiyatı - 1
- Haftalık getiri = son fiyat / yaklaşık 7 gün önceki fiyat - 1
- 1 Ay = son fiyat / yaklaşık 30 gün önceki fiyat - 1
- 3 Ay = son fiyat / yaklaşık 90 gün önceki fiyat - 1
- 6 Ay = son fiyat / yaklaşık 180 gün önceki fiyat - 1
- 1 Yıl = son fiyat / yaklaşık 365 gün önceki fiyat - 1

## Dosyalar

```text
streamlit_app.py
scraper.py
database.py
requirements.txt
README.md
.streamlit/config.toml
data/.gitkeep
```

## requirements.txt

```text
streamlit
requests
beautifulsoup4
pandas
plotly
```

## Not

TEFAS endpoint geçici olarak cevap vermezse uygulama BES Fon Getirileri kartındaki statik 1 Ay, 3 Ay, 6 Ay, 1 Yıl verilerine döner.
