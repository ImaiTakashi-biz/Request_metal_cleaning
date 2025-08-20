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

MODERN_STYLESHEET = """
/* Modern Flat UI Stylesheet */

QMainWindow, QWidget {
    background-color: #F5F5F5; /* Off-white background */
    font-family: 'Segoe UI', 'Meiryo UI', 'MS PGothic', sans-serif;
}

#mainTitle {
    font-size: 22px;
    font-weight: bold;
    color: #0053a6; /* Corporate Blue */
    padding: 10px 5px;
}

QPushButton {
    background-color: #007BFF;
    color: white;
    border: none;
    padding: 8px 16px;
    font-size: 14px;
    border-radius: 4px;
}
QPushButton:hover {
    background-color: #0056b3;
}
QPushButton:pressed {
    background-color: #004494;
}

/* CheckBox Styling */
QCheckBox {
    color: #212121;
    spacing: 5px;
}
QCheckBox::indicator {
    border: 1px solid #B0B0B0;
    border-radius: 3px;
    width: 15px;
    height: 15px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:checked {
    background-color: #007BFF;
    border-color: #007BFF;
}

/* ComboBox Styling */
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #D0D0D0;
    border-radius: 4px;
    padding: 5px;
    color: #212121; /* Dark text for dropdown */
}
QComboBox::drop-down {
    border: none;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #D0D0D0;
    selection-background-color: #E8E8E8; /* Gray selection */
    selection-color: #212121;
    color: #212121;
    outline: 0px;
}
QComboBox QAbstractItemView::item {
    color: #212121;
    padding: 5px;
}

/* TableView Styling */
QTableView {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    gridline-color: #E0E0E0;
    font-size: 14px;
}
QTableView::item {
    padding: 5px;
    color: #212121;
}
QTableView::item:selected {
    background-color: #E8E8E8; /* Subtle gray selection */
    color: #212121;
}

/* Header Styling */
QHeaderView::section {
    background-color: #F5F5F5;
    padding: 6px;
    border: none;
    border-bottom: 1px solid #E0E0E0;
    font-size: 14px;
    font-weight: bold;
    color: #212121; /* Dark text for header */
}

/* Calendar Widget Styling */
QCalendarWidget QToolButton {
    color: white;
    background-color: #007BFF;
    border: none;
    padding: 8px;
    border-radius: 4px;
    font-size: 14px;
    margin: 2px;
}
QCalendarWidget QMenu {
    background-color: white;
}
QCalendarWidget QSpinBox {
    background-color: white;
    border: 1px solid #E0E0E0;
    padding: 4px;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #007BFF;
}
QCalendarWidget QTableView {
    selection-background-color: #007BFF;
    selection-color: white;
    border: none;
}

QStatusBar {
    font-size: 12px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("洗浄依頼管理アプリ")
        self.setGeometry(100, 100, 1200, 800)

        self.config = load_config()
        if not self.config:
            self.show_critical_error("設定ファイル 'config.json' が見つからないか、不正です。")
            sys.exit(1)
        
        self.db_handler = DatabaseHandler(self.config['database']['path'])
        
        self.setup_ui()
        
        self.table_model = CleaningTableModel(config=self.config)
        self.table_view.setModel(self.table_model)

        self.setup_delegates()
        self.setup_table_columns() # 新しいメソッド呼び出し

        self.connect_to_db_and_load_data()

        self.refresh_button.clicked.connect(self.load_data_for_selected_date)
        self.calendar.selectionChanged.connect(self.load_data_for_selected_date)
        self.table_model.db_update_signal.connect(self.update_database_record)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        title_label = QLabel("洗浄依頼管理")
        title_label.setObjectName("mainTitle")

        top_panel = QHBoxLayout()
        
        self.calendar = QCalendarWidget()
        self.calendar.setFixedWidth(400)
        
        self.refresh_button = QPushButton("🔄 データ更新")
        
        control_panel = QVBoxLayout()
        control_panel.addWidget(self.refresh_button)
        control_panel.addStretch()

        top_panel.addWidget(self.calendar)
        top_panel.addLayout(control_panel)

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setAlternatingRowColors(True)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

        main_layout.addWidget(title_label)
        main_layout.addLayout(top_panel)
        main_layout.addWidget(self.table_view)

    def setup_table_columns(self):
        """テーブルの列のサイズモードと初期幅を個別に設定する"""
        header = self.table_view.horizontalHeader()
        for i in range(self.table_model.columnCount()):
            col_name = self.table_model._headers[i]
            if col_name in ["remarks", "cleaning_instruction"]:
                header.setSectionResizeMode(i, QHeaderView.Fixed)
                self.table_view.setColumnWidth(i, 100)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        # 最後の列（洗浄指示）を可変ではなく、内容に合わせるように変更
        last_col_index = self.table_model.columnCount() - 1
        if self.table_model._headers[last_col_index] not in ["remarks", "cleaning_instruction"]:
             header.setSectionResizeMode(last_col_index, QHeaderView.Stretch)
        else:
             # もし最後の列が固定幅の列だった場合、その一つ前をストレッチさせるなど、要件に応じて調整
             pass

    def setup_delegates(self):
        try:
            col_index = self.table_model._headers.index("cleaning_instruction")
            items = ["", "1", "2", "3", "4"]
            delegate = EditableComboBoxDelegate(items=items, parent=self.table_view)
            self.table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError:
            print("Warning: 'cleaning_instruction' column not found.")

        try:
            col_index = self.table_model._headers.index("remarks")
            items = ["出荷無し", "1st外観"]
            delegate = EditableComboBoxDelegate(items=items, parent=self.table_view)
            self.table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError:
            print("Warning: 'remarks' column not found.")

    @Slot()
    def connect_to_db_and_load_data(self):
        if self.db_handler.connect():
            self.status_label.setText("データベースに接続しました。")
            self.load_data_for_selected_date()
        else:
            self.show_critical_error(f"データベース接続に失敗しました。\nパスを確認してください: {self.config['database']['path']}")

    @Slot()
    def load_data_for_selected_date(self):
        selected_date = self.calendar.selectedDate().toString("yyyy-MM-dd")
        self.status_label.setText(f"{selected_date} のデータを読み込み中...")
        
        data, error = self.db_handler.get_data_by_date(selected_date)
        
        if error:
            self.table_model.load_data([])
            self.status_label.setText(f"エラー: {error}")
            QMessageBox.warning(self, "データベースエラー", f"データの読み込みに失敗しました。\n\n詳細: {error}")
        else:
            self.table_model.load_data(data)
            self.status_label.setText(f"{selected_date} のデータ {len(data)} 件を読み込みました。")
            # self.table_view.resizeColumnsToContents() # 個別設定に切り替えたため不要に

    @Slot(int, str, object)
    def update_database_record(self, record_id, column, value):
        success = self.db_handler.update_record(record_id, column, value)
        if success:
            self.status_label.setText(f"レコード {record_id} の {column} を更新しました。")
        else:
            self.status_label.setText(f"レコード {record_id} の更新に失敗しました。")
            self.load_data_for_selected_date()

    def show_critical_error(self, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("エラー")
        msg_box.exec()

    def closeEvent(self, event):
        if self.db_handler:
            self.db_handler.close()
        super().closeEvent(event)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyleSheet(MODERN_STYLESHEET) # スタイルシートをアプリ全体に適用
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
