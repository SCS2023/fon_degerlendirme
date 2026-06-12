# BES Fon Takip Paneli

Streamlit ile kullanıcı bazlı BES fon takip uygulaması.

## Özellikler

- Kullanıcı adı + şifre ile giriş
- Yeni kullanıcı oluşturma
- Kullanıcı bazlı favori fon listesi
- Varsayılan fonlar: AMZ, AGH, GHO, FFC, AZY, AZL, ALI, AUA
- Fon kodu ile manuel sorgulama
- Son fiyat ve dönemsel getiriler için tablo
- Grafik ekranı
- CSV indirme
- SQLite veritabanı
- 6 saatte bir otomatik veri yenileme cache mantığı

## Dosya Yapısı

```text
bes-fon-app/
├── streamlit_app.py
├── scraper.py
├── database.py
├── requirements.txt
├── README.md
├── data/
└── .streamlit/
    └── config.toml
```

## Lokal Çalıştırma

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Streamlit Cloud Deploy

1. GitHub'da yeni repo oluştur.
2. Bu proje dosyalarını repoya yükle.
3. Streamlit Cloud'da `New app` seç.
4. Repository seç.
5. Main file path alanına şunu yaz:

```text
streamlit_app.py
```

6. Deploy et.

## 6 Saatte Bir Güncelleme

Uygulamada şu satır verinin 6 saatte bir yenilenmesini sağlar:

```python
CACHE_TTL_SECONDS = 6 * 60 * 60
```

Bu şu anlama gelir:

- Aynı fon listesi 6 saat boyunca cache'ten gelir.
- 6 saat dolunca uygulama yeniden siteye bağlanır.
- Sol menüdeki `Veriyi şimdi yenile` butonu cache'i manuel temizler.

## Önemli Not

Veri kaynağı olarak `https://www.besfongetirileri.com/fon-karti/{FON_KODU}` sayfası kullanılmaktadır. Site HTML yapısı değişirse `scraper.py` içindeki veri ayrıştırma mantığını güncellemek gerekebilir.
