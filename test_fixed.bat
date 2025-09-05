@echo off
cd /d ZB-MUSIC
python -c "from playback_controls_fixed import handle_playback_callback, create_playback_markup; print('Playback controls başarıyla import edildi')"
pause
