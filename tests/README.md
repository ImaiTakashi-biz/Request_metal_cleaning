# テストディレクトリ

このディレクトリには、アプリケーションのテストファイルを配置します。

## 将来的に追加予定のテスト

- `test_config.py` - 設定管理のテスト
- `test_database.py` - データベース操作のテスト
- `test_models.py` - データモデルのテスト
- `test_main_window.py` - UIコンポーネントのテスト

## テストの実行方法

```bash
# 開発用依存関係をインストール
pip install -r requirements-dev.txt

# テストの実行（将来的に）
pytest tests/
```