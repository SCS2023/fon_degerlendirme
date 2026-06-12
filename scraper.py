# BES Fon Takip Streamlit Uygulaması

Bu proje, `besfongetirileri.com/fon-karti/{FON_KODU}` sayfalarından BES fon kartı verilerini çekerek kullanıcı bazlı fon takip ekranı oluşturur.

## Özellikler

- Kullanıcı adı + şifre ile giriş
- Yeni kullanıcı oluşturma
- Kullanıcıya özel kaydedilen fon listesi
- Varsayılan fonlar: `AMZ, AGH, GHO, FFC, AZY, AZL, ALI, AUA`
- Fon sorgulama ve kayıtlı listeye ekleme
- Son fiyat, 1 ay, 3 ay, 6 ay, 1 yıl getiri tablosu
- Plotly grafik
- CSV indirme

> Not: Site HTML'inde standart olarak görünen ana getiriler 1 ay, 3 ay, 6 ay ve 1 yıl alanlarıdır. Günlük/haftalık getiri için site tarafında ayrıca erişilebilir bir tarihsel veri endpoint'i bulunursa `scraper.py` içine eklenebilir.

## Lokal kurulum

```bash
git clone https://github.com/KULLANICI_ADIN/bes-fon-app.git
cd bes-fon-app
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Mac/Linux:

```bash
source .venv/bin/activate
```

Paketleri kur:

```bash
pip install -r requirements.txt
```

Uygulamayı çalıştır:

```bash
streamlit run app.py
```

## GitHub'a yükleme

```bash
git init
git add .
git commit -m "Initial BES fund tracker app"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/bes-fon-app.git
git push -u origin main
```

## Streamlit Community Cloud'a yükleme

1. GitHub'a projeyi yükleyin.
2. Streamlit Community Cloud'da **New app** seçin.
3. Repository olarak bu projeyi seçin.
4. Main file path: `app.py`
5. Deploy edin.

## Güvenlik notu

Bu ilk sürüm basit kullanıcı yönetimi için `data/users.json` kullanır. Tek kişinin veya küçük kullanımın yeterli olduğu prototipler için uygundur. Daha profesyonel kullanım için SQLite/PostgreSQL ve Streamlit secrets ile yönetim önerilir.

## Veri kaynağı notu

Veriler ilgili fon kartı sayfalarından çekilir. Sayfa yapısı değişirse `scraper.py` dosyasındaki parsing mantığı güncellenmelidir. Uygulama yatırım tavsiyesi değildir.
