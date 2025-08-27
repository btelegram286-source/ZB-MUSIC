# 🎵 ZB MUSIC Bot v1.1

Telegram üzerinden müzik indirme botu. Kullanıcılar şarkı ismi gönderir, bot YouTube'dan MP3 formatında indirip gönderir.

**Güncelleme:** yt-dlp sürüm hatası düzeltildi.

## Özellikler

- 🤖 Telegram bot entegrasyonu
- 🎶 YouTube'dan müzik indirme
- 🔊 MP3 formatında dönüşüm
- 🌐 Webhook ve polling modu desteği
- 🚀 Render/Heroku deployment hazır

## Kurulum

### Gereksinimler

- Python 3.8+
- Telegram Bot Token
- FFmpeg

### Yerel Kurulum

1. Depoyu klonlayın:
```bash
git clone <repository-url>
cd ZB-MUSIC
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. Ortam değişkenlerini ayarlayın:
```bash
export BOT_TOKEN="your_bot_token_here"
```

4. Botu çalıştırın:
```bash
python reis_bot.py
```

### Render Deployment

1. Render hesabına giriş yapın
2. Yeni Web Service oluşturun
3. GitHub reposunu bağlayın
4. Ortam değişkenlerini ayarlayın:
   - `BOT_TOKEN`: Telegram bot token
5. Deploy edin

## Ortam Değişkenleri

| Değişken | Açıklama | Gerekli |
|----------|----------|---------|
| `BOT_TOKEN` | Telegram bot token | Evet |
| `WEBHOOK_HOST` | Webhook URL (Render için) | Hayır |
| `PORT` | Port numarası | Hayır |

## Kullanım

1. Telegram'da botu bulun
2. `/start` komutuyla başlayın
3. Şarkı ismini gönderin
4. Bot MP3'ü indirip gönderecek

## Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/amazing-feature`)
3. Commit edin (`git commit -m 'Add amazing feature'`)
4. Push edin (`git push origin feature/amazing-feature`)
5. Pull Request oluşturun

## Lisans

Bu proje MIT lisansı altında lisanslanmıştır.
