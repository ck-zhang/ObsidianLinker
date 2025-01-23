import sys
import os
import re
import json
import shutil
import tempfile
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QCheckBox,
    QProgressBar,
    QTabWidget,
    QInputDialog,
)
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QProcess


class EntityLinkerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Entity Linker")
        self.resize(800, 600)
        self.entities = []
        self.notes_folder = ""
        self.output_json = ""
        self.default_db_file = "entities.json"
        self.data = {}
        self.init_ui()

    def init_ui(self):
        self.tabs = QTabWidget()
        self.extract_tab = QWidget()
        self.link_tab = QWidget()
        self.tabs.addTab(self.extract_tab, "Extract")
        self.tabs.addTab(self.link_tab, "Link")
        self.init_extract_tab()
        self.init_link_tab()
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        self.setLayout(main_layout)

    def init_extract_tab(self):
        notes_folder_label = QLabel("Notes Folder:")
        self.notes_folder_edit = QLineEdit()
        notes_folder_button = QPushButton("Browse")
        notes_folder_button.clicked.connect(self.browse_notes_folder)
        notes_folder_layout = QHBoxLayout()
        notes_folder_layout.addWidget(notes_folder_label)
        notes_folder_layout.addWidget(self.notes_folder_edit)
        notes_folder_layout.addWidget(notes_folder_button)
        output_json_label = QLabel("Output JSON File:")
        self.output_json_edit = QLineEdit(self.default_db_file)
        output_json_button = QPushButton("Browse")
        output_json_button.clicked.connect(self.browse_output_json)
        output_json_layout = QHBoxLayout()
        output_json_layout.addWidget(output_json_label)
        output_json_layout.addWidget(self.output_json_edit)
        output_json_layout.addWidget(output_json_button)
        extract_button = QPushButton("Extract Entities")
        extract_button.clicked.connect(self.extract_entities)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        extract_layout = QVBoxLayout()
        extract_layout.addLayout(notes_folder_layout)
        extract_layout.addLayout(output_json_layout)
        extract_layout.addWidget(extract_button)
        extract_layout.addWidget(self.progress_bar)
        self.extract_tab.setLayout(extract_layout)

    def init_link_tab(self):
        link_output_json_label = QLabel("Entities JSON File:")
        self.link_output_json_edit = QLineEdit(self.default_db_file)
        link_output_json_button = QPushButton("Browse")
        link_output_json_button.clicked.connect(self.browse_link_output_json)
        link_output_json_layout = QHBoxLayout()
        link_output_json_layout.addWidget(link_output_json_label)
        link_output_json_layout.addWidget(self.link_output_json_edit)
        link_output_json_layout.addWidget(link_output_json_button)
        load_entities_button = QPushButton("Load Entities")
        load_entities_button.clicked.connect(self.load_entities)
        entities_label = QLabel("Entities:")
        self.entities_list = QListWidget()
        self.entities_list.setSelectionMode(QListWidget.MultiSelection)
        self.entities_list.itemSelectionChanged.connect(self.entities_selected)
        occurrences_label = QLabel("Occurrences:")
        self.occurrences_list = QListWidget()
        self.occurrences_list.setFixedHeight(200)
        add_links_button = QPushButton("Add Links to Selected Occurrences")
        add_links_button.clicked.connect(self.add_links)
        link_layout = QVBoxLayout()
        link_layout.addLayout(link_output_json_layout)
        link_layout.addWidget(load_entities_button)
        link_layout.addWidget(entities_label)
        link_layout.addWidget(self.entities_list)
        link_layout.addWidget(occurrences_label)
        link_layout.addWidget(self.occurrences_list)
        link_layout.addWidget(add_links_button)
        self.link_tab.setLayout(link_layout)

    def browse_notes_folder(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Notes Folder")
        if directory:
            self.notes_folder_edit.setText(directory)

    def browse_output_json(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Select Output JSON File", self.default_db_file, "JSON Files (*.json)"
        )
        if file_name:
            self.output_json_edit.setText(file_name)

    def browse_link_output_json(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Select Entities JSON File",
            self.default_db_file,
            "JSON Files (*.json)",
        )
        if file_name:
            self.link_output_json_edit.setText(file_name)

    def extract_entities(self):
        self.notes_folder = self.notes_folder_edit.text()
        self.output_json = self.output_json_edit.text()
        if not self.notes_folder or not self.output_json:
            QMessageBox.warning(
                self,
                "Warning",
                "Please select both the notes folder and output JSON file.",
            )
            return
        if not os.path.isdir(self.notes_folder):
            QMessageBox.warning(
                self, "Warning", "The selected notes folder does not exist."
            )
            return
        self.notes_folder = os.path.abspath(self.notes_folder)
        self.output_json = os.path.abspath(self.output_json)
        self.entities_list.clear()
        self.occurrences_list.clear()
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Extracting entities... 0%")
        self.worker = EntityExtractionWorker(self.notes_folder, self.output_json)
        self.worker.progress.connect(self.update_progress_bar)
        self.worker.finished.connect(self.extraction_finished)
        self.worker.error.connect(self.extraction_error)
        self.worker.start()

    def update_progress_bar(self, value):
        self.progress_bar.setValue(value)
        self.progress_bar.setFormat(f"Extracting entities... {value}%")

    def extraction_finished(self):
        self.progress_bar.setVisible(False)
        self.link_output_json_edit.setText(self.output_json)
        self.load_entities()
        self.tabs.setCurrentWidget(self.link_tab)

    def extraction_error(self, error_message):
        self.progress_bar.setVisible(False)
        QMessageBox.critical(self, "Extraction Error", error_message)

    def load_entities(self):
        self.output_json = self.link_output_json_edit.text()
        if not self.output_json or not os.path.exists(self.output_json):
            QMessageBox.warning(
                self, "Warning", f"The JSON file '{self.output_json}' does not exist."
            )
            return
        with open(self.output_json, "r", encoding="utf-8") as f:
            self.data = json.load(f)
        self.entities = self.data.get("entities", [])
        self.display_entities()

    def display_entities(self):
        self.entities_list.clear()
        for entity in self.entities:
            t = f"{entity['word']} (Group: {entity.get('entity_group', '')}, Score: {entity.get('score', 0):.2f})"
            item = QListWidgetItem(t)
            item.setData(Qt.UserRole, entity)
            self.entities_list.addItem(item)
        self.occurrences_list.clear()

    def entities_selected(self):
        selected_items = self.entities_list.selectedItems()
        self.display_occurrences(selected_items)

    def display_occurrences(self, selected_entity_items):
        self.occurrences_list.clear()
        self.selected_entities = []
        for item in selected_entity_items:
            entity = item.data(Qt.UserRole)
            self.selected_entities.append(entity)
            for occ in entity["occurrences"]:
                c = QCheckBox(
                    f"Entity: {entity['word']}, File: {occ['file']}, Text: '{occ['word']}'"
                )
                c.setChecked(True)
                li = QListWidgetItem()
                li.setSizeHint(c.sizeHint())
                li.setData(Qt.UserRole, (entity, occ))
                self.occurrences_list.addItem(li)
                self.occurrences_list.setItemWidget(li, c)

    def add_links(self):
        selected_occurrences = []
        for i in range(self.occurrences_list.count()):
            li = self.occurrences_list.item(i)
            c = self.occurrences_list.itemWidget(li)
            if c.isChecked():
                e, o = li.data(Qt.UserRole)
                selected_occurrences.append((e, o))
        if not selected_occurrences:
            QMessageBox.information(self, "Information", "No occurrences selected.")
            return
        use_custom_name = QMessageBox.question(
            self,
            "Custom Link Name",
            "Do you want to specify a custom link target name?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        custom_name_map = {}
        if use_custom_name == QMessageBox.Yes:
            s = set(e["word"] for e, occ in selected_occurrences)
            for w in s:
                text, ok = QInputDialog.getText(
                    self,
                    "Custom Link Name",
                    f"Enter the custom link name for '{w}':",
                    QLineEdit.Normal,
                    w,
                )
                if ok and text:
                    custom_name_map[w] = text
                else:
                    custom_name_map[w] = w
        else:
            for e, occ in selected_occurrences:
                custom_name_map[e["word"]] = e["word"]
        self.add_links_directly(selected_occurrences, custom_name_map)
        QMessageBox.information(self, "Information", "Links added successfully.")

    def add_links_directly(self, selected_occurrences, custom_name_map):
        store = {}
        for e, occ in selected_occurrences:
            fp = occ["file"]
            if fp not in store:
                store[fp] = []
            store[fp].append((e, occ))
        for fp, occs in store.items():
            if not os.path.isfile(fp):
                continue
            with open(fp, "r", encoding="utf-8") as f:
                text = f.read()
            positions = []
            for e, o in occs:
                positions.append((o["start"], o["end"], e, o))
            positions.sort(key=lambda x: x[0])
            new_text = ""
            last_idx = 0
            for start, end, e, o in positions:
                if start < last_idx:
                    continue
                if not self.is_plain_text(text, start):
                    continue
                word_in_text = text[start:end]
                if word_in_text != o["word"]:
                    continue
                link_text = (
                    f"[[{custom_name_map[e['word']]}]]"
                    if custom_name_map[e["word"]] == o["word"]
                    else f"[[{custom_name_map[e['word']]}|{o['word']}]]"
                )
                new_text += text[last_idx:start] + link_text
                last_idx = end
            new_text += text[last_idx:]
            with open(fp, "w", encoding="utf-8") as f:
                f.write(new_text)
        self.save_entities()

    def is_plain_text(self, text, position):
        heading_pattern = re.compile(r"^#+\s.*$", re.MULTILINE)
        code_block_pattern = re.compile(r"```.*?```", re.DOTALL)
        link_pattern = re.compile(r"\[.*?\]\(.*?\)")
        obsidian_link_pattern = re.compile(r"\[\[.*?\]\]")
        comment_pattern = re.compile(r"<!--.*?-->", re.DOTALL)
        patterns = [
            heading_pattern,
            code_block_pattern,
            link_pattern,
            obsidian_link_pattern,
            comment_pattern,
        ]
        for pattern in patterns:
            for m in pattern.finditer(text):
                if m.start() <= position < m.end():
                    return False
        return True

    def save_entities(self):
        self.data["entities"] = self.entities
        with open(self.output_json, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)


class EntityExtractionWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, notes_folder, output_json):
        super().__init__()
        self.notes_folder = notes_folder
        self.output_json = output_json
        self.process = None

    def start(self):
        script_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "extract_entities.py"
        )
        args = [
            script_path,
            "--notes_folder",
            self.notes_folder,
            "--output_json",
            self.output_json,
        ]
        self.process = QProcess()
        self.process.setProgram(sys.executable)
        self.process.setArguments(args)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = data.data().decode()
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("PROGRESS:"):
                try:
                    value = int(line.split(":")[1].strip())
                    self.progress.emit(value)
                except ValueError:
                    pass
            else:
                print(line)

    def handle_stderr(self):
        data = self.process.readAllStandardError()
        stderr = data.data().decode()
        print(stderr)

    def process_finished(self, exit_code, exit_status):
        if exit_code != 0:
            e = f"Extraction process failed with exit code {exit_code}"
            self.error.emit(e)
        else:
            self.finished.emit()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = EntityLinkerApp()
    window.show()
    sys.exit(app.exec_())
