import sys
import sys
import collections
from PySide6.QtWidgets import (
    QMainWindow, QApplication, QWidget, QVBoxLayout, 
    QTableView, QDateEdit, QPushButton,
    QHBoxLayout, QStatusBar, QLabel, QMessageBox, QHeaderView,
    QTableWidget, QTableWidgetItem, QStackedWidget, QButtonGroup, QSizePolicy, QScrollArea,
    QStyle
)
from PySide6.QtCore import QDate, Slot, Qt, QModelIndex, QTimer
from PySide6.QtGui import QShortcut, QKeySequence

from config import load_config
from database import DatabaseHandler
from models import MainTableModel, CleaningInstructionTableModel, EditableComboBoxDelegate, UnprocessedMachineNumbersTableModel, CleaningInstructionDelegate

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

        self.design_config = self.config.get("design", {})

        self.db_handler = DatabaseHandler(self.config['database']['path'])

        # Undo/Redo履歴管理
        self.operation_history = []  # [(record_id, column, old_value, new_value), ...]
        self.undo_stack_pointer = 0  # 現在の位置
        self.max_history_size = 50   # 最大履歴サイズ

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

        # 洗浄指示管理ページ用の単一モデル
        self.cleaning_model = CleaningInstructionTableModel(config=self.config)
        self.cleaning_table_view.setModel(self.cleaning_model)

        self.manufacturing_unprocessed_model = UnprocessedMachineNumbersTableModel(check_column='manufacturing_check', config=self.config)
        self.manufacturing_unprocessed_table_view.setModel(self.manufacturing_unprocessed_model)

        self.cleaning_unprocessed_model = UnprocessedMachineNumbersTableModel(check_column='cleaning_check', config=self.config)
        self.cleaning_unprocessed_table_view.setModel(self.cleaning_unprocessed_model)
        
        self.all_models = list(self.main_models.values()) + [self.cleaning_model]
        self.all_table_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right, self.cleaning_table_view, self.manufacturing_unprocessed_table_view, self.cleaning_unprocessed_table_view]

        for view in self.all_table_views:
            view.setAlternatingRowColors(True);

        self.setup_delegates()
        self.setup_table_columns()

        self.connect_to_db_and_load_data()

        # --- シグナルとスロットの接続 ---
        self.page_button_group.idClicked.connect(self.pages_stack.setCurrentIndex)
        self.page_button_group.idClicked.connect(self.toggle_unprocessed_widget_visibility)
        self.date_edit.dateChanged.connect(self.load_data_for_selected_date)
        self.copy_instructions_button.clicked.connect(self.handle_copy_instructions)
        
        for model in self.all_models:
            model.db_update_signal.connect(self.update_database_record)
            model.data_changed_for_unprocessed_list.connect(self.refresh_unprocessed_list_from_model)

        for view in self.all_table_views:
            view.clicked.connect(self.handle_table_click)

        # Undo/Redoショートカットキーの設定
        self.setup_shortcuts()

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
        self.date_edit.calendarWidget().setStyleSheet("""
            QAbstractItemView:enabled {
                selection-background-color: #0078d7;
                selection-color: white;
            }
        """)
        top_controls_layout.addWidget(date_label)
        top_controls_layout.addWidget(self.date_edit)
        top_controls_layout.addStretch()

        # --- ページ切り替えボタン ---
        self.main_page_button = QPushButton("Main")
        self.main_page_button.setIcon(self.style().standardIcon(QStyle.SP_DirHomeIcon))
        self.main_page_button.setCheckable(True)
        self.main_page_button.setProperty("class", "page-button")
        
        self.cleaning_page_button = QPushButton("洗浄指示管理")
        self.cleaning_page_button.setIcon(self.style().standardIcon(QStyle.SP_FileDialogDetailedView))
        self.cleaning_page_button.setCheckable(True)
        self.cleaning_page_button.setProperty("class", "page-button")

        self.page_button_group = QButtonGroup(self)
        self.page_button_group.addButton(self.main_page_button, 0)
        self.page_button_group.addButton(self.cleaning_page_button, 1)
        self.main_page_button.setChecked(True)

        top_controls_layout.addWidget(self.main_page_button)
        top_controls_layout.addWidget(self.cleaning_page_button)
        top_controls_layout.addStretch()

        # --- 凡例 ---
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
            color_hex = colors_config.get(f"instruction_{num}", "#FFFFFF")
            item_container = QWidget()
            item_layout = QHBoxLayout(item_container)
            item_layout.setContentsMargins(0, 0, 0, 0)
            item_layout.setSpacing(5)
            color_swatch = QLabel()
            color_swatch.setFixedSize(15, 15)
            color_swatch.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #CED4DA; border-radius: 3px;")
            description_label = QLabel(f"{num}: {desc}")
            description_label.setStyleSheet("font-size: 12px; color: #495057;")
            item_layout.addWidget(color_swatch)
            item_layout.addWidget(description_label)
            legend_layout.addWidget(item_container)
        legend_layout.addStretch()
        top_controls_layout.addWidget(legend_widget)
        top_controls_layout.addStretch()

        # --- ページスタック ---
        self.pages_stack = QStackedWidget()
        self.pages_stack.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # Mainページ
        main_page_widget = QWidget()
        main_page_layout = QHBoxLayout(main_page_widget)
        self.main_table_view_left = QTableView()
        self.main_table_view_left.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_left.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_table_view_center = QTableView()
        self.main_table_view_center.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_center.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.main_table_view_right = QTableView()
        self.main_table_view_right.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.main_table_view_right.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        main_page_layout.addWidget(self.main_table_view_left, 0, Qt.AlignTop)
        main_page_layout.addWidget(self.main_table_view_center, 0, Qt.AlignTop)
        main_page_layout.addWidget(self.main_table_view_right, 0, Qt.AlignTop)
        self.pages_stack.addWidget(main_page_widget)

        # 洗浄指示管理ページ
        cleaning_page_widget = QWidget()
        cleaning_page_layout = QVBoxLayout(cleaning_page_widget)
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
        self.copy_instructions_button.setIcon(self.style().standardIcon(QStyle.SP_DialogSaveButton))
        copy_layout.addWidget(self.copy_instructions_button)
        copy_layout.addStretch()
        cleaning_page_layout.addWidget(copy_widget)
        
        # 一括表示用の単一テーブルビュー
        self.cleaning_table_view = QTableView()
        self.cleaning_table_view.setObjectName("cleaning_table_view")
        cleaning_page_layout.addWidget(self.cleaning_table_view)
        self.pages_stack.addWidget(cleaning_page_widget)

        # --- 未払い出し機番テーブル ---
        self.unprocessed_widget = QWidget()
        unprocessed_layout = QHBoxLayout(self.unprocessed_widget)
        # 製造
        manufacturing_unprocessed_container = QWidget()
        manufacturing_unprocessed_layout = QVBoxLayout(manufacturing_unprocessed_container)
        manufacturing_unprocessed_title = QLabel("製造未払い出し機番")
        manufacturing_unprocessed_title.setObjectName("unprocessedTitle")
        manufacturing_unprocessed_title.setFixedHeight(35)
        unprocessed_colors = self.config.get("colors", {})
        manufacturing_title_color = unprocessed_colors.get("unprocessed_manufacturing_bg_color", "#E0F7FA")
        manufacturing_unprocessed_title.setStyleSheet(f"background-color: {manufacturing_title_color}; color: black; padding: 5px; border-radius: 5px;")
        self.manufacturing_unprocessed_table_view = QTableView()
        self.manufacturing_unprocessed_table_view.setObjectName("manufacturingUnprocessedTable")
        self.manufacturing_unprocessed_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.manufacturing_unprocessed_table_view.verticalHeader().setVisible(False)
        self.manufacturing_unprocessed_table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.manufacturing_unprocessed_table_view.horizontalHeader().setMinimumSectionSize(80)
        self.manufacturing_unprocessed_table_view.setMinimumWidth(600)
        self.manufacturing_unprocessed_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.manufacturing_unprocessed_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        manufacturing_unprocessed_layout.addWidget(manufacturing_unprocessed_title)
        manufacturing_unprocessed_layout.addWidget(self.manufacturing_unprocessed_table_view)
        unprocessed_layout.addWidget(manufacturing_unprocessed_container, 0, Qt.AlignTop)
        # 洗浄
        cleaning_unprocessed_container = QWidget()
        cleaning_unprocessed_layout = QVBoxLayout(cleaning_unprocessed_container)
        cleaning_unprocessed_title = QLabel("洗浄未払い出し機番")
        cleaning_unprocessed_title.setObjectName("unprocessedTitle")
        cleaning_unprocessed_title.setFixedHeight(35)
        cleaning_title_color = unprocessed_colors.get("unprocessed_cleaning_bg_color", "#FFF3E0")
        cleaning_unprocessed_title.setStyleSheet(f"background-color: {cleaning_title_color}; color: black; padding: 5px; border-radius: 5px;")
        self.cleaning_unprocessed_table_view = QTableView()
        self.cleaning_unprocessed_table_view.setObjectName("cleaningUnprocessedTable")
        self.cleaning_unprocessed_table_view.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.cleaning_unprocessed_table_view.verticalHeader().setVisible(False)
        self.cleaning_unprocessed_table_view.setEditTriggers(QTableView.NoEditTriggers)
        self.cleaning_unprocessed_table_view.horizontalHeader().setMinimumSectionSize(80)
        self.cleaning_unprocessed_table_view.setMinimumWidth(600)
        self.cleaning_unprocessed_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.cleaning_unprocessed_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cleaning_unprocessed_layout.addWidget(cleaning_unprocessed_title)
        cleaning_unprocessed_layout.addWidget(self.cleaning_unprocessed_table_view)
        unprocessed_layout.addWidget(cleaning_unprocessed_container, 0, Qt.AlignTop)

        # --- 全体レイアウト ---
        main_layout.addLayout(top_controls_layout)
        main_layout.addWidget(self.pages_stack)
        main_layout.addWidget(self.unprocessed_widget)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("準備完了")
        self.status_bar.addWidget(self.status_label)

    def setup_table_columns(self):
        for view in self.all_table_views:
            header = view.horizontalHeader()
            model = view.model()
            if not model: continue
            
            if isinstance(model, UnprocessedMachineNumbersTableModel):
                for i in range(model.columnCount()):
                    view.setColumnWidth(i, 100)
                view.horizontalHeader().setFixedHeight(30)
                continue

            # 洗浄指示管理ページは特別な列幅設定
            if view == self.cleaning_table_view:
                # 最初はすべてコンテンツサイズに設定
                for i in range(model.columnCount()):
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
            else:
                # その他のテーブルはコンテンツサイズに合わせる
                for i in range(model.columnCount()):
                    header.setSectionResizeMode(i, QHeaderView.ResizeToContents)

        # ヘッダーに強調色を設定
        emphasized_header_color = self.design_config.get("highlight_color", "#00BFFF")
        views_for_emphasized_header = [
            self.main_table_view_left, self.main_table_view_center, self.main_table_view_right,
            self.cleaning_table_view
        ]
        for view in views_for_emphasized_header:
            view.horizontalHeader().setStyleSheet(f"QHeaderView::section {{ background-color: {emphasized_header_color}; }}")

        # Mainページの固定幅カラム
        main_views = [self.main_table_view_left, self.main_table_view_center, self.main_table_view_right]
        fixed_width_columns = {
            "part_number": 95, "product_name": 95, "customer_name": 95, "notes": 85,
        }
        for col_name, width in fixed_width_columns.items():
            try:
                col_index = self.main_models['left']._headers.index(col_name)
                for view in main_views:
                    view.horizontalHeader().setSectionResizeMode(col_index, QHeaderView.Fixed)
                    view.setColumnWidth(col_index, width)
            except ValueError: pass

        # 洗浄指示管理ページの列幅設定（余裕を持たせた幅）
        if hasattr(self, 'cleaning_model') and self.cleaning_model:
            cleaning_column_widths = {
                "set_date": 90,           # セット予定日
                "machine_no": 80,         # 機番  
                "customer_name": 120,     # 客先名
                "part_number": 120,       # 品番
                "product_name": 140,      # 製品名
                "next_process": 100,      # 次工程
                "quantity": 70,           # 数量
                "completion_date": 90,    # 加工終了日
                "material_id": 50,        # 識別
                "cleaning_instruction": 80, # 洗浄指示
                "notes": 85,              # 備考（Mainページと同じ固定幅）
            }
            
            for col_name, width in cleaning_column_widths.items():
                try:
                    col_index = self.cleaning_model._headers.index(col_name)
                    if col_name == "notes":
                        # 備考カラムは固定幅
                        self.cleaning_table_view.horizontalHeader().setSectionResizeMode(col_index, QHeaderView.Fixed)
                        self.cleaning_table_view.setColumnWidth(col_index, width)
                    else:
                        # その他のカラムは最小幅を設定して見やすくする
                        self.cleaning_table_view.horizontalHeader().setSectionResizeMode(col_index, QHeaderView.ResizeToContents)
                        self.cleaning_table_view.setColumnWidth(col_index, width)
                        # 最小幅も設定
                        self.cleaning_table_view.horizontalHeader().setMinimumSectionSize(width)
                except ValueError: 
                    pass

    def setup_delegates(self):
        try:
            col_index = self.main_models['left']._headers.index("notes")
            items = self.config.get("notes_options", self.config.get("remarks_options", ["出荷無し", "1st外観"]))
            delegate = EditableComboBoxDelegate(items=items, parent=self)
            self.main_table_view_left.setItemDelegateForColumn(col_index, delegate)
            self.main_table_view_center.setItemDelegateForColumn(col_index, delegate)
            self.main_table_view_right.setItemDelegateForColumn(col_index, delegate)
        except ValueError: pass

        # 洗浄指示管理ページの洗浄指示カラム用デリゲート（ドロップダウン廃止・直接入力）
        try:
            col_index = self.cleaning_model._headers.index("cleaning_instruction")
            
            # 自動移動フラグを初期化
            self.cleaning_table_view.auto_move_enabled = True
            
            # カスタムテーブルビュー機能を追加
            self.cleaning_table_view.move_to_next_cell = self.create_move_to_next_cell_function(self.cleaning_table_view)
            
            delegate = CleaningInstructionDelegate(table_view=self.cleaning_table_view, parent=self.cleaning_table_view)
            self.cleaning_table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError: pass

        # 洗浄指示管理ページの備考カラム用デリゲート
        try:
            col_index = self.cleaning_model._headers.index("notes")
            items = self.config.get("notes_options", self.config.get("remarks_options", ["出荷無し", "1st外観"]))
            delegate = EditableComboBoxDelegate(items=items, parent=self)
            self.cleaning_table_view.setItemDelegateForColumn(col_index, delegate)
        except ValueError: pass

    def create_move_to_next_cell_function(self, table_view):
        """テーブルビュー用の次のセルへ移動する関数を作成"""
        def move_to_next_cell(current_index):
            if not current_index.isValid():
                return
            
            # 自動移動が無効化されている場合は何もしない
            if hasattr(table_view, 'auto_move_enabled') and not table_view.auto_move_enabled:
                return
                
            model = table_view.model()
            current_row = current_index.row()
            current_col = current_index.column()
            
            # 洗浄指示カラムのインデックスを取得
            try:
                cleaning_instruction_col = model._headers.index("cleaning_instruction")
            except (ValueError, AttributeError):
                return
            
            # 洗浄指示カラムでの編集の場合のみ移動
            if current_col == cleaning_instruction_col:
                next_row = current_row + 1
                
                # 次の行が存在する場合
                if next_row < model.rowCount():
                    next_index = model.index(next_row, current_col)
                    table_view.setCurrentIndex(next_index)
                    table_view.scrollTo(next_index)
                    # 少し遅れてから編集状態にする
                    QTimer.singleShot(100, lambda: table_view.edit(next_index))
        
        return move_to_next_cell

    def setup_shortcuts(self):
        """ショートカットキーの設定"""
        # Ctrl+Z: Undo
        self.undo_shortcut = QShortcut(QKeySequence.Undo, self)
        self.undo_shortcut.activated.connect(self.perform_undo)
        
        # Ctrl+Y: Redo
        self.redo_shortcut = QShortcut(QKeySequence.Redo, self)
        self.redo_shortcut.activated.connect(self.perform_redo)

    def add_to_history(self, record_id, column, old_value, new_value):
        """操作履歴を追加"""
        # 現在のポインタ以降の履歴を削除（新しい操作で上書き）
        self.operation_history = self.operation_history[:self.undo_stack_pointer]
        
        # 新しい操作を追加
        operation = {
            'record_id': record_id,
            'column': column,
            'old_value': old_value,
            'new_value': new_value
        }
        self.operation_history.append(operation)
        
        # 最大サイズを超えた場合、古い履歴を削除
        if len(self.operation_history) > self.max_history_size:
            self.operation_history.pop(0)
        else:
            self.undo_stack_pointer += 1
        
        # ポインタを現在の位置に設定
        self.undo_stack_pointer = len(self.operation_history)

    @Slot()
    def perform_undo(self):
        """元に戻す操作（Ctrl+Z）"""
        if self.undo_stack_pointer <= 0:
            self.status_label.setText("元に戻せる操作がありません")
            return
        
        # ポインタを前に移動
        self.undo_stack_pointer -= 1
        operation = self.operation_history[self.undo_stack_pointer]
        
        # 元の値に戻す
        success = self.db_handler.update_record(
            operation['record_id'], 
            operation['column'], 
            operation['old_value']
        )
        
        if success:
            # UIを更新
            self.load_data_for_selected_date()
            self.status_label.setText(f"操作を元に戻しました: {operation['column']}")
        else:
            self.status_label.setText("元に戻す操作に失敗しました")
            # 失敗した場合はポインタを戻す
            self.undo_stack_pointer += 1

    @Slot()
    def perform_redo(self):
        """やり直し操作（Ctrl+Y）"""
        if self.undo_stack_pointer >= len(self.operation_history):
            self.status_label.setText("やり直せる操作がありません")
            return
        
        operation = self.operation_history[self.undo_stack_pointer]
        
        # 新しい値に戻す
        success = self.db_handler.update_record(
            operation['record_id'], 
            operation['column'], 
            operation['new_value']
        )
        
        if success:
            # ポインタを次に移動
            self.undo_stack_pointer += 1
            # UIを更新
            self.load_data_for_selected_date()
            self.status_label.setText(f"操作をやり直しました: {operation['column']}")
        else:
            self.status_label.setText("やり直し操作に失敗しました")

    def _adjust_table_height(self, table_view):
        header_height = table_view.horizontalHeader().height()
        rows_height = sum(table_view.rowHeight(i) for i in range(table_view.model().rowCount()))
        grid_lines_height = (table_view.model().rowCount() - 1) * 1 if table_view.model().rowCount() > 0 else 0
        total_height = header_height + rows_height + grid_lines_height + 2
        table_view.setFixedHeight(total_height)

    @Slot(QModelIndex)
    def handle_table_click(self, index):
        if not index.isValid(): return
        sender_view = self.sender()
        model = sender_view.model()
        col_name = model._headers[index.column()]

        # 洗浄指示管理ページでのクリック処理
        if isinstance(model, CleaningInstructionTableModel):
            # 洗浄指示カラム以外がクリックされた場合、自動移動を無効化
            try:
                cleaning_instruction_col = model._headers.index("cleaning_instruction")
                if index.column() != cleaning_instruction_col:
                    # 自動移動フラグを無効化
                    if hasattr(sender_view, 'auto_move_enabled'):
                        sender_view.auto_move_enabled = False
                else:
                    # 洗浄指示カラムがクリックされた場合、自動移動を有効化
                    if hasattr(sender_view, 'auto_move_enabled'):
                        sender_view.auto_move_enabled = True
            except ValueError:
                pass
            
            # 編集可能なカラムの場合、編集開始
            if col_name in ["cleaning_instruction", "notes"]:
                sender_view.edit(index)
        elif isinstance(model, MainTableModel) and col_name == "notes":
            sender_view.edit(index)

    @Slot(int)
    def toggle_unprocessed_widget_visibility(self, page_id):
        is_visible = (page_id == 0)
        self.unprocessed_widget.setVisible(is_visible)

    @Slot()
    def refresh_unprocessed_list_from_model(self):
        self.load_data_for_selected_date()

    def _refresh_unprocessed_only(self):
        """未処理リストのみを軽量更新するメソッド"""
        selected_date = self.date_edit.date().toString("yyyy-MM-dd")
        data, error = self.db_handler.get_data_by_date(selected_date)
        
        if not error and data:
            # 未処理リストのみ更新（メインテーブルは更新しない）
            self.manufacturing_unprocessed_model.load_data(data)
            self.cleaning_unprocessed_model.load_data(data)
            
            # 未処理リストのテーブルサイズ調整
            self._adjust_table_height(self.manufacturing_unprocessed_table_view)
            self._adjust_table_height(self.cleaning_unprocessed_table_view)
            self.manufacturing_unprocessed_table_view.resizeColumnsToContents()
            self.cleaning_unprocessed_table_view.resizeColumnsToContents()

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
            self.main_models['left'].load_data(data[:20])
            self.main_models['center'].load_data(data[20:40])
            self.main_models['right'].load_data(data[40:])

            # 洗浄指示管理ページは全データを一括表示
            self.cleaning_model.load_data(data)

            self.manufacturing_unprocessed_model.load_data(data)
            self.cleaning_unprocessed_model.load_data(data)

            self.status_label.setText(f"{selected_date} のデータ {len(data)} 件を読み込みました。")

            self._adjust_table_height(self.main_table_view_left)
            self._adjust_table_height(self.main_table_view_center)
            self._adjust_table_height(self.main_table_view_right)
            self._adjust_table_height(self.manufacturing_unprocessed_table_view)
            self._adjust_table_height(self.cleaning_unprocessed_table_view)

            self.manufacturing_unprocessed_table_view.resizeColumnsToContents()
            self.cleaning_unprocessed_table_view.resizeColumnsToContents()
            
            # 洗浄指示管理ページのテーブル列幅を再調整
            if hasattr(self, 'cleaning_table_view'):
                # データ読み込み後に列幅を再設定
                self.cleaning_table_view.resizeColumnsToContents()
                
                # 備考カラムのみ固定幅に再設定
                try:
                    notes_col_index = self.cleaning_model._headers.index("notes")
                    self.cleaning_table_view.horizontalHeader().setSectionResizeMode(notes_col_index, QHeaderView.Fixed)
                    self.cleaning_table_view.setColumnWidth(notes_col_index, 85)
                except (ValueError, AttributeError):
                    pass

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
            QApplication.processEvents()

            success, result = self.db_handler.copy_cleaning_instructions(source_date_str, dest_date_str)

            if success:
                QMessageBox.information(self, "成功", f"{result}件の洗浄指示を複製しました。")
                self.status_label.setText(f"{result}件の洗浄指示を複製しました。")
                if self.date_edit.date() == dest_date:
                    self.load_data_for_selected_date()
            else:
                QMessageBox.critical(self, "エラー", f"処理に失敗しました。\n\n詳細: {result}")
                self.status_label.setText(f"複製に失敗しました: {result}")

    @Slot(int, str, object)
    def update_database_record(self, record_id, column, value):
        # 現在の値を取得（履歴用）
        old_value = self.db_handler.get_record_value(record_id, column)
        
        success = self.db_handler.update_record(record_id, column, value)
        if success:
            # 履歴に追加（old_valueとvalueが異なる場合のみ）
            if old_value != value:
                self.add_to_history(record_id, column, old_value, value)
            
            self.status_label.setText(f"レコード {record_id} の {column} を更新しました。")
            # データベース更新後の全データ再読み込みを軽量化
            # チェックボックス系の更新では未処理リストのみを更新
            if column in ["manufacturing_check", "cleaning_check"]:
                # 未処理リストのみ非同期で更新（重い全データ再読み込みを回避）
                QTimer.singleShot(50, self._refresh_unprocessed_only)
            elif column in ["notes", "cleaning_instruction"]:
                # 備考・洗浄指示更新時は再読み込み不要（すでにモデルに反映済み）
                # 洗浄指示の場合は未処理リストのみ更新
                if column == "cleaning_instruction":
                    QTimer.singleShot(50, self._refresh_unprocessed_only)
            else:
                # その他のカラム更新時のみ全データ再読み込み
                self.load_data_for_selected_date()
        else:
            self.status_label.setText(f"レコード {record_id} の更新に失敗しました。")
            # 失敗時は整合性のため全データ再読み込み
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

    def _generate_stylesheet(self):
        design = self.design_config
        return f"""
        QMainWindow, QWidget {{
            background-color: {design.get("background_color")};
            font-family: {design.get("font_family")};
            color: {design.get("text_color")};
            font-size: {design.get("base_font_size")};
        }}

        #unprocessedTitle {{
            font-size: 18px;
            font-weight: 600;
            color: {design.get("unprocessed_title_color")};
            margin-bottom: 10px;
        }}

        QPushButton {{
            background-color: {design.get("button_background_color")};
            color: {design.get("button_text_color")};
            border: none;
            padding: 12px 22px;
            font-size: 15px;
            font-weight: 600;
            border-radius: 8px;
            min-width: 120px;
        }}
        QPushButton:hover {{
            background-color: {design.get("button_hover_color")};
        }}
        QPushButton:pressed {{
            background-color: {design.get("button_pressed_color")};
        }}

        QPushButton.page-button {{
            background-color: {design.get("page_button_inactive_bg")};
            color: {design.get("page_button_inactive_text")};
            font-weight: 500;
        }}

        QPushButton.page-button:checked {{
            background-color: {design.get("page_button_active_bg")};
            color: {design.get("page_button_active_text")};
            font-weight: 600;
        }}

        QComboBox, QLineEdit, QDateEdit {{
            background-color: {design.get("input_background_color")};
            border: 1px solid {design.get("input_border_color")};
            border-radius: 8px;
            padding: 8px 12px;
            color: {design.get("input_text_color")};
            font-size: 14px;
            min-height: 32px;
        }}
        QComboBox::drop-down, QDateEdit::drop-down {{
            background-color: {design.get("input_background_color")} !important;
            border: none;
            width: 20px;
            subcontrol-origin: padding;
            subcontrol-position: top right;
        }}

        QComboBox::down-arrow {{
            image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 10 10'><polygon points='0,0 10,0 5,10' fill='white'/></svg>");
            background-color: transparent;
        }}
        QComboBox QAbstractItemView {{
            background-color: {design.get("input_background_color")} !important;
            border: 1px solid {design.get("input_border_color")};
            selection-background-color: {design.get("table_selection_background_color")};
            selection-color: {design.get("table_selection_color")};
            color: {design.get("input_text_color")} !important;
            outline: 0px;
            border-radius: 8px;
        }}

        QComboBox QListView {{
            background-color: {design.get("input_background_color")} !important;
            color: {design.get("input_text_color")} !important;
        }}

        QCheckBox {{
            color: {design.get("text_color")};
            spacing: 8px;
            font-size: 14px;
        }}
        QCheckBox::indicator {{
            border: 1px solid {design.get("input_border_color")};
            border-radius: 4px;
            width: 18px;
            height: 18px;
            background-color: {design.get("input_background_color")};
        }}
        QCheckBox::indicator:hover {{
            border: 1px solid {design.get("primary_color")};
        }}
        QCheckBox::indicator:checked {{
            background-color: {design.get("primary_color")};
            border-color: {design.get("primary_color")};
        }}

        QTableView, QTableWidget {{
            background-color: {design.get("background_color")};
            border: 1px solid {design.get("border_color")};
            border-radius: 8px;
            gridline-color: {design.get("border_color")};
            font-size: 14px;
            alternate-background-color: {design.get("table_alternate_row_color")};
            selection-background-color: {design.get("table_selection_background_color")};
            selection-color: {design.get("table_selection_color")};
            outline: 0;
        }}
        QTableView::item, QTableWidget::item {{
            padding: 10px 12px;
            border-bottom: 1px solid {design.get("border_color")};
            color: {design.get("text_color")};
        }}
        QTableView::item:selected, QTableWidget::item:selected {{
            background-color: {design.get("table_selection_background_color")};
            color: {design.get("table_selection_color")};
            border: 1px solid {design.get("input_border_color")};
        }}

        QHeaderView::section {{
            background-color: {design.get("table_header_color")};
            padding: 12px 12px;
            border: none;
            border-bottom: 2px solid {design.get("table_header_color")};
            font-size: 14px;
            font-weight: 600;
            color: {design.get("text_color")};
            text-align: left;
        }}
        QHeaderView::section:last {{
            border-right: none;
        }}

        QStatusBar {{
            font-size: 13px;
            background-color: {design.get("background_color")};
            border-top: 1px solid {design.get("border_color")};
            color: {design.get("text_color")};
            padding: 5px 10px;
        }}
        """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()

    from PySide6.QtGui import QPalette, QColor
    
    design_config = window.design_config

    light_palette = QPalette()
    light_palette.setColor(QPalette.Window, QColor(design_config.get("background_color")))
    light_palette.setColor(QPalette.WindowText, QColor(design_config.get("text_color")))
    light_palette.setColor(QPalette.Base, QColor(design_config.get("input_background_color")))
    light_palette.setColor(QPalette.AlternateBase, QColor(design_config.get("table_alternate_row_color")))
    light_palette.setColor(QPalette.ToolTipBase, QColor(design_config.get("input_background_color")))
    light_palette.setColor(QPalette.ToolTipText, QColor(design_config.get("text_color")))
    light_palette.setColor(QPalette.Text, QColor(design_config.get("text_color")))
    light_palette.setColor(QPalette.BrightText, QColor(design_config.get("highlight_color")))
    light_palette.setColor(QPalette.Link, QColor(design_config.get("primary_color")))
    light_palette.setColor(QPalette.Highlight, QColor(design_config.get("table_selection_background_color")))
    light_palette.setColor(QPalette.HighlightedText, QColor(design_config.get("table_selection_color")))
    
    light_palette.setColor(QPalette.Disabled, QPalette.Text, QColor(design_config.get("secondary_color")))
    light_palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor(design_config.get("secondary_color")))
    light_palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor(design_config.get("secondary_color")))
    
    app.setPalette(light_palette)

    app.setStyleSheet(window._generate_stylesheet())
    window.show()
    sys.exit(app.exec())