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

    def copy_cleaning_instructions(self, source_date, destination_date):
        """
        ある日付の洗浄指示を別の日付にコピーする
        :param source_date: YYYY-MM-DD形式のコピー元日付
        :param destination_date: YYYY-MM-DD形式のコピー先日付
        :return: (成功したかどうか, 更新した件数またはエラーメッセージ)
        """
        if not self.conn:
            return False, "データベースに接続されていません。"

        # 1. コピー元の洗浄指示を取得 (機番をキーにした辞書を作成)
        source_query = "SELECT machine_no, cleaning_instruction FROM production_plan WHERE acquisition_date = ? AND cleaning_instruction IS NOT NULL AND cleaning_instruction != ''"
        try:
            cursor = self.conn.cursor()
            cursor.execute(source_query, (source_date,))
            source_rows = cursor.fetchall()
            source_instructions = {row['machine_no']: row['cleaning_instruction'] for row in source_rows}
        except sqlite3.Error as e:
            return False, f"コピー元データの取得に失敗: {e}"

        if not source_instructions:
            return False, "コピー元の有効な洗浄指示データがありません。"

        # 2. コピー先のレコードを取得
        dest_query = "SELECT id, machine_no FROM production_plan WHERE acquisition_date = ?"
        try:
            cursor.execute(dest_query, (destination_date,))
            dest_rows = cursor.fetchall()
        except sqlite3.Error as e:
            return False, f"コピー先データの取得に失敗: {e}"

        # 3. トランザクション内で更新処理
        update_query = "UPDATE production_plan SET cleaning_instruction = ? WHERE id = ?"
        updated_count = 0
        try:
            self.conn.execute("BEGIN TRANSACTION")
            for row in dest_rows:
                machine_no = row['machine_no']
                record_id = row['id']
                if machine_no in source_instructions:
                    new_instruction = source_instructions[machine_no]
                    cursor.execute(update_query, (new_instruction, record_id))
                    updated_count += 1
            self.conn.commit()
            return True, updated_count
        except sqlite3.Error as e:
            self.conn.rollback()
            return False, f"データベースの更新に失敗: {e}"

    def get_record_value(self, record_id, column):
        """
        指定されたレコードの特定カラムの現在値を取得（Undo/Redo履歴用）
        :param record_id: レコードID
        :param column: カラム名
        :return: 現在の値（取得失敗時はNone）
        """
        if not self.conn:
            return None
        
        query = f"SELECT {column} FROM production_plan WHERE id = ?"
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, (record_id,))
            row = cursor.fetchone()
            if row:
                return row[column]
            return None
        except sqlite3.Error as e:
            print(f"Failed to get record value: {e}")
            return None