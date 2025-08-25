from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox
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
        editor.setCurrentText(str(value))

    def setModelData(self, editor, model, index):
        text_value = editor.currentText()
        model.setData(index, text_value, Qt.EditRole)
        self.commitData.emit(editor)

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

    def _get_set_checkbox_color(self, row_data):
        if not self._is_set_logically(row_data): return None
        completion_date_str = row_data.get("completion_date")
        acquisition_date_str = row_data.get("acquisition_date")
        colors = self._config.get("colors", {})
        try:
            acquisition_date = datetime.date.fromisoformat(str(acquisition_date_str).split(' ')[0])
            if not completion_date_str:
                return QColor(colors.get("set_fg_other_day", "#FFFF00"))
            completion_date = datetime.date.fromisoformat(str(completion_date_str).split(' ')[0])
            if completion_date == acquisition_date:
                return QColor(colors.get("set_fg_today", "#0000FF"))
            else:
                return QColor(colors.get("set_fg_other_day", "#FFFF00"))
        except (ValueError, TypeError):
            return QColor(colors.get("set_fg_other_day", "#FFFF00"))

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
                return Qt.Checked if bool(row_data.get(col_name)) else Qt.Unchecked

        if role == Qt.FontRole:
            if col_name == 'machine_no':
                font = QFont()
                font.setBold(True)
                return font

        if role == Qt.BackgroundRole:
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
            self._data[row][col_name] = new_value
            self.db_update_signal.emit(record_id, col_name, new_value)
            self.dataChanged.emit(index, index, [role])
            if col_name in ["manufacturing_check", "cleaning_check"]:
                self.data_changed_for_unprocessed_list.emit()
            return True

        if role == Qt.EditRole and col_name == "notes":
            self._data[row][col_name] = value
            self.db_update_signal.emit(record_id, col_name, value)
            self.dataChanged.emit(index, index, [role])
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
            "product_name", "next_process", "quantity", "completion_date", "material_id", "cleaning_instruction"
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

        if col_name == "cleaning_instruction":
            self._data[row][col_name] = value
            self.db_update_signal.emit(record_id, col_name, value)
            self.dataChanged.emit(index, index, [role])
            self.data_changed_for_unprocessed_list.emit()
            return True
        return False

    def flags(self, index):
        base_flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid(): return base_flags
        col_name = self._headers[index.column()]
        if col_name == "cleaning_instruction":
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
        
        # 各ラインの機番をソート
        for line_char in self._filtered_data:
            self._filtered_data[line_char].sort()

        print(f"UnprocessedModel ({self._check_column}) filtered data: {self._filtered_data}") # Debug print

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
