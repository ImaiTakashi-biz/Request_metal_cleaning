import sys
import collections
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QTableView, QCalendarWidget, QPushButton,
    QHBoxLayout, QStatusBar, QLabel, QMessageBox, QHeaderView,
    QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import QDate, Slot, Qt, QEvent, QModelIndex

from config import load_config
from database import DatabaseHandler
from models import CleaningTableModel, ComboBoxDelegate, EditableComboBoxDelegate

FINAL_STYLESHEET = """
/* Modern & Sophisticated UI Stylesheet */

QMainWindow, QWidget {
    background-color: #F8F9FA; /* Very light gray, almost white */
    font-family: 'Noto Sans JP', 'Segoe UI', 'Roboto', 'Helvetica Neue', sans-serif; /* Modern font stack */
    color: #343A40; /* Darker text for better contrast */
    font-size: 14px;
}

#mainTitle {
    font-size: 28px; /* Larger title */
    font-weight: 700; /* Bolder */
    color: #2C48B3; /* Corporate blue */
    padding: 15px 10px;
    margin-bottom: 10px;
    border-bottom: 1px solid #E9ECEF; /* Subtle separator */
}

#unprocessedTitle {
    font-size: 18px;
    font-weight: 600;
    color: #343A40;
    margin-bottom: 10px;
}

QPushButton {
    background-color: #3457D5; /* Corporate blue */
    color: white;
    border: none;
    padding: 12px 22px; /* Slightly larger padding */
    font-size: 15px; /* Slightly larger font */
    font-weight: 600;
    border-radius: 8px; /* More rounded corners */
    min-width: 120px;
    transition: background-color 0.3s ease; /* Smooth transition */
}
QPushButton:hover {
    background-color: #2C48B3; /* Darker blue on hover */
}
QPushButton:pressed {
    background-color: #1A3A9A; /* Even darker on press */
}

/* Consistent styling for input widgets */
QComboBox, QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #CED4DA; /* Lighter border */
    border-radius: 8px; /* More rounded */
    padding: 8px 12px; /* More padding */
    color: #495057; /* Slightly softer text color */
    font-size: 14px;
    min-height: 32px;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}
QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #CED4DA;
    selection-background-color: #E9ECEF; /* Subtle selection */
    selection-color: #343A40;
    color: #343A40;
    outline: 0px;
    border-radius: 8px;
}

/* CheckBox */
QCheckBox {
    color: #343A40;
    spacing: 8px; /* More spacing */
    font-size: 14px;
}
QCheckBox::indicator {
    border: 1px solid #ADB5BD; /* Softer border */
    border-radius: 4px; /* Slightly more rounded */
    width: 18px; /* Larger indicator */
    height: 18px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:hover {
    border: 1px solid #3457D5;
}
QCheckBox::indicator:checked {
    background-color: #3457D5;
    border-color: #3457D5;
}

/* Table */
QTableView, QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E9ECEF; /* Subtle border for the whole table */
    border-radius: 8px; /* Rounded corners for the table */
    gridline-color: #F1F3F5;
    font-size: 14px;
    alternate-background-color: #FDFDFD;
    selection-background-color: #E9ECEF; /* Consistent selection color */
    selection-color: #343A40;
    outline: 0; /* Remove focus outline */
}
QTableView::item, QTableWidget::item {
    padding: 10px 12px; /* More padding for items */
    border-bottom: 1px solid #E9ECEF; /* Lighter separator */
    color: #343A40;
}
QTableView::item:selected, QTableWidget::item:selected {
    background-color: #E9ECEF;
    color: #343A40;
}

/* Table Header */
QHeaderView::section {
    background-color: #F8F9FA; /* Lighter header background */
    padding: 12px 12px; /* More padding */
    border: none;
    border-bottom: 2px solid #DEE2E6;
    font-size: 14px;
    font-weight: 600;
    color: #495057; /* Softer header text */
    text-align: left; /* Align text to left */
}
QHeaderView::section:last {
    border-right: none;
}

/* Calendar */
QCalendarWidget {
    background-color: #FFFFFF;
    border-radius: 8px; /* More rounded */
    border: 1px solid #E9ECEF; /* Subtle border */
    padding: 10px;
}
QCalendarWidget QToolButton {
    color: #3457D5; /* Corporate blue for navigation buttons */
    background-color: transparent;
    font-size: 18px; /* Larger navigation arrows */
    font-weight: 600;
    border-radius: 5px;
}
QCalendarWidget QToolButton:hover {
    background-color: #E9ECEF;
}
QCalendarWidget QWidget#qt_calendar_navigationbar {
    background-color: #F8F9FA; /* Lighter navigation bar */
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    padding: 5px;
}
QCalendarWidget QTableView {
    selection-background-color: #3457D5; /* Corporate blue for selected date */
    selection-color: white;
    border: none;
    gridline-color: #F1F3F5;
    font-size: 14px;
}
QCalendarWidget QTableView QHeaderView::section {
    background-color: #FFFFFF;
    border: none;
    padding: 6px;
    font-size: 13px;
    font-weight: 500;
    color: #6C757D; /* Softer day names */
}
QCalendarWidget QTableView::item:hover {
    background-color: #E9ECEF; /* Subtle hover effect */
}
QCalendarWidget QTableView::item:selected {
    background-color: #3457D5;
    color: white;
    border-radius: 4px; /* Slightly rounded selected date */
}
QCalendarWidget QTableView::item:disabled {
    color: #ADB5BD; /* Disabled dates */
}

/* Status Bar */
QStatusBar {
    font-size: 13px;
    background-color: #F8F9FA;
    border-top: 1px solid #DEE2E6;
    color: #495057;
    padding: 5px 10px;
}
"""

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("洗浄依頼管理アプリ")
        self.setGeometry(100, 100, 1200, 800)
        self.showMaximized()

        self.config = load_config()
        if not self.config:
            self.show_critical_error("設定ファイル 'config.json' が見つからないか、不正です。")
            sys.exit(1)

        self.db_handler = DatabaseHandler(self.config['database']['path'])

        self.setup_ui()

        self.table_model = CleaningTableModel(config=self.config)
        self.table_view.setModel(self.table_model)

        self.setup_delegates()
        self.setup_table_columns()

        self.connect_to_db_and_load_data()

        # --- シグナルとスロットの接続 ---
        self.calendar.selectionChanged.connect(self.load_data_for_selected_date)
        self.table_model.db_update_signal.connect(self.update_database_record)
        self.table_model.data_changed_for_unprocessed_list.connect(self.refresh_unprocessed_list_from_model)
        self.table_view.clicked.connect(self.handle_table_click)
        self.calendar.installEventFilter(self)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)

        title_label = QLabel("洗浄依頼管理")
        title_label.setObjectName("mainTitle")

        top_panel = QHBoxLayout()
        top_panel.setSpacing(20)

        self.calendar = QCalendarWidget()
        self.calendar.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
        self.calendar.setSelectedDate(QDate.currentDate())
        self.calendar.setFixedWidth(400)
        top_panel.addWidget(self.calendar)

        # 製造払い出し未機番リスト表示エリア
        unprocessed_widget = QWidget()
        unprocessed_layout = QVBoxLayout(unprocessed_widget)
        unprocessed_title = QLabel("製造未払い出し機番")
        unprocessed_title.setObjectName("unprocessedTitle")
        self.unprocessed_table = QTableWidget()
        self.unprocessed_table.setColumnCount(6)
        self.unprocessed_table.setHorizontalHeaderLabels(["A line", "B line", "C line", "D line", "E line", "F line"])
        self.unprocessed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.unprocessed_table.verticalHeader().setVisible(False)
        self.unprocessed_table.setEditTriggers(QTableWidget.NoEditTriggers)
        unprocessed_layout.addWidget(unprocessed_title)
        unprocessed_layout.addWidget(self.unprocessed_table)
        top_panel.addWidget(unprocessed_widget)

        top_panel.addStretch()

        self.table_view = QTableView()
        self.table_view.setSortingEnabled(True)
        self.table_view.setShowGrid(False)
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setEditTriggers(QTableView.NoEditTriggers)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

        main_layout.addWidget(title_label)
        main_layout.addLayout(top_panel)
        main_layout.addWidget(self.table_view)

    def setup_table_columns(self):
        header = self.table_view.horizontalHeader()
        product_name_index = -1

        for i in range(self.table_model.columnCount()):
            col_name = self.table_model._headers[i]
            if col_name in ["remarks", "cleaning_instruction"]:
                header.setSectionResizeMode(i, QHeaderView.Fixed)
                self.table_view.setColumnWidth(i, 150)
            elif col_name == "product_name":
                product_name_index = i
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        if product_name_index != -1:
            header.setSectionResizeMode(product_name_index, QHeaderView.Stretch)

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

    @Slot(QModelIndex)
    def handle_table_click(self, index):
        if index.isValid():
            col_name = self.table_model._headers[index.column()]
            if col_name in ["cleaning_instruction", "remarks"]:
                self.table_view.edit(index)

    def eventFilter(self, obj, event):
        if obj == self.calendar and event.type() == QEvent.Type.Wheel:
            return True
        return super().eventFilter(obj, event)

    @Slot()
    def refresh_unprocessed_list_from_model(self):
        if self.table_model:
            self.update_unprocessed_table(self.table_model._data)

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
            self.update_unprocessed_table(data)

    def update_unprocessed_table(self, data):
        self.unprocessed_table.clearContents()
        self.unprocessed_table.setRowCount(0)

        unprocessed = [d for d in data if str(d.get('cleaning_instruction', '0')) not in ['0', ''] and not d.get('manufacturing_check')]
        
        if not unprocessed:
            return

        grouped = collections.defaultdict(list)
        for item in unprocessed:
            machine_no = item.get('machine_no')
            if machine_no:
                grouped[machine_no[0]].append(machine_no)

        col_map = {chr(ord('A') + i): i for i in range(6)} # {'A':0, 'B':1, ...}
        max_rows = 0

        for line, machine_nos in grouped.items():
            col = col_map.get(line)
            if col is None: continue

            machine_nos.sort()
            if len(machine_nos) > max_rows:
                max_rows = len(machine_nos)
                self.unprocessed_table.setRowCount(max_rows)

            for row, machine_no in enumerate(machine_nos):
                item = QTableWidgetItem(machine_no)
                self.unprocessed_table.setItem(row, col, item)

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
    app.setStyleSheet(FINAL_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())