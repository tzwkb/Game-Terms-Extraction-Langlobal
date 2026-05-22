@echo off
cd /d "%~dp0"

if exist python\python.exe (
    set PY=python\python.exe
) else (
    where python >nul 2>nul
    if not errorlevel 1 (
        set PY=python
    ) else (
        echo [run.bat] No Python found, running setup.bat...
        call setup.bat
        if errorlevel 1 (
            pause & exit /b 1
        )
        set PY=python\python.exe
    )
)

%PY% -m streamlit run ui/app.py --browser.gatherUsageStats false
pause
