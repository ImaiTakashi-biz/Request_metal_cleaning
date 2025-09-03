from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal, QTimer
from PySide6.QtGui import QColor, QFont, QKeyEvent
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox, QLineEdit
import datetime
import collections

class EditableComboBoxDelegate(QStyledItemDelegate):
    """編集可能なQComboBoxをテーブルセル内に表示するためのデリゲート"""
    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.items = items or []

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.setEditable(True)
        # Explicitly set stylesheet for the editor and its dropdown view
        editor.setStyleSheet("""
            QComboBox {
                background-color: white;
                color: black;
                border: 1px solid #CED4DA;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                color: black;
                selection-background-color: #E9ECEF;
                selection-color: #343A40;
                border: 1px solid #CED4DA;
            }
            QComboBox QListView {
                background-color: white;
                color: black;
            }
        """)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        # Noneの場合は空文字列を設定、その他は文字列に変換
        display_value = "" if value is None else str(value)
        editor.setCurrentText(display_value)

    def setModelData(self, editor, model, index):
        text_value = editor.currentText()
        model.setData(index, text_value, Qt.EditRole)
        self.commitData.emit(editor)

class CleaningInstructionDelegate(QStyledItemDelegate):
    """洗浄指示用のカスタムデリゲート（直接入力・下のセルへの自動移動機能付き）"""
    
    def __init__(self, parent=None, table_view=None):
        super().__init__(parent)
        self.table_view = table_view
        
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setStyleSheet("""
            QLineEdit {
                background-color: white;
                color: black;
                border: 1px solid #CED4DA;
                padding: 4px;
            }
        """)
        # 編集開始時に自動移動を有効化
        if self.table_view and hasattr(self.table_view, 'auto_move_enabled'):
            self.table_view.auto_move_enabled = True
        return editor
        
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setText(str(value) if value else "")
        editor.selectAll()  # 既存テキストを選択状態にする
        
    def setModelData(self, editor, model, index):
        text_value = editor.text().strip()
        # 入力値の検証（1-4の数値または空文字のみ許可）
        if text_value == "" or text_value in ["1", "2", "3", "4"]:
            model.setData(index, text_value, Qt.EditRole)
            self.commitData.emit(editor)
            
            # 自動移動が有効で、洗浄指示カラムでの編集の場合のみ移動
            if (self.table_view and 
                hasattr(self.table_view, 'move_to_next_cell') and 
                hasattr(self.table_view, 'auto_move_enabled') and 
                self.table_view.auto_move_enabled):
                
                # 洗浄指示カラムかどうか確認
                try:
                    cleaning_instruction_col = model._headers.index("cleaning_instruction")
                    if index.column() == cleaning_instruction_col:
                        QTimer.singleShot(50, lambda: self.table_view.move_to_next_cell(index))
                except (ValueError, AttributeError):
                    pass
                
    def eventFilter(self, editor, event):
        if isinstance(event, QKeyEvent) and event.type() == QKeyEvent.KeyPress:
            key = event.key()
            text = event.text()
            
            # 数字キー1-4または削除系キーのみ許可
            if text.isdigit() and text in "1234":
                return super().eventFilter(editor, event)
            elif key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_Return, Qt.Key_Enter, Qt.Key_Tab, Qt.Key_Escape):
                return super().eventFilter(editor, event)
            else:
                return True  # その他のキーはブロック
                
        return super().eventFilter(editor, event)

