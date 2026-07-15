@echo off
set PYTHONHOME=
set ALLOWED_ORIGIN=https://riffscribe.app
set PUBLIC_BASE_URL=https://api.riffscribe.app
cd /d "C:\Users\Harel Volotzky\guitar-solo-tabs\backend"
:loop
"C:\Users\Harel Volotzky\guitar-solo-tabs\backend\venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 >> "C:\Users\Harel Volotzky\guitar-solo-tabs\backend\backend-log.txt" 2>&1
echo ---restarted at %date% %time%--- >> "C:\Users\Harel Volotzky\guitar-solo-tabs\backend\backend-log.txt"
ping -n 6 127.0.0.1 >nul
goto loop
