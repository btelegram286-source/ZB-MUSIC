# ZB MUSIC Bot - Render Deployment Guide

## 🚀 Render'a Deploy Adımları

### 1. GitHub Repository Hazırlığı
- Bu kodu GitHub'a push edin
- Repository public veya private olabilir

### 2. Render'da Yeni Web Service Oluştur
1. [Render Dashboard](https://dashboard.render.com/)'a gidin
2. "New +" → "Web Service" seçin
3. GitHub repository'nizi bağlayın

### 3. Environment Variables Ayarları
Render dashboard'da aşağıdaki environment variables'ları ayarlayın:

**GEREKLİ AYARLAR:**
- `BOT_TOKEN`: Telegram bot token'iniz (örnek: `123456789:AAF9Utjvkgo9F4Nw8MoZbvSXJ-Y_dUXEuVY`)

**OTOMATIK AYARLANAN:**
- `WEBHOOK_HOST`: Render otomatik olarak ayarlayacak
- `PORT`: Render otomatik olarak ayarlayacak

### 4. Build Settings
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python reis_bot.py`

### 5. Plan Seçimi
- Free plan yeterli (Web Service)

### 6. Deploy
- Deploy butonuna tıklayın
- Build işlemi tamamlandıktan sonra bot otomatik çalışacak

## ✅ Deploy Sonrası Kontroller

1. **Webhook Kontrolü**: 
   - Render URL'sini açın (örnek: `https://zb-music-bot.onrender.com`)
   - "🎵 ZB MUSIC Bot Webhook Server - Çalışıyor!" mesajını görmelisiniz

2. **Ping Testi**:
   - `https://zb-music-bot.onrender.com/ping` adresine gidin
   - "pong" cevabı almalısınız

3. **Telegram Bot Testi**:
   - Botunuza `/start` gönderin
   - "🎶 Selam reis! Şarkı ismini gönder, sana MP3 olarak araç formatında yollayayım." mesajı gelmeli

## 🔧 Sorun Giderme

### Bot Çalışmıyorsa:
1. Logları kontrol edin (Render Dashboard → Logs)
2. Environment variables doğru ayarlandı mı?
3. BOT_TOKEN geçerli mi?

### Webhook Ayarlanmamışsa:
1. Manual olarak webhook ayarlayın:
```bash
curl "https://api.telegram.org/bot<BOT_TOKEN>/setWebhook?url=https://your-app.onrender.com/<BOT_TOKEN>"
```

### Build Hatası:
1. Requirements.txt'deki paketler uyumlu mu?
2. Python versiyonu uygun mu? (3.8+)

## 📞 Destek
Sorun olursa Render logs'una bakın veya Telegram Bot Father'dan token kontrol edin.
