@echo off
echo 配布パッケージを作成しています...

REM 配布用フォルダを作成
set PACKAGE_NAME=洗浄依頼管理App
if exist "%PACKAGE_NAME%" rmdir /s /q "%PACKAGE_NAME%"
mkdir "%PACKAGE_NAME%"

REM 必要なファイルをコピー
if exist "dist\洗浄依頼管理App_v0.9_beta.exe" (
    copy "dist\洗浄依頼管理App_v0.9_beta.exe" "%PACKAGE_NAME%\"
    echo ✓ EXEファイルをコピーしました
) else (
    echo ✗ EXEファイルが見つかりません。先にbuild_exe.batを実行してください。
    dir dist
    pause
    exit /b 1
)

if exist "config.json" (
    copy "config.json" "%PACKAGE_NAME%\"
    echo ✓ 設定ファイルをコピーしました
) else (
    echo ⚠ 警告: config.jsonが見つかりません
)

if exist "README.txt" (
    copy "README.txt" "%PACKAGE_NAME%\"
    echo ✓ READMEファイルをコピーしました
)

echo.
echo ✓ 配布パッケージが作成されました: %PACKAGE_NAME%
echo   以下のファイルが含まれています:
dir /b "%PACKAGE_NAME%"
echo.
echo このフォルダをZIPに圧縮してテスト配布してください。
echo ※現在はベータ版（v0.9）です。正式リリース時にはv1.0に更新してください。
echo.
pause