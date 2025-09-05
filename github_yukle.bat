@echo off
echo 🚀 ZB MUSIC Bot GitHub'a Yükleniyor...
echo.

cd /d "%~dp0"

echo 1. Git init...
git init

echo 2. Dosyalar ekleniyor...
git add .

echo 3. Commit oluşturuluyor...
git commit -m "Initial commit - ZB MUSIC Bot"

echo 4. Main branch ayarlanıyor...
git branch -M main

echo 5. Remote origin ekleniyor...
echo Lütfen GitHub repository URL'sini girin:
set /p repo_url="Repository URL: "
git remote add origin %repo_url%

echo 6. Push işlemi...
git push -u origin main

echo.
echo ✅ Yükleme tamamlandı!
echo GitHub repository: %repo_url%
pause
