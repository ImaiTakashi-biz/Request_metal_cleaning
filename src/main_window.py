import sys
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QTableView, QCalendarWidget, QPushButton,
    QHBoxLayout, QStatusBar, QLabel, QMessageBox, QHeaderView
)
from PySide6.QtCore import QDate, Slot, Qt

from config import load_config
from database import DatabaseHandler
from models import CleaningTableModel, ComboBoxDelegate, EditableComboBoxDelegate

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("洗浄依頼管理アプリ")
        self.setGeometry(100, 100, 1024, 768)

        # --- 設定とDBハンドラの初期化 ---
        self.config = load_config()
        if not self.config:
            self.show_critical_error("設定ファイル 'config.json' が見つからないか、不正です。")
            sys.exit(1)
        
        self.db_handler = DatabaseHandler(self.config['database']['path'])
        
        # --- UIのセットアップ ---
        self.setup_ui()
        
        # --- モデルの初期化とテーブルへの設定 ---
        self.table_model = CleaningTableModel(config=self.config)
        self.table_view.setModel(self.table_model)

        # --- デリゲートの設定 ---
        self.setup_delegates()

        # --- 接続とデータロード ---
        self.connect_to_db_and_load_data()

        # --- シグナルとスロットの接続 ---
        self.refresh_button.clicked.connect(self.load_data_for_selected_date)
        self.calendar.selectionChanged.connect(self.load_data_for_selected_date)
        self.table_model.db_update_signal.connect(self.update_database_record)

    def setup_ui(self):
        """UIウィジェットの作成とレイアウト"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- 上部パネル ---
        top_panel = QWidget()
        top_layout = QHBoxLayout(top_panel)
        
        self.calendar = QCalendarWidget()
        self.calendar.setSelectedDate(QDate.currentDate())
        
        self.refresh_button = QPushButton("データ更新")

        top_layout.addWidget(self.calendar)
        top_layout.addStretch()
        top_layout.addWidget(self.refresh_button)

        # --- データテーブル ---
        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)
        # ユーザーが列幅を自由に変更できるようにする
        self.table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # --- ステータスバー ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

        # --- レイアウトへの追加 ---
        main_layout.addWidget(top_panel)
        main_layout.addWidget(self.table_view)

    def setup_delegates(self):
        """テーブルビューにカスタムデリゲートを設定する"""
        # 洗浄指示 (編集可能なドロップダウン)
        try:
            col_index = self.table_model._headers.index("cleaning_instruction")
            items = ["", "1", "2", "3", "4"]
            delegate = EditableComboBoxDelegate(items=items, parent=self.table_view)
            self.table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError:
            print("Warning: 'cleaning_instruction' column not found.")

        # 備考 (編集可能なドロップダウン)
        try:
            col_index = self.table_model._headers.index("remarks")
            items = ["出荷無し", "1st外観"]
            delegate = EditableComboBoxDelegate(items=items, parent=self.table_view)
            self.table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError:
            print("Warning: 'remarks' column not found.")

    @Slot()
    def connect_to_db_and_load_data(self):
        """DBに接続し、初期データをロードする"""
        if self.db_handler.connect():
            self.status_label.setText("データベースに接続しました。")
            self.load_data_for_selected_date()
        else:
            self.show_critical_error(f"データベース接続に失敗しました。\nパスを確認してください: {self.config['database']['path']}")

    @Slot()
    def load_data_for_selected_date(self):
        """選択された日付のデータをDBからロードしてテーブルに表示する"""
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.status_label.setText(f"{selected_date} のデータを読み込み中...")
        
        data, error = self.db_handler.get_data_by_date(selected_date)
        
        if error:
            self.table_model.load_data([]) # エラー時はテーブルをクリア
            self.status_label.setText(f"エラー: {error}")
            QMessageBox.warning(self, "データベースエラー", f"データの読み込みに失敗しました。\n\n詳細: {error}")
        else:
            self.table_model.load_data(data)
            self.status_label.setText(f"{selected_date} のデータ {len(data)} 件を読み込みました。")
            # データロード後に列幅を調整
            self.table_view.resizeColumnsToContents()
            try:
                remarks_col_index = self.table_model._headers.index("remarks")
                self.table_view.setColumnWidth(remarks_col_index, 200)
            except ValueError:
                pass # カラムがなければ何もしない

    @Slot(int, str, object)
    def update_database_record(self, record_id, column, value):
        """モデルからのシグナルを受けてDBを更新する"""
        success = self.db_handler.update_record(record_id, column, value)
        if success:
            self.status_label.setText(f"レコード {record_id} の {column} を更新しました。")
        else:
            self.status_label.setText(f"レコード {record_id} の更新に失敗しました。")
            self.load_data_for_selected_date() # 失敗時はデータを再読み込みしてUIを元に戻す

    def show_critical_error(self, message):
        """致命的なエラーメッセージを表示する"""
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("エラー")
        msg_box.exec()

    def closeEvent(self, event):
        """ウィンドウが閉じられるときにDB接続をクリーンアップする"""
        if self.db_handler:
            self.db_handler.close()
        super().closeEvent(event)

# --- アプリケーションの実行 ---
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
