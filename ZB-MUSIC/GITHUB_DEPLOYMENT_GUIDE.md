# 🚀 GitHub Deployment Rehberi

Bu rehber, ZB MUSIC botunu GitHub'a yükleyip Render/Heroku gibi platformlarda deploy etmek için adımları içerir.

## 📋 Ön Gereksinimler

- GitHub hesabı
- Telegram Bot Token
- Render/Heroku hesabı (opsiyonel)

## 🔧 Adım 1: GitHub Repository Oluşturma

1. GitHub'da giriş yapın
2. Sağ üstteki "+" butonuna tıklayıp "New repository" seçin
3. Repository bilgilerini girin:
   - Repository name: `ZB-MUSIC`
   - Description: `Telegram Music Downloader Bot`
   - Public/Private: Tercihinize göre
   - Initialize with README: İşaretleyin
4. "Create repository" butonuna tıklayın

## 📤 Adım 2: Projeyi GitHub'a Yükleme

### Yöntem 1: GitHub Desktop ile
1. GitHub Desktop uygulamasını açın
2. File > Clone repository
3. URL sekmesine repository URL'sini yapıştırın
4. Local path olarak ZB MUSIC klasörünü seçin
5. Commit message yazıp "Commit to main" butonuna tıklayın
6. "Push origin" butonuna tıklayın

### Yöntem 2: Komut Satırı ile
```bash
cd ZB-MUSIC
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/kullanici-adiniz/ZB-MUSIC.git
git push -u origin main
```

## 🌐 Adım 3: Render'da Deployment

### Render Kurulumu
1. [Render](https://render.com) sitesine gidin
2. GitHub hesabınızla giriş yapın
3. "New +" butonuna tıklayıp "Web Service" seçin

### Repository Bağlama
1. "Connect GitHub account" butonuna tıklayın
2. ZB-MUSIC repository'sini seçin
3. "Connect" butonuna tıklayın

### Ayarları Yapılandırma
1. **Name**: `zb-music-bot` (veya tercih ettiğiniz isim)
2. **Environment**: `Python 3`
3. **Region**: `Frankfurt` (EU) veya size yakın bölge
4. **Branch**: `main`
5. **Root Directory**: (boş bırakın)
6. **Build Command**: `pip install -r requirements.txt`
7. **Start Command**: `python reis_bot.py --webhook`

### Ortam Değişkenleri
1. "Advanced" butonuna tıklayın
2. "Add Environment Variable" butonuna tıklayın
3. Aşağıdaki değişkenleri ekleyin:

| Key | Value |
|-----|-------|
| `BOT_TOKEN` | `8182908384:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY` |
| `PORT` | `10000` |

### Deployment
1. "Create Web Service" butonuna tıklayın
2. Deployment işleminin tamamlanmasını bekleyin

## 🔍 Adım 4: Webhook Ayarları

Deployment tamamlandıktan sonra:

1. Render dashboard'da web service'i açın
2. "Settings" sekmesine gidin
3. "URL" kısmındaki adresi kopyalayın
4. Bot kodundaki `WEBHOOK_HOST` değişkenini bu URL ile güncelleyin

## ✅ Adım 5: Test Etme

1. Telegram'da botunuza mesaj gönderin
2. Render logs kısmından hata kontrolü yapın
3. Her şey çalışıyorsa deployment başarılı!

## 🐛 Sorun Giderme

### Common Issues:
1. **Import errors**: requirements.txt'deki paketlerin yüklendiğinden emin olun
2. **403 Errors**: YouTube erişim sorunları için bekleyin veya IP değiştirin
3. **Webhook errors**: URL'nin doğru olduğundan emin olun

### Log Kontrolü:
- Render dashboard > Web Service > Logs
- Hata mesajlarını buradan takip edin

## 📞 Destek

Sorun yaşarsanız:
1. Render logs'unu kontrol edin
2. GitHub issues'da sorun bildirin
3. Telegram: @kullanici_adiniz

---

**Not**: Bu bot educational purposes içindir. YouTube'un terms of service'ine uygun kullanın.
