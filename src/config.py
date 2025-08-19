import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config.json')

def load_config():
    """
    config.jsonから設定を読み込む
    :return: 設定の辞書
    """
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {CONFIG_FILE}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {CONFIG_FILE}")
        return None

# --- 使用例 ---
# if __name__ == '__main__':
#     settings = load_config()
#     if settings:
#         print("Configuration loaded successfully:")
#         print(settings)
