# ZB MUSIC Bot 🎵

Telegram müzik botu - YouTube'dan MP3 indirme ve dönüştürme botu.

## Özellikler

- YouTube'dan MP3 indirme
- 320kbps ses kalitesi
- Webhook desteği
- Flask tabanlı sunucu
- Otomatik geçici dosya temizleme

## Kurulum

1. Gerekli bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

2. Çevre değişkenlerini ayarlayın:
```bash
export BOT_TOKEN="your_bot_token_here"
export WEBHOOK_HOST="https://your-app.herokuapp.com"
```

3. Botu çalıştırın:
```bash
python reis_bot.py
```

## Komutlar

- `/start` - Botu başlat
- `/getid` - Chat ID öğren
- `/status` - Bot durumu
- Şarkı ismi gönder - MP3 indir

## Deploy

### Heroku
1. Bu repository'i fork edin
2. Heroku'da yeni app oluşturun
3. Environment variables ayarlayın
4. Deploy edin

### Railway
1. Repository'i bağlayın
2. Environment variables ayarlayın
3. Otomatik deploy

## Environment Variables

- `BOT_TOKEN`: Telegram bot token
- `WEBHOOK_HOST`: Deployment URL
- `PORT`: Sunucu portu (varsayılan: 5000)