class BaseTableModel(QAbstractTableModel):
    """モデルの共通ロジックを持つベースクラス"""
    db_update_signal = Signal(int, str, object)
    data_changed_for_unprocessed_list = Signal()

    def __init__(self, data=None, config=None, parent=None):
        super().__init__(parent)
        self._data = data or [] # _data will now directly hold the data passed to load_data
        self._config = config or {}
        self._headers = []
        self._display_headers = {}

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            col_name = self._headers[section]
            return self._display_headers.get(col_name, col_name)
        return None

    def load_data(self, data, machine_number_filter=None):
        self.beginResetModel()
        if machine_number_filter:
            # machine_number_filter が指定されている場合、その機番に一致するデータのみをフィルタリング
            self._data = [row for row in data if row.get('machine_no') in machine_number_filter]
        else:
            # machine_number_filter が指定されていない場合、すべてのデータをロード
            self._data = data
        self.endResetModel()

    def get_all_data(self):
        return self._data # Now returns the data currently loaded in the model

    def _is_set_logically(self, row_data):
        set_date_str = row_data.get("set_date")
        acquisition_date_str = row_data.get("acquisition_date")
        if not set_date_str or not acquisition_date_str: return False
        try:
            set_date = datetime.date.fromisoformat(str(set_date_str).split(' ')[0])
            acquisition_date = datetime.date.fromisoformat(str(acquisition_date_str).split(' ')[0])
            delta = datetime.timedelta(days=1)
            logical_yesterday = acquisition_date - delta
            return set_date == logical_yesterday
        except (ValueError, TypeError): return False

