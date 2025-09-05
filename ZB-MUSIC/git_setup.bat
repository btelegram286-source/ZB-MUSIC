@echo off
cd /d "%~dp0"
git init
git add .
git commit -m "Initial commit - ZB MUSIC Bot"
git remote add origin https://github.com/btelegram286-source/ZB-MUSIC.git
git push -u origin master
