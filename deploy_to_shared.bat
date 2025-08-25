@echo off
echo 洗浄依頼管理App_v0.9_beta 配布スクリプト
echo =========================================

REM 配布先共有フォルダのパス（必要に応じて変更してください）
set SHARED_FOLDER=\\192.168.1.200\共有\製造課\ロボパット\洗浄依頼管理App
REM ローカル配布フォルダ
set LOCAL_PACKAGE=洗浄依頼管理App

echo.
echo 配布準備中...

REM 共有フォルダの存在確認
if not exist "%SHARED_FOLDER%" (
    echo ❌ エラー: 共有フォルダにアクセスできません
    echo 共有フォルダパス: %SHARED_FOLDER%
    echo.
    echo 以下を確認してください:
    echo 1. ネットワーク接続
    echo 2. 共有フォルダのアクセス権限
    echo 3. パスの正確性
    pause
    exit /b 1
)

REM ローカル配布パッケージの存在確認
if not exist "%LOCAL_PACKAGE%" (
    echo ❌ エラー: 配布パッケージが見つかりません
    echo 先に create_package.bat を実行してください
    pause
    exit /b 1
)

echo.
echo 📁 配布先: %SHARED_FOLDER%
echo 📦 配布元: %LOCAL_PACKAGE%
echo.

REM バックアップの作成（既存ファイルがある場合）
if exist "%SHARED_FOLDER%\洗浄依頼管理App_v0.9_beta.exe" (
    echo 🔄 既存ファイルのバックアップを作成中...
    set BACKUP_DIR=%SHARED_FOLDER%\backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%
    set BACKUP_DIR=!BACKUP_DIR: =0!
    mkdir "!BACKUP_DIR!" 2>nul
    copy "%SHARED_FOLDER%\*.*" "!BACKUP_DIR!\" >nul
    echo ✅ バックアップ完了: !BACKUP_DIR!
)

echo.
echo 📤 ファイルをコピー中...

REM 配布ファイルのコピー
copy "%LOCAL_PACKAGE%\*.*" "%SHARED_FOLDER%\" >nul
if %errorlevel% equ 0 (
    echo ✅ 配布完了！
    echo.
    echo 📋 配布されたファイル:
    dir /b "%SHARED_FOLDER%"
    echo.
    echo 💡 ユーザーへの案内:
    echo    共有フォルダから洗浄依頼管理App_v0.9_beta.exeを実行してください
    echo    パス: %SHARED_FOLDER%
) else (
    echo ❌ エラー: ファイルのコピーに失敗しました
    echo 権限やネットワーク接続を確認してください
)

echo.
echo 配布作業完了
pause