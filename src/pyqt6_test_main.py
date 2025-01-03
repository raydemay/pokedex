import sys
import sqlite3
import os

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QComboBox,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import Qt


class PokedexApp(QMainWindow):
    def __init__(self):
        super().__init__()
        db_path = os.path.join("..", "database", "pokedex.db")
        self.setWindowTitle("Pokédex")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.pokemon_names = self.get_pokemon_names()
        self.selected_index = 0
        self.setup_ui()
        self.bind_keys()

    def setup_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        self.name_label = QLabel("Select a Pokémon:")
        layout.addWidget(self.name_label)

        self.pokemon_combobox = QComboBox()
        self.pokemon_combobox.addItems(self.pokemon_names)
        self.pokemon_combobox.currentIndexChanged.connect(self.display_pokemon_info)
        layout.addWidget(self.pokemon_combobox)

        self.image_label = QLabel()
        layout.addWidget(self.image_label)

        # Set the first item as selected
        self.pokemon_combobox.setCurrentIndex(0)
        self.display_pokemon_info(0)

        self.showFullScreen()

    def bind_keys(self):
        shortcut = QShortcut(QKeySequence("Esc"), self)
        shortcut.activated.connect(self.showNormal)

    def get_pokemon_names(self):
        self.cursor.execute("SELECT name FROM pokemon")
        return [row[0] for row in self.cursor.fetchall()]

    def get_pokemon_id(self):
        self.cursor.execute("SELECT id FROM pokemon")
        return [row[0] for row in self.cursor.fetchall()]

    def display_pokemon_info(self, index):
        selected_pokemon = self.pokemon_combobox.currentText()
        self.cursor.execute(
            "SELECT image_file FROM pokemon WHERE name=?", (selected_pokemon,)
        )
        image_file = self.cursor.fetchone()[0]

        try:
            image_path = os.path.join("..", "images", "pokemon", image_file)
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap)
            self.name_label.setText(selected_pokemon)

        except FileNotFoundError:
            self.name_label.setText(f"Error: Image not found for {selected_pokemon}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokedexApp()
    window.show()
    sys.exit(app.exec())
