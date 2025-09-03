import json
import os
import sys

def get_config_file_path():
    """
    EXE実行時とスクリプト実行時の両方に対応したconfig.jsonのパスを取得
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstallerでEXE化された場合
        return os.path.join(sys._MEIPASS, 'config.json')
    else:
        # 通常のスクリプト実行の場合
        return os.path.join(os.path.dirname(__file__), '..', 'config.json')

def load_config():
    """
    config.jsonから設定を読み込む
    :return: 設定の辞書
    """
    config_file = get_config_file_path()
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Error: Configuration file not found at {config_file}")
        return None
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {config_file}")
        return None