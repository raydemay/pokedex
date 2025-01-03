import sys
import sqlite3
import os

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QComboBox,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QStackedWidget,
    QGridLayout,
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QFontDatabase
from PyQt6.QtCore import Qt


class MainMenu(QWidget):
    def __init__(self, stacked_widget):
        super().__init__()
        layout = QVBoxLayout(self)

        pokedex_button = QPushButton("Pokédex")
        pokedex_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(0)]
        )
        layout.addWidget(pokedex_button)

        trainer_card_button = QPushButton("Trainer Card")
        trainer_card_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(1)]
        )
        layout.addWidget(trainer_card_button)

        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(2)]
        )
        layout.addWidget(settings_button)


class PokedexPage(QWidget):  # Your existing Pokedex interface
    def __init__(self, stacked_widget, main_menu):
        super().__init__()
        db_path = os.path.join("..", "database", "pokedex.db")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.pokemon_names = self.get_pokemon_names()
        self.selected_index = 0
        layout = QVBoxLayout(self)
        self.name_label = QLabel("Select a Pokémon:")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.name_label)

        self.pokemon_combobox = QComboBox()
        for id, name in self.pokemon_names:  # Iterate through the tuples
            self.pokemon_combobox.addItem(
                f"{id}: {name.capitalize()}"
            )  # Add id and name to the combobox
        self.pokemon_combobox.currentIndexChanged.connect(self.display_pokemon_info)
        layout.addWidget(self.pokemon_combobox)
        layout.addStretch(2)
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ]  # Switch to MainMenu widget
        )
        layout.addWidget(self.back_button)

        # self.showFullScreen()

    def get_pokemon_names(self):
        self.cursor.execute("SELECT id, name FROM pokemon")
        return [
            (str(row[0]), row[1]) for row in self.cursor.fetchall()
        ]  # Return tuples of (id, name)

    def get_pokemon_id(self):
        self.cursor.execute("SELECT id FROM pokemon")
        return [row[0] for row in self.cursor.fetchall()]

    def display_pokemon_info(self):
        selected_text = self.pokemon_combobox.currentText()
        pokemon_id, selected_pokemon = selected_text.split(": ")
        pokemon_lookup_name = selected_pokemon.lower()
        self.cursor.execute(
            "SELECT image_file FROM pokemon WHERE name=?", (pokemon_lookup_name,)
        )
        image_file = self.cursor.fetchone()[0]

        try:
            image_path = os.path.join("..", "images", "pokemon", image_file)
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap)
            self.name_label.setText(f"{pokemon_id}: {selected_pokemon}")

        except FileNotFoundError:
            self.name_label.setText(f"Error: Image not found for {selected_pokemon}")


class TrainerCardPage(QWidget):
    def __init__(self, stacked_widget, main_menu):
        super().__init__()
        layout = QVBoxLayout(self)
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        self.name_label = QLabel("Trainer Card")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        title_layout.addWidget(self.name_label)
        layout.addWidget(title_widget)

        trainer_info_widget = QWidget()
        trainer_info_layout = QHBoxLayout(trainer_info_widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        image_path = os.path.join("..", "images", "trainers", "trainer.jpeg")
        pixmap = QPixmap(image_path)
        image_label = QLabel()
        image_label.setPixmap(pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the image
        left_layout.addWidget(image_label)

        right_widget = QWidget()
        right_layout = QGridLayout(right_widget)

        name_label = QLabel(f"Name: Ash")
        right_layout.addWidget(name_label, 0, 0, 1, 2)  # Span 2 columns

        id_label = QLabel(f"ID: 1")
        right_layout.addWidget(id_label, 1, 0)

        caught_label = QLabel(f"Caught: 135")
        right_layout.addWidget(caught_label, 1, 1)

        badges_label = QLabel(f"Badges: 2")
        right_layout.addWidget(badges_label, 2, 0)

        layout.addWidget(left_widget)
        layout.addWidget(right_widget)

        button_widget = QWidget()  # Create a widget for the button
        button_layout = QHBoxLayout(button_widget)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ]  # Switch to MainMenu widget
        )
        button_layout.addWidget(self.back_button)
        layout.addWidget(button_widget)


class SettingsPage(QWidget):
    def __init__(self, stacked_widget, main_menu):
        super().__init__()
        layout = QVBoxLayout(self)
        self.name_label = QLabel("Selttings")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.name_label)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ]  # Switch to MainMenu widget
        )
        layout.addWidget(self.back_button)


class PokedexApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pokédex")
        self.setMinimumSize(640, 640)
        self.bind_keys()
        self.load_custom_font()  # Load the custom font

        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        self.main_menu = MainMenu(self.stacked_widget)  # Initialize main_menu first
        self.pokedex_page = PokedexPage(self.stacked_widget, self.main_menu)
        self.trainer_card_page = TrainerCardPage(self.stacked_widget, self.main_menu)
        self.settings_page = SettingsPage(self.stacked_widget, self.main_menu)

        self.stacked_widget.addWidget(self.pokedex_page)
        self.stacked_widget.addWidget(self.trainer_card_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.main_menu)

        self.stacked_widget.setCurrentWidget(self.main_menu)

        # self.showFullScreen()
        # Open the qss styles file and read in the CSS-like styling code
        with open("styles.qss", "r") as f:
            style = f.read()

            # Set the stylesheet of the application
            app.setStyleSheet(style)

    def load_custom_font(self):
        font_path = os.path.join("fonts/PKMN_RBYGSC.ttf")
        font_id = QFontDatabase.addApplicationFont(
            font_path
        )  # Add the font to the application
        font_families = QFontDatabase.applicationFontFamilies(
            font_id
        )  # Get the font family name
        if font_families:
            self.custom_font_family = font_families[0]  # Store the font family name
        else:
            print(f"Error loading font from {font_path}")
            self.custom_font_family = "Arial"  # Fallback to a default font

    def bind_keys(self):
        shortcut = QShortcut(QKeySequence("Esc"), self)
        shortcut.activated.connect(self.showNormal)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokedexApp()
    window.show()
    sys.exit(app.exec())
