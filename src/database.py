import sqlite3
import os

class DatabaseHandler:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None

    def connect(self):
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=5)
            # Row factoryをここに設定すると、すべてのカーソルが辞書風の行を返すようになる
            self.conn.row_factory = sqlite3.Row
            print("Database connection successful.")
            return True
        except sqlite3.Error as e:
            print(f"Error connecting to database: {e}")
            self.conn = None
            return False

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None
            print("Database connection closed.")

    def get_data_by_date(self, acquisition_date):
        """
        指定された取得日でデータを取得する
        :param acquisition_date: YYYY-MM-DD形式の日付文字列
        :return: (データのリスト, エラーメッセージ) のタプル。成功時はエラーメッセージがNone。
        """
        if not self.conn:
            return None, "データベースに接続されていません。"
        
        # 要件定義書のサンプルクエリ。テーブル名が異なる可能性がある。
        query = "SELECT * FROM production_plan WHERE acquisition_date = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (acquisition_date,))
            rows = cursor.fetchall()
            # sqlite3.Rowオブジェクトを辞書のリストに変換
            data = [dict(row) for row in rows]
            return data, None
        except sqlite3.Error as e:
            error_msg = f"データ取得失敗: {e}"
            print(error_msg)
            return None, error_msg

    def update_record(self, record_id, column, value):
        if not self.conn:
            return False

        # 'id' カラムを主キーと仮定
        query = f"UPDATE production_plan SET {column} = ? WHERE id = ?"
        
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (value, record_id))
            self.conn.commit()
            print(f"Record {record_id} updated. Set {column} to {value}")
            return True
        except sqlite3.Error as e:
            print(f"Failed to update record: {e}")
            self.conn.rollback()
            return False

