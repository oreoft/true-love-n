@echo off
setlocal EnableExtensions

REM ===== 配置 =====
set "WORKUNC=\\wsl.localhost\Ubuntu\root\true-love-n\true-love-base"
set "PY=C:\Users\admin\.venvs\true-love-base\Scripts\python.exe"
set "MODULE=true_love_base"

REM ===== 校验 python =====
if not exist "%PY%" (
  echo [ERROR] python not found: %PY%
  exit /b 1
)

REM ===== 切到项目目录（UNC 必须用 pushd）=====
pushd "%WORKUNC%"
if errorlevel 1 (
  echo [ERROR] pushd failed: %WORKUNC%
  exit /b 2
)

REM ===== 直接前台运行（日志直出）=====
echo =========================================
echo Starting true_love_base
echo PY=%PY%
echo CWD=%CD%
echo =========================================

"%PY%" -u -m %MODULE%
set RC=%ERRORLEVEL%

echo =========================================
echo Process exited with code %RC%
echo =========================================

popd
exit /b %RC%