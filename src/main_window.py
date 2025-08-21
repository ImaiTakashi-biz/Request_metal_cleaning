import sys
import collections
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QTableView, QDateEdit, QPushButton,
    QHBoxLayout, QStatusBar, QLabel, QMessageBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QStackedWidget, QButtonGroup, QSizePolicy
)
from PySide6.QtCore import QDate, Slot, Qt, QModelIndex

from config import load_config
from database import DatabaseHandler
from models import MainTableModel, CleaningInstructionTableModel, ComboBoxDelegate, EditableComboBoxDelegate

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

QPushButton.page-button {
    background-color: #E9ECEF;
    color: #495057;
    font-weight: 500;
}

QPushButton.page-button:checked {
    background-color: #3457D5;
    color: white;
    font-weight: 600;
}


/* Consistent styling for input widgets */
QComboBox, QLineEdit, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #CED4DA; /* Lighter border */
    border-radius: 8px; /* More rounded */
    padding: 8px 12px; /* More padding */
    color: #495057; /* Slightly softer text color */
    font-size: 14px;
    min-height: 32px;
}
QComboBox::drop-down, QDateEdit::drop-down {
    border: none;
    width: 20px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}
QComboBox QAbstractItemView, QDateEdit QAbstractItemView {
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
        self.setGeometry(100, 100, 1800, 960)
        self.showMaximized()

        self.config = load_config()
        if not self.config:
            self.show_critical_error("設定ファイル 'config.json' が見つからないか、不正です。")
            sys.exit(1)

        self.db_handler = DatabaseHandler(self.config['database']['path'])

        self.setup_ui()

        # --- モデルの初期化 ---
        self.main_models = {
            'left': MainTableModel(config=self.config, line_filter=['A', 'B']),
            'center': MainTableModel(config=self.config, line_filter=['C', 'D']),
            'right': MainTableModel(config=self.config, line_filter=['E', 'F'])
        }
        self.main_table_view_left.setModel(self.main_models['left'])
        self.main_table_view_center.setModel(self.main_models['center'])
        self.main_table_view_right.setModel(self.main_models['right'])

        self.cleaning_model = CleaningInstructionTableModel(config=self.config, line_filter=None)
        self.cleaning_table_view.setModel(self.cleaning_model)
        
        self.all_models = list(self.main_models.values()) + [self.cleaning_model]
        self.all_table_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right, self.cleaning_table_view]

        self.setup_delegates()
        self.setup_table_columns()

        self.connect_to_db_and_load_data()

        # --- シグナルとスロットの接続 ---
        self.page_button_group.idClicked.connect(self.pages_stack.setCurrentIndex)
        self.date_edit.dateChanged.connect(self.load_data_for_selected_date)
        
        for model in self.all_models:
            model.db_update_signal.connect(self.update_database_record)
            model.data_changed_for_unprocessed_list.connect(self.refresh_unprocessed_list_from_model)

        for view in self.all_table_views:
            view.clicked.connect(self.handle_table_click)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        title_label = QLabel("洗浄依頼管理")
        title_label.setObjectName("mainTitle")

        # --- 上部コントロール ---
        top_controls_layout = QHBoxLayout()
        date_label = QLabel("日付選択:")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        top_controls_layout.addWidget(date_label)
        top_controls_layout.addWidget(self.date_edit)
        top_controls_layout.addStretch()

        # --- ページ切り替えボタン ---
        page_button_layout = QHBoxLayout()
        self.main_page_button = QPushButton("Main")
        self.main_page_button.setCheckable(True)
        self.main_page_button.setProperty("class", "page-button")
        
        self.cleaning_page_button = QPushButton("洗浄指示管理")
        self.cleaning_page_button.setCheckable(True)
        self.cleaning_page_button.setProperty("class", "page-button")

        self.page_button_group = QButtonGroup(self)
        self.page_button_group.addButton(self.main_page_button, 0)
        self.page_button_group.addButton(self.cleaning_page_button, 1)
        self.main_page_button.setChecked(True) # 初期状態

        page_button_layout.addWidget(self.main_page_button)
        page_button_layout.addWidget(self.cleaning_page_button)
        page_button_layout.addStretch()

        # --- ページスタック ---
        self.pages_stack = QStackedWidget()
        self.pages_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mainページ (3分割)
        main_page_widget = QWidget()
        main_page_layout = QHBoxLayout(main_page_widget)
        self.main_table_view_left = QTableView()
        self.main_table_view_center = QTableView()
        self.main_table_view_right = QTableView()
        main_page_layout.addWidget(self.main_table_view_left)
        main_page_layout.addWidget(self.main_table_view_center)
        main_page_layout.addWidget(self.main_table_view_right)
        self.pages_stack.addWidget(main_page_widget)

        # 洗浄指示管理ページ (1つ)
        self.cleaning_table_view = QTableView()
        self.pages_stack.addWidget(self.cleaning_table_view)

        # --- 未払い出し機番テーブル ---
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

        # --- 全体レイアウト ---
        main_layout.addWidget(title_label)
        main_layout.addLayout(top_controls_layout)
        main_layout.addLayout(page_button_layout)
        main_layout.addWidget(self.pages_stack)
        main_layout.addWidget(unprocessed_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

    def setup_table_columns(self):
        # 全ビューのデフォルトをResizeToContentsに設定
        for view in self.all_table_views:
            header = view.horizontalHeader()
            model = view.model()
            if not model: continue
            for i in range(model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Mainページのテーブルの指定された列を固定幅に設定
        main_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right]
        
        # 固定幅にするカラムとその幅
        fixed_width_columns = {
            "part_number": 95,
            "product_name": 95,
            "customer_name": 95,
            "remarks": 90,
        }

        for col_name, width in fixed_width_columns.items():
            try:
                # モデルのヘッダー定義は共通なので、どれか一つからインデックスを取得
                col_index = self.main_models['left']._headers.index(col_name)
                for view in main_views:
                    header = view.horizontalHeader()
                    # 固定サイズモードに設定
                    header.setSectionResizeMode(col_index, QHeaderView.Fixed)
                    # 幅を設定
                    view.setColumnWidth(col_index, width)
            except ValueError:
                pass # カラムが見つからない場合は何もしない

    def setup_delegates(self):
        # Mainテーブルのデリゲート
        try:
            col_index = self.main_models['left']._headers.index("remarks")
            items = self.config.get("remarks_options", ["出荷無し", "1st外観"])
            delegate = EditableComboBoxDelegate(items=items, parent=self)
            self.main_table_view_left.setItemDelegateForColumn(col_index, delegate)
            self.main_table_view_center.setItemDelegateForColumn(col_index, delegate)
            self.main_table_view_right.setItemDelegateForColumn(col_index, delegate)
        except ValueError: pass

        # 洗浄指示管理テーブルのデリゲート
        try:
            col_index = self.cleaning_model._headers.index("cleaning_instruction")
            items = ["", "1", "2", "3", "4"]
            delegate = EditableComboBoxDelegate(items=items, parent=self.cleaning_table_view)
            self.cleaning_table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError: pass

    @Slot(QModelIndex)
    def handle_table_click(self, index):
        if not index.isValid(): return
        sender_view = self.sender()
        model = sender_view.model()
        col_name = model._headers[index.column()]

        if isinstance(model, MainTableModel) and col_name == "remarks":
            sender_view.edit(index)
        elif isinstance(model, CleaningInstructionTableModel) and col_name == "cleaning_instruction":
            sender_view.edit(index)

    @Slot()
    def refresh_unprocessed_list_from_model(self):
        if self.main_models['left']:
            self.update_unprocessed_table(self.main_models['left'].get_all_data())

    @Slot()
    def connect_to_db_and_load_data(self):
        if self.db_handler.connect():
            self.status_label.setText("データベースに接続しました。")
            self.load_data_for_selected_date()
        else:
            self.show_critical_error(f"データベース接続に失敗しました。\nパスを確認してください: {self.config['database']['path']}")

    @Slot()
    def load_data_for_selected_date(self):
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        self.status_label.setText(f"{selected_date} のデータを読み込み中...")

        data, error = self.db_handler.get_data_by_date(selected_date)

        if error:
            for model in self.all_models:
                model.load_data([])
            self.status_label.setText(f"エラー: {error}")
            QMessageBox.warning(self, "データベースエラー", f"データの読み込みに失敗しました。\n\n詳細: {error}")
        else:
            for model in self.all_models:
                model.load_data(data)
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
            self.load_data_for_selected_date()
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