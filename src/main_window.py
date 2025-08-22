import sys
import collections
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QTableView, QDateEdit, QPushButton,
    QHBoxLayout, QStatusBar, QLabel, QMessageBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QStackedWidget, QButtonGroup, QSizePolicy, QScrollArea
)
from PySide6.QtCore import QDate, Slot, Qt, QModelIndex

from config import load_config
from database import DatabaseHandler
from models import MainTableModel, CleaningInstructionTableModel, ComboBoxDelegate, EditableComboBoxDelegate, UnprocessedMachineNumbersTableModel

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
    background-color: white !important;
    border: none;
    width: 20px;
    subcontrol-origin: padding;
    subcontrol-position: top right;
}

QComboBox::down-arrow {
    image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'><polygon points='0,0 10,0 5,10' fill='black'/></svg>");
    background-color: transparent; /* Ensure arrow background is transparent */
}
QComboBox QAbstractItemView {
    background-color: white !important;
    border: 1px solid #CED4DA;
    selection-background-color: #E9ECEF;
    selection-color: #343A40;
    color: black !important; /* Changed to black for visibility */
    outline: 0px;
    border-radius: 8px;
}

QComboBox QListView {
    background-color: white !important;
    color: black !important;
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
    background-color: #E9ECEF; /* Less prominent background */
    color: #343A40;
    border: 1px solid #CED4DA; /* Thinner, less contrasting border */
}

