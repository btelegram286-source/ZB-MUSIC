m s# 🎵 ZB MUSIC Bot

Telegram üzerinden YouTube'dan müzik indirebilen ve MP3 formatında gönderebilen bir Telegram botu.

## ✨ Özellikler

- YouTube'dan müzik arama ve indirme
- Otomatik MP3 formatına dönüştürme
- Yüksek kaliteli ses (320kbps)
- Webhook ve polling modu desteği
- Flask tabanlı web arayüzü

## 🚀 Kurulum

### Gereksinimler

- Python 3.8+
- FFmpeg
- Telegram Bot Token

### Yerel Kurulum

1. Depoyu klonlayın:
```bash
git clone https://github.com/kullanici-adiniz/ZB-MUSIC.git
cd ZB-MUSIC
```

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

3. FFmpeg'i kurun:
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows: https://ffmpeg.org/download.html adresinden indirin
```

4. Ortam değişkenlerini ayarlayın:
```bash
export BOT_TOKEN="bot_tokeniniz_buraya"
```

5. Botu çalıştırın:
```bash
python reis_bot.py
```

### Render Üzerinde Deployment

1. [Render](https://render.com) hesabı oluşturun
2. Yeni bir Web Service oluşturun
3. GitHub reposunu bağlayın
4. Ortam değişkenlerini ayarlayın:
   - `BOT_TOKEN`: Telegram bot tokenınız

5. Deploy edin!

### Bot Token Alma

1. [@BotFather](https://t.me/BotFather) ile iletişime geçin
2. `/newbot` komutunu kullanın
3. Bot ismi ve kullanıcı adı belirleyin
4. Size verilen token'ı kullanın

## 📝 Kullanım

1. Botu başlatmak için: `/start`
2. Chat ID öğrenmek için: `/getid`
3. Müzik indirmek için: şarkı ismi veya sanatçı adı yazın

## ⚠️ Güvenlik Notları

- **ÖNEMLİ**: Bot token'ını asla public repolarda paylaşmayın!
- Ortam değişkenlerini kullanın
- `cookies.txt` dosyasını .gitignore'a ekledim

## 🛠️ Teknik Detaylar

- **Python**: 3.8+
- **Telegram Bot API**: pyTelegramBotAPI
- **Video İndirme**: yt-dlp
- **Audio Conversion**: FFmpeg
- **Web Framework**: Flask

## 📄 Lisans

Bu proje MIT lisansı altında lisanslanmıştır.

## 🤝 Katkıda Bulunma

1. Fork edin
2. Feature branch oluşturun (`git checkout -b feature/yeni-ozellik`)
3. Commit edin (`git commit -m 'Yeni özellik eklendi'`)
4. Push edin (`git push origin feature/yeni-ozellik`)
5. Pull Request oluşturun

## 📞 İletişim

Proje ile ilgili sorularınız için issue açabilirsiniz.
