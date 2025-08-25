# 洗浄依頼管理App

金属部品の洗浄依頼を管理するためのデスクトップアプリケーション

## 概要

このアプリケーションは製造業や工業分野において、金属部品の洗浄作業を効率的に管理するためのツールです。

### 主な機能

- 洗浄依頼の登録・管理
- 洗浄指示の作成・編集
- データの永続化（データベース保存）
- 設定のカスタマイズ（JSON設定ファイル）

## 技術スタック

- **言語**: Python 3.x
- **GUIフレームワーク**: PySide6
- **データベース**: SQLite
- **設定管理**: JSON
- **ビルドツール**: PyInstaller

## 開発環境のセットアップ

### 必要な依存関係

```bash
pip install -r requirements.txt
```

### アプリケーションの実行

```bash
python src/main.py
```

## ビルド・配布

### アイコンの作成（オプション）

アプリにカスタムアイコンを使用する場合:

1. 256x256ピクセルのICOファイルを作成
2. ファイル名を`app_icon.ico`としてプロジェクトルートに配置
3. ビルドを実行

**推奨デザイン**: 
- メインモチーフ: 金属部品（歯車、パイプなど）
- 洗浄要素: 水しぶき、泡、光
- カラー: シルバー/グレー + ブルー + ホワイト

### EXEファイルの作成

```bash
# Windows用バッチファイルを使用
build_exe.bat

# または直接PyInstallerを実行
pyinstaller metal_cleaning_app.spec
```

### 配布パッケージの作成

```bash
create_package.bat
```

## プロジェクト構造

```
Request_metal_cleaning/
├── src/                    # ソースコード
│   ├── main.py            # メインエントリポイント
│   ├── main_window.py     # メインウィンドウ
│   ├── config.py          # 設定管理
│   ├── database.py        # データベース管理
│   └── models.py          # データモデル
├── config.json            # アプリケーション設定
├── requirements.txt       # Python依存関係
├── metal_cleaning_app.spec # PyInstaller設定
├── version.txt            # バージョン情報
└── README.md              # このファイル
```

## 設定

アプリケーションの設定は `config.json` ファイルで管理されます。詳細は設定ファイルのコメントを参照してください。

## バージョン履歴

- v0.9-beta: 初期ベータ版リリース

## ライセンス

[ライセンス情報を記載]

## お問い合わせ

[連絡先情報を記載]