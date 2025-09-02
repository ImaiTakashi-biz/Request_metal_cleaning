@echo off
echo 洗浄依頼管理App v1.0 正式版をビルド中...

REM 既存のbuildとdistフォルダを削除
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM PyInstallerでEXEファイルを作成
pyinstaller metal_cleaning_app.spec

REM ビルド結果を確認
if exist "dist\洗浄依頼管理App_v1.0.exe" (
    echo.
    echo ✓ v1.0正式版ビルドが完了しました！
    echo EXEファイルの場所: dist\洗浄依頼管理App_v1.0.exe
    echo.
    echo 配布パッケージを作成するには create_package.bat を実行してください。
    echo.
    pause
) else (
    echo.
    echo ✗ ビルドに失敗しました。エラーログを確認してください。
    echo.
    pause
)