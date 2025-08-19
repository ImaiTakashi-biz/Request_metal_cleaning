from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtGui import QColor
import datetime

class CleaningTableModel(QAbstractTableModel):
    db_update_signal = Signal(int, str, object)

    def __init__(self, data=None, config=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._config = config or {}
        # カラム名を「前日セット」に変更し、順序を定義
        self._headers = [
            "machine_no", 
            "manufacturing_check", 
            "cleaning_check", 
            "前日セット", # App-only Field
            "part_number", 
            "product_name", 
            "customer_name", 
            "next_process", 
            "remarks", 
            "cleaning_instruction",
        ]
        self._hidden_fields = ["set_date", "completion_date", "id"] 

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self._headers[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row_data = self._data[index.row()]
        col_name = self._headers[index.column()]

        if role == Qt.DisplayRole:
            if col_name in ["manufacturing_check", "cleaning_check", "前日セット"]:
                return None # チェックボックス列はテキスト非表示
            return row_data.get(col_name, "")

        if role == Qt.CheckStateRole:
            if col_name in ["manufacturing_check", "cleaning_check"]:
                return Qt.Checked if bool(row_data.get(col_name)) else Qt.Unchecked
            if col_name == "前日セット":
                return Qt.Checked if self._is_set_logically(row_data) else Qt.Unchecked
        
        if role == Qt.BackgroundRole:
            if col_name == 'machine_no':
                instruction = str(row_data.get("cleaning_instruction", ""))
                color_map = self._config.get("colors", {})
                color_key = f"instruction_{instruction}"
                if color_key in color_map:
                    color = QColor(color_map[color_key])
                    color.setAlpha(100) # 色を半透明にする (0-255)
                    return color

            if col_name == "前日セット":
                set_color = self._get_set_checkbox_color(row_data)
                if set_color:
                    return set_color # QColorオブジェクトを直接返す

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid() or role not in [Qt.CheckStateRole, Qt.EditRole]:
            return False

        row = index.row()
        col_name = self._headers[index.column()]
        record_id = self._data[row].get("id")
        if record_id is None: return False

        if role == Qt.CheckStateRole and col_name in ["manufacturing_check", "cleaning_check"]:
            new_value = (value == Qt.Checked)
            self._data[row][col_name] = new_value
            self.db_update_signal.emit(record_id, col_name, new_value)
            self.dataChanged.emit(index, index, [role])
            return True
        
        if role == Qt.EditRole and col_name in ["remarks", "cleaning_instruction"]:
            self._data[row][col_name] = value
            self.db_update_signal.emit(record_id, col_name, value)
            self.dataChanged.emit(index, index, [role])
            return True

        return False

    def flags(self, index):
        flags = super().flags(index)
        col_name = self._headers[index.column()]

        # デフォルトですべて編集不可に設定
        flags &= ~Qt.ItemIsEditable

        if col_name in ["manufacturing_check", "cleaning_check"]:
            flags |= Qt.ItemIsUserCheckable
        elif col_name in ["remarks", "cleaning_instruction"]:
            flags |= Qt.ItemIsEditable
        
        return flags

    def load_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def _is_set_logically(self, row_data):
        set_date_str = row_data.get("set_date")
        if not set_date_str: return False
        try:
            set_date = datetime.date.fromisoformat(set_date_str)
            yesterday = datetime.date.today() - datetime.timedelta(days=1)
            return set_date == yesterday
        except (ValueError, TypeError): return False

    def _get_set_checkbox_color(self, row_data):
        if not self._is_set_logically(row_data): return None
        completion_date_str = row_data.get("completion_date")
        colors = self._config.get("colors", {})
        if not completion_date_str: return QColor(colors.get("set_fg_other_day"))
        try:
            completion_date = datetime.date.fromisoformat(completion_date_str)
            today = datetime.date.today()
            return QColor(colors.get("set_fg_today") if completion_date == today else colors.get("set_fg_other_day"))
        except (ValueError, TypeError): return QColor(colors.get("set_fg_other_day"))