/* Table Header */
QHeaderView::section {
    background-color: #DEE2E6; /* New header background color */
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
        self.setWindowTitle("洗浄依頼管理App")
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
            'left': MainTableModel(config=self.config),
            'center': MainTableModel(config=self.config),
            'right': MainTableModel(config=self.config)
        }
        self.main_table_view_left.setModel(self.main_models['left'])
        self.main_table_view_center.setModel(self.main_models['center'])
        self.main_table_view_right.setModel(self.main_models['right'])

        self.cleaning_model = CleaningInstructionTableModel(config=self.config)
        self.cleaning_table_view.setModel(self.cleaning_model)

        # 未払い出し機番モデルの初期化
        self.manufacturing_unprocessed_model = UnprocessedMachineNumbersTableModel(check_column='manufacturing_check', config=self.config)
        self.manufacturing_unprocessed_table_view.setModel(self.manufacturing_unprocessed_model)

        self.cleaning_unprocessed_model = UnprocessedMachineNumbersTableModel(check_column='cleaning_check', config=self.config)
        self.cleaning_unprocessed_table_view.setModel(self.cleaning_unprocessed_model)
        
        self.all_models = list(self.main_models.values()) + [self.cleaning_model]
        self.all_table_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right, self.cleaning_table_view, self.manufacturing_unprocessed_table_view, self.cleaning_unprocessed_table_view]

        # 全てのテーブルに交互の背景色を有効にする
        for view in self.all_table_views:
            view.setAlternatingRowColors(True)

        self.setup_delegates()
        self.setup_table_columns()

        self.connect_to_db_and_load_data()

        # --- シグナルとスロットの接続 ---
        self.page_button_group.idClicked.connect(self.pages_stack.setCurrentIndex)
        self.date_edit.dateChanged.connect(self.load_data_for_selected_date)
        self.copy_instructions_button.clicked.connect(self.handle_copy_instructions)
        
        for model in self.all_models:
            model.db_update_signal.connect(self.update_database_record)
            model.data_changed_for_unprocessed_list.connect(self.refresh_unprocessed_list_from_model)

        for view in self.all_table_views:
            view.clicked.connect(self.handle_table_click)

    def setup_ui(self):
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(central_widget)
        self.setCentralWidget(scroll_area)

        # --- 上部コントロール ---
        top_controls_layout = QHBoxLayout()
        date_label = QLabel("日付選択:")
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        top_controls_layout.addWidget(date_label)
        top_controls_layout.addWidget(self.date_edit)
        top_controls_layout.addStretch()

        # --- ページ切り替えボタンを上部コントロールに移動 ---
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

        top_controls_layout.addWidget(self.main_page_button)
        top_controls_layout.addWidget(self.cleaning_page_button)
        top_controls_layout.addStretch() # ページボタンと凡例の間にスペースを追加

        # 洗浄指示の凡例を追加
        legend_widget = QWidget()
        legend_layout = QHBoxLayout(legend_widget)
        legend_layout.setContentsMargins(0, 0, 0, 0)
        legend_layout.setSpacing(10)

        instructions_data = [
            ("1", "急ぎ・当日出荷（AM10：30までに洗浄）"),
            ("2", "近日中に出荷（AM中に洗浄）"),
            ("3", "通常品(当日中に洗浄）"),
            ("4", "サビ注意品・別途指示品"),
        ]

        colors_config = self.config.get("colors", {})

        for num, desc in instructions_data:
            color_hex = colors_config.get(f"instruction_{num}", "#FFFFFF") # configから色を取得

            item_container = QWidget()
            item_layout = QHBoxLayout(item_container)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)

            color_swatch = QLabel()
            color_swatch.setFixedSize(15, 15) # 色見本のサイズ
            color_swatch.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #CED4DA; border-radius: 3px;")

            description_label = QLabel(desc)
            description_label.setStyleSheet("font-size: 12px; color: #495057;") # 説明文のスタイル

            item_layout.addWidget(color_swatch)
            item_layout.addWidget(description_label)

            legend_layout.addWidget(item_container)
        
        legend_layout.addStretch() # 凡例の項目を左寄せにする
        top_controls_layout.addWidget(legend_widget)

        top_controls_layout.addStretch() # 右端に寄せるため

        # --- ページスタック ---
        self.pages_stack = QStackedWidget()
        self.pages_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mainページ (3分割)
        main_page_widget = QWidget()
        main_page_layout = QHBoxLayout(main_page_widget)
        self.main_table_view_left = QTableView()
        self.main_table_view_left.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_left.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_center = QTableView()
        self.main_table_view_center.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_center.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_right = QTableView()
        self.main_table_view_right.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_right.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        main_page_layout.addWidget(self.main_table_view_left, 0, Qt.AlignTop)
        main_page_layout.addWidget(self.main_table_view_center, 0, Qt.AlignTop)
        main_page_layout.addWidget(self.main_table_view_right, 0, Qt.AlignTop)
        self.pages_stack.addWidget(main_page_widget)

        # 洗浄指示管理ページ
        cleaning_page_widget = QWidget()
        cleaning_page_layout = QVBoxLayout(cleaning_page_widget)

        # --- コピー機能UI ---
        copy_widget = QWidget()
        copy_layout = QHBoxLayout(copy_widget)
        copy_layout.setContentsMargins(0, 0, 0, 0)
        copy_layout.addWidget(QLabel("コピー元日付:"))
        self.source_date_edit = QDateEdit(QDate.currentDate())
        self.source_date_edit.setCalendarPopup(True)
        copy_layout.addWidget(self.source_date_edit)
        copy_layout.addWidget(QLabel("  コピー先日付:"))
        self.destination_date_edit = QDateEdit(QDate.currentDate())
        self.destination_date_edit.setCalendarPopup(True)
        copy_layout.addWidget(self.destination_date_edit)
        self.copy_instructions_button = QPushButton("洗浄指示を複製")
        copy_layout.addWidget(self.copy_instructions_button)
        copy_layout.addStretch()
        
        cleaning_page_layout.addWidget(copy_widget)

        # --- テーブル ---
        self.cleaning_table_view = QTableView()
        cleaning_page_layout.addWidget(self.cleaning_table_view)

        self.pages_stack.addWidget(cleaning_page_widget)

        # --- 未払い出し機番テーブル ---
        unprocessed_widget = QWidget()
        unprocessed_layout = QHBoxLayout(unprocessed_widget) # Changed to QHBoxLayout

        # 製造未払い出し機番テーブル (左側)
        manufacturing_unprocessed_container = QWidget()
        manufacturing_unprocessed_layout = QVBoxLayout(manufacturing_unprocessed_container)
        manufacturing_unprocessed_title = QLabel("製造未払い出し機番")
        manufacturing_unprocessed_title.setObjectName("unprocessedTitle")
        manufacturing_unprocessed_title.setFixedHeight(35) # 固定高さに設定
        # タイトルに背景色を適用
        unprocessed_colors = self.config.get("colors", {})
        manufacturing_title_color = unprocessed_colors.get("unprocessed_manufacturing_bg_color", "#E0F7FA")
        manufacturing_unprocessed_title.setStyleSheet(f"background-color: {manufacturing_title_color}; color: black; padding: 5px; border-radius: 5px;")
        self.manufacturing_unprocessed_table_view = QTableView()
        self.manufacturing_unprocessed_table_view.setFixedHeight(250) # 固定高さに設定
        self.manufacturing_unprocessed_table_view.setObjectName("manufacturingUnprocessedTable")
        self.manufacturing_unprocessed_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.manufacturing_unprocessed_table_view.verticalHeader().setVisible(False)
        self.manufacturing_unprocessed_table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.manufacturing_unprocessed_table_view.horizontalHeader().setMinimumSectionSize(80) # Set minimum column width
        self.manufacturing_unprocessed_table_view.setMinimumWidth(600) # Added minimum width to ensure space for all 6 columns
        self.manufacturing_unprocessed_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.manufacturing_unprocessed_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        manufacturing_unprocessed_layout.addWidget(manufacturing_unprocessed_title)
        manufacturing_unprocessed_layout.addWidget(self.manufacturing_unprocessed_table_view)
        unprocessed_layout.addWidget(manufacturing_unprocessed_container)

        # 洗浄未払い出し機番テーブル (右側)
        cleaning_unprocessed_container = QWidget()
        cleaning_unprocessed_layout = QVBoxLayout(cleaning_unprocessed_container)
        cleaning_unprocessed_title = QLabel("洗浄未払い出し機番")
        cleaning_unprocessed_title.setObjectName("unprocessedTitle")
        cleaning_unprocessed_title.setFixedHeight(35) # 固定高さに設定
        # タイトルに背景色を適用
        cleaning_title_color = unprocessed_colors.get("unprocessed_cleaning_bg_color", "#FFF3E0")
        cleaning_unprocessed_title.setStyleSheet(f"background-color: {cleaning_title_color}; color: black; padding: 5px; border-radius: 5px;")
        self.cleaning_unprocessed_table_view = QTableView()
        self.cleaning_unprocessed_table_view.setFixedHeight(250) # 固定高さに設定
        self.cleaning_unprocessed_table_view.setObjectName("cleaningUnprocessedTable")
        self.cleaning_unprocessed_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cleaning_unprocessed_table_view.verticalHeader().setVisible(False)
        self.cleaning_unprocessed_table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.cleaning_unprocessed_table_view.horizontalHeader().setMinimumSectionSize(80) # Set minimum column width
        self.cleaning_unprocessed_table_view.setMinimumWidth(600) # Added minimum width to ensure space for all 6 columns
        self.cleaning_unprocessed_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cleaning_unprocessed_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cleaning_unprocessed_layout.addWidget(cleaning_unprocessed_title)
        cleaning_unprocessed_layout.addWidget(self.cleaning_unprocessed_table_view)
        unprocessed_layout.addWidget(cleaning_unprocessed_container)

        # --- 全体レイアウト ---
        main_layout.addLayout(top_controls_layout)
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
            
            # 未払い出し機番テーブルの列幅設定
            if isinstance(model, UnprocessedMachineNumbersTableModel):
                for i in range(model.columnCount()):
                    view.setColumnWidth(i, 100) # Explicitly set fixed width for all columns
                view.horizontalHeader().setFixedHeight(30) # ヘッダーの高さ固定
                continue # 未払い出し機番テーブルはこれ以上設定しない

            for i in range(model.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # Mainページと洗浄指示管理ページのヘッダーに強調色を設定
        emphasized_header_color = "#8DAAE0" # 強調したい背景色

        # Mainページのテーブル
        main_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right]
        for view in main_views:
            view.horizontalHeader().setStyleSheet(f"QHeaderView::section {{ background-color: {emphasized_header_color}; }}")

        # 洗浄指示管理ページのテーブル
        self.cleaning_table_view.horizontalHeader().setStyleSheet(f"QHeaderView::section {{ background-color: {emphasized_header_color}; }}")

        # Mainページのテーブルの指定された列を固定幅に設定
        main_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right]
        
        # 固定幅にするカラムとその幅
        fixed_width_columns = {
            "part_number": 95,
            "product_name": 95,
            "customer_name": 95,
            "remarks": 85,
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

    def adjust_main_table_height(self, table_view):
        # ヘッダーの高さ
        header_height = table_view.horizontalHeader().height()
        # 各行の高さの合計
        rows_height = sum(table_view.rowHeight(i) for i in range(table_view.model().rowCount()))
        # グリッド線の高さ (行数 - 1) * グリッド線幅 (仮に1px)
        grid_lines_height = (table_view.model().rowCount() - 1) * 1 if table_view.model().rowCount() > 0 else 0
        # 合計高さ
        total_height = header_height + rows_height + grid_lines_height + 2 # +2 for border/padding
        table_view.setFixedHeight(total_height)

    def adjust_unprocessed_table_height(self, table_view):
        # ヘッダーの高さ
        header_height = table_view.horizontalHeader().height()
        # 各行の高さの合計
        rows_height = sum(table_view.rowHeight(i) for i in range(table_view.model().rowCount()))
        # グリッド線の高さ (行数 - 1) * グリッド線幅 (仮に1px)
        grid_lines_height = (table_view.model().rowCount() - 1) * 1 if table_view.model().rowCount() > 0 else 0
        # 合計高さ
        total_height = header_height + rows_height + grid_lines_height + 2 # +2 for border/padding
        table_view.setFixedHeight(total_height)

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
        # 全てのデータを再ロードして、未払い出しリストを更新
        self.load_data_for_selected_date()

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
            # Mainテーブルのデータスライスとロード
            left_data = data[:20]
            center_data = data[20:40]
            right_data = data[40:]

            self.main_models['left'].load_data(left_data)
            self.main_models['center'].load_data(center_data)
            self.main_models['right'].load_data(right_data)

            # 洗浄指示管理テーブルのロード
            self.cleaning_model.load_data(data)

            # 未払い出し機番テーブルのロード
            self.manufacturing_unprocessed_model.load_data(data)
            self.cleaning_unprocessed_model.load_data(data)

            self.status_label.setText(f"{selected_date} のデータ {len(data)} 件を読み込みました。")

            # メインテーブルの高さ調整
            self.adjust_main_table_height(self.main_table_view_left)
            self.adjust_main_table_height(self.main_table_view_center)
            self.adjust_main_table_height(self.main_table_view_right)

            self.manufacturing_unprocessed_table_view.resizeColumnsToContents()
            self.cleaning_unprocessed_table_view.resizeColumnsToContents()

    @Slot()
    def handle_copy_instructions(self):
        source_date = self.source_date_edit.date()
        dest_date = self.destination_date_edit.date()

        if source_date == dest_date:
            QMessageBox.warning(self, "日付エラー", "コピー元とコピー先の日付が同じです。")
            return

        source_date_str = source_date.toString("yyyy-MM-dd")
        dest_date_str = dest_date.toString("yyyy-MM-dd")

        reply = QMessageBox.question(self, "実行確認",
                                     f"{source_date_str} の洗浄指示を、\n"
                                     f"{dest_date_str} のデータに複製します。\n"
                                     f"（同じ機番の洗浄指示が上書きされます）\n\n"
                                     f"よろしいですか？",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.status_label.setText("洗浄指示を複製中...")
            QApplication.processEvents() # UIの更新を強制

            success, result = self.db_handler.copy_cleaning_instructions(source_date_str, dest_date_str)

            if success:
                QMessageBox.information(self, "成功", f"{result}件の洗浄指示を複製しました。")
                self.status_label.setText(f"{result}件の洗浄指示を複製しました。")
                # 現在表示中の日付がコピー先の日付だったら、UIを即時更新
                if self.date_edit.date() == dest_date:
                    self.load_data_for_selected_date()
            else:
                QMessageBox.critical(self, "エラー", f"処理に失敗しました。\n\n詳細: {result}")
                self.status_label.setText(f"複製に失敗しました: {result}")

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

    # Create and set a light palette to override system dark mode
    from PySide6.QtGui import QPalette, QColor
    
    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, QColor("#F0F0F0"))
    light_palette.setColor(QPalette.WindowText, Qt.black)
    light_palette.setColor(QPalette.Base, Qt.white)
    light_palette.setColor(QPalette.AlternateBase, QColor("#F0F0F0"))
    light_palette.setColor(QPalette.ToolTipBase, Qt.white)
    light_palette.setColor(QPalette.ToolTipText, Qt.black)
    light_palette.setColor(QPalette.Text, Qt.black)
    light_palette.setColor(QPalette.Button, QColor("#F0F0F0"))
    light_palette.setColor(QPalette.ButtonText, Qt.black)
    light_palette.setColor(QPalette.BrightText, Qt.red)
    light_palette.setColor(QPalette.Link, QColor(0, 0, 255))
    light_palette.setColor(QPalette.Highlight, QColor(0, 120, 215))
    light_palette.setColor(QPalette.HighlightedText, Qt.white)
    
    # Set colors for disabled state
    light_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(127, 127, 127))
    light_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(127, 127, 127))
    light_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(127, 127, 127))
    
    app.setPalette(light_palette)

    app.setStyleSheet(FINAL_STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