class MainTableModel(BaseTableModel):
    """Mainページ用のテーブルモデル"""
    def __init__(self, data=None, config=None, parent=None):
        super().__init__(data, config, parent)
        self._headers = [
            "machine_no",
            "manufacturing_check",
            "cleaning_check",
            "previous_day_set",
            "part_number",
            "product_name",
            "customer_name",
            "notes",
        ]
        self._display_headers = {
            "machine_no": "機番",
            "manufacturing_check": "製造",
            "cleaning_check": "洗浄",
            "previous_day_set": "セット",
            "part_number": "品番",
            "product_name": "品名",
            "customer_name": "客先名",
            "notes": "備考",
        }

    def _is_set_yesterday(self, row_data):
        set_date_str = row_data.get("set_date")
        acquisition_date_str = row_data.get("acquisition_date")
        if not set_date_str or not acquisition_date_str:
            return False
        try:
            set_date = datetime.date.fromisoformat(str(set_date_str).split(' ')[0])
            acquisition_date = datetime.date.fromisoformat(str(acquisition_date_str).split(' ')[0])
            yesterday = acquisition_date - datetime.timedelta(days=1)
            return set_date == yesterday
        except (ValueError, TypeError):
            return False

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row_data = self._data[index.row()]
        col_name = self._headers[index.column()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col_name in ["manufacturing_check", "cleaning_check", "previous_day_set"]:
                return None
            return row_data.get(col_name, "")

        if role == Qt.CheckStateRole:
            if col_name in ["manufacturing_check", "cleaning_check", "previous_day_set"]:
                # セットカラムの場合、カラーリング設定条件（セット日が昨日）でも自動的にTRUEに設定
                if col_name == "previous_day_set":
                    # データベース値をチェックし、カラーリング条件が満たされた場合は自動的にTRUE
                    stored_value = bool(row_data.get(col_name))
                    if self._is_set_yesterday(row_data):
                        return Qt.Checked
                    else:
                        return Qt.Checked if stored_value else Qt.Unchecked
                else:
                    return Qt.Checked if bool(row_data.get(col_name)) else Qt.Unchecked

        if role == Qt.FontRole:
            if col_name == 'machine_no':
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.ForegroundRole:
            # 備考カラムのテキスト色を赤に設定
            if col_name == 'notes':
                return QColor(Qt.red)

        if role == Qt.BackgroundRole:
            # 洗浄チェックがTRUEの場合、機番以外の背景色を薄い紺色に設定
            if bool(row_data.get("cleaning_check")) and col_name != 'machine_no':
                return QColor("#B3C6E7")  # 薄い紺色（テキストが見やすい色）
            if col_name == 'machine_no':
                instruction = str(row_data.get("cleaning_instruction", ""))
                color_map = self._config.get("colors", {})
                color_key = f"instruction_{instruction}"
                if color_key in color_map:
                    color = QColor(color_map[color_key])
                    return color
            
            if col_name == 'previous_day_set':
                if self._is_set_yesterday(row_data):
                    completion_date_str = row_data.get("completion_date")
                    acquisition_date_str = row_data.get("acquisition_date")
                    colors = self._config.get("colors", {})
                    try:
                        acquisition_date = datetime.date.fromisoformat(str(acquisition_date_str).split(' ')[0])
                        if completion_date_str:
                            completion_date = datetime.date.fromisoformat(str(completion_date_str).split(' ')[0])
                            if completion_date == acquisition_date:
                                return QColor(colors.get("set_bg_today", "#0000FF"))  # 青
                    except (ValueError, TypeError):
                        pass
                    return QColor(colors.get("set_bg_other_day", "#FFFF00"))  # 黄色

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid(): return False
        row = index.row()
        col_name = self._headers[index.column()]
        record_id = self._data[row].get("id")
        if record_id is None: return False

        if role == Qt.CheckStateRole and col_name in ["manufacturing_check", "cleaning_check", "previous_day_set"]:
            new_value = bool(value)
            
            # UI更新を即座に実行
            self._data[row][col_name] = new_value
            self.dataChanged.emit(index, index, [role])
            
            # データベース更新を非同期で実行（次のイベントループで実行）
            QTimer.singleShot(0, lambda: self.db_update_signal.emit(record_id, col_name, new_value))
            
            # 未処理リスト更新も少し遅らせて実行（データベース更新の後に実行されるように）
            if col_name in ["manufacturing_check", "cleaning_check"]:
                QTimer.singleShot(10, lambda: self.data_changed_for_unprocessed_list.emit())
            
            return True

        if role == Qt.EditRole and col_name == "notes":
            # 備考欄も同様に非同期化
            self._data[row][col_name] = value
            self.dataChanged.emit(index, index, [role])
            
            # データベース更新を非同期で実行
            QTimer.singleShot(0, lambda: self.db_update_signal.emit(record_id, col_name, value))
            
            return True

        return False

    def flags(self, index):
        base_flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid(): return base_flags
        col_name = self._headers[index.column()]
        if col_name in ["manufacturing_check", "cleaning_check", "previous_day_set"]:
            return base_flags | Qt.ItemIsUserCheckable
        elif col_name == "notes":
            return base_flags | Qt.ItemIsEditable
        return base_flags

class CleaningInstructionTableModel(BaseTableModel):
    """洗浄指示管理ページ用のテーブルモデル"""
    def __init__(self, data=None, config=None, parent=None):
        super().__init__(data, config, parent)
        self._headers = [
            "set_date", "machine_no", "customer_name", "part_number", 
            "product_name", "next_process", "quantity", "completion_date", "material_id", "cleaning_instruction", "notes"
        ]
        self._display_headers = {
            "set_date": "セット予定日",
            "machine_no": "機番",
            "customer_name": "客先名",
            "part_number": "品番",
            "product_name": "製品名",
            "next_process": "次工程",
            "quantity": "数量",
            "completion_date": "加工終了日",
            "material_id": "識別",
            "cleaning_instruction": "洗浄指示",
            "notes": "備考",
        }

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid(): return None
        row_data = self._data[index.row()]
        col_name = self._headers[index.column()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            value = row_data.get(col_name, "")
            if col_name == "cleaning_instruction" and str(value) == "0":
                return ""
            if col_name in ["set_date", "completion_date"] and value:
                return str(value).split(' ')[0]
            return value

        if role == Qt.FontRole:
            if col_name == 'machine_no':
                font = QFont()
                font.setBold(True)
                return font
        
        if role == Qt.BackgroundRole:
            # 優先度1: 機番の背景色（洗浄指示）
            if col_name == 'machine_no':
                instruction = str(row_data.get("cleaning_instruction", ""))
                color_map = self._config.get("colors", {})
                color_key = f"instruction_{instruction}"
                if color_key in color_map:
                    color = QColor(color_map[color_key])
                    return color

            # 優先度2: 材質識別の背景色
            if col_name == 'material_id' and str(row_data.get('material_id')) == '5':
                color_hex = self._config.get("colors", {}).get("material_id_background_yellow", "#FFD54F")
                return QColor(color_hex)

            # 優先度3: セット項目の背景色
            if self._is_set_logically(row_data) and col_name != 'cleaning_instruction':
                color_hex = self._config.get("colors", {}).get("set_background_green", "#81C784")
                return QColor(color_hex)

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role != Qt.EditRole: return False
        row = index.row()
        col_name = self._headers[index.column()]
        record_id = self._data[row].get("id")
        if record_id is None: return False

        if col_name in ["cleaning_instruction", "notes"]:
            # UI更新を即座に実行
            self._data[row][col_name] = value
            self.dataChanged.emit(index, index, [role])
            
            # データベース更新を非同期で実行（次のイベントループで実行）
            QTimer.singleShot(0, lambda: self.db_update_signal.emit(record_id, col_name, value))
            
            # 洗浄指示更新時は未処理リスト更新も少し遅らせて実行
            if col_name == "cleaning_instruction":
                QTimer.singleShot(10, lambda: self.data_changed_for_unprocessed_list.emit())
            
            return True
        return False

    def flags(self, index):
        base_flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid(): return base_flags
        col_name = self._headers[index.column()]
        if col_name in ["cleaning_instruction", "notes"]:
            return base_flags | Qt.ItemIsEditable
        return base_flags

class UnprocessedMachineNumbersTableModel(QAbstractTableModel):
    """未払い出し機番を表示するためのモデル"""
    def __init__(self, check_column, config=None, parent=None):
        super().__init__(parent)
        self._all_data = []
        self._filtered_data = collections.defaultdict(list)
        self._config = config or {}
        self._check_column = check_column # 'manufacturing_check' or 'cleaning_check'
        self._headers = [chr(ord('A') + i) + ' line' for i in range(6)] # A line, B line, ... F line

    def load_data(self, new_data):
        self.beginResetModel()
        self._all_data = new_data
        self._filtered_data = collections.defaultdict(list)
        
        for item in self._all_data:
            # フィルタリングロジック: 指定されたチェックカラムがFalse、かつ洗浄指示が"0"または"空欄"以外であるものを抽出
            if not item.get(self._check_column, False) and str(item.get('cleaning_instruction', '0')) not in ['0', '']:
                machine_no = item.get('machine_no')
                if machine_no and len(machine_no) > 0:
                    line_char = machine_no[0]
                    self._filtered_data[line_char].append(machine_no)
        
        # 各ラインの機番をソート（数値順）
        def natural_sort_key(machine_no):
            """機番を数値順にソートするためのキー関数 (例: D-1, D-2, D-3, D-10)"""
            try:
                # ハイフンで分割して数値部分を取得
                parts = machine_no.split('-')
                if len(parts) >= 2:
                    prefix = parts[0]  # アルファベット部分 (D, A など)
                    number = int(parts[1])  # 数値部分
                    return (prefix, number)
                else:
                    # ハイフンがない場合は文字列としてソート
                    return (machine_no, 0)
            except (ValueError, IndexError):
                # 数値変換に失敗した場合は文字列としてソート
                return (machine_no, 0)
        
        for line_char in self._filtered_data:
            self._filtered_data[line_char].sort(key=natural_sort_key)

        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        # 各ラインの最大行数を取得
        return max((len(v) for v in self._filtered_data.values()), default=0)

    def columnCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        line_char = chr(ord('A') + index.column())
        
        if role == Qt.DisplayRole:
            if index.row() < len(self._filtered_data[line_char]):
                return self._filtered_data[line_char][index.row()]
            return None

        if role == Qt.ForegroundRole:
            return QColor(Qt.black)
        
        if role == Qt.TextAlignmentRole:
            return Qt.AlignCenter
        
        if role == Qt.BackgroundRole:
            colors = self._config.get("colors", {})
            if self._check_column == 'manufacturing_check':
                color_hex = colors.get("unprocessed_manufacturing_bg_color", "#E0F7FA") # Light Cyan
            elif self._check_column == 'cleaning_check':
                color_hex = colors.get("unprocessed_cleaning_bg_color", "#FFF3E0") # Light Orange
            else:
                return None
            return QColor(color_hex)
            
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None
