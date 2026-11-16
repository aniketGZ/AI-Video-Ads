@echo off
cd /d "%~dp0"
echo ===================================================
echo Starting AI Video Ads Engine locally...
echo URL: http://127.0.0.1:8001
echo ===================================================
python -m uvicorn app:app --host 127.0.0.1 --port 8001 --reload
pause
