@echo off
cd /d "%~dp0"
pip install -r requirements.txt -q 2>nul
pythonw app.py
