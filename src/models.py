from PySide6.QtCore import QAbstractTableModel, Qt, QModelIndex, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QStyledItemDelegate, QComboBox
import datetime

class ComboBoxDelegate(QStyledItemDelegate):
    """QComboBoxをテーブルセル内に表示するためのデリゲート"""
    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.items = items or []

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        if value in self.items:
            editor.setCurrentText(str(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class EditableComboBoxDelegate(QStyledItemDelegate):
    """編集可能なQComboBoxをテーブルセル内に表示するためのデリゲート"""
    def __init__(self, parent=None, items=None):
        super().__init__(parent)
        self.items = items or []

    def createEditor(self, parent, option, index):
        editor = QComboBox(parent)
        editor.addItems(self.items)
        editor.setEditable(True)
        return editor

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole)
        editor.setCurrentText(str(value))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)

class CleaningTableModel(QAbstractTableModel):
    db_update_signal = Signal(int, str, object)
    data_changed_for_unprocessed_list = Signal()

    def __init__(self, data=None, config=None, parent=None):
        super().__init__(parent)
        self._data = data or []
        self._config = config or {}
        
        self._headers = [
            "machine_no", 
            "manufacturing_check", 
            "cleaning_check", 
            "前日セット",
            "part_number", 
            "product_name", 
            "customer_name", 
            "next_process", 
            "remarks", 
            "cleaning_instruction",
        ]
        
        self._display_headers = {
            "machine_no": "機番",
            "manufacturing_check": "製造",
            "cleaning_check": "洗浄",
            "前日セット": "セット",
            "part_number": "品番",
            "product_name": "品名",
            "customer_name": "客先名",
            "next_process": "次工程",
            "remarks": "備考",
            "cleaning_instruction": "洗浄指示",
        }
        
        self._hidden_fields = ["set_date", "completion_date", "id", "acquisition_date"]

    def rowCount(self, parent=QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            col_name = self._headers[section]
            return self._display_headers.get(col_name, col_name)
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        row_data = self._data[index.row()]
        col_name = self._headers[index.column()]

        if role == Qt.DisplayRole or role == Qt.EditRole:
            if col_name in ["manufacturing_check", "cleaning_check", "前日セット"]:
                return None
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
                    color.setAlpha(100)
                    return color

            if col_name == "前日セット":
                set_color = self._get_set_checkbox_color(row_data)
                if set_color:
                    return set_color

        return None

    def setData(self, index, value, role=Qt.EditRole):
        if not index.isValid():
            return False

        row = index.row()
        col_name = self._headers[index.column()]
        record_id = self._data[row].get("id")
        if record_id is None: return False

        if role == Qt.CheckStateRole and col_name in ["manufacturing_check", "cleaning_check"]:
            new_value = bool(value)
            self._data[row][col_name] = new_value
            self.db_update_signal.emit(record_id, col_name, new_value)
            self.dataChanged.emit(index, index, [role])
            self.data_changed_for_unprocessed_list.emit() # リアルタイム更新のためにシグナルを発行
            return True
        
        if role == Qt.EditRole and col_name in ["remarks", "cleaning_instruction"]:
            self._data[row][col_name] = value
            self.db_update_signal.emit(record_id, col_name, value)
            self.dataChanged.emit(index, index, [role])
            self.data_changed_for_unprocessed_list.emit() # リアルタイム更新のためにシグナルを発行
            return True

        return False

    def flags(self, index):
        base_flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if not index.isValid():
            return base_flags
        col_name = self._headers[index.column()]
        if col_name in ["manufacturing_check", "cleaning_check"]:
            return base_flags | Qt.ItemIsUserCheckable
        elif col_name in ["remarks", "cleaning_instruction"]:
            return base_flags | Qt.ItemIsEditable
        else:
            return base_flags

    def load_data(self, new_data):
        self.beginResetModel()
        self._data = new_data
        self.endResetModel()

    def _is_set_logically(self, row_data):
        set_date_str = row_data.get("set_date")
        acquisition_date_str = row_data.get("acquisition_date")
        if not set_date_str or not acquisition_date_str: return False
        try:
            set_date = datetime.date.fromisoformat(str(set_date_str).split(' ')[0])
            acquisition_date = datetime.date.fromisoformat(str(acquisition_date_str).split(' ')[0])
            weekday = acquisition_date.weekday()
            if weekday == 6: delta = datetime.timedelta(days=2)
            elif weekday == 0: delta = datetime.timedelta(days=3)
            else: delta = datetime.timedelta(days=1)
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

