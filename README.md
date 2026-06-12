# BES Fon Takip - V6 Fixed Parser

Bu sürümde dönem getirileri düzeltildi.

## Ana dosya
Streamlit Cloud Main file path:

```text
streamlit_app.py
```

## Dosyalar
- streamlit_app.py
- scraper.py
- database.py
- requirements.txt
- .streamlit/config.toml

## Önemli düzeltme
Önceki sürümde scraper ilk gördüğü sayıyı fiyat zannedebiliyordu. Bu yüzden AMZ için 13.743 gibi bir getiri/değer fiyat alanına düşebiliyordu.

Bu sürümde:
- Son Fiyat sadece fiyat etiketlerinden okunur.
- Son 1 Ay Getirisi, Son 3 Ay Getirisi, Son 6 Ay Getirisi, Son 1 Yıl Getirisi ayrı ayrı okunur.
- Yüzde işareti yoksa uygulama otomatik `%` ekler.
