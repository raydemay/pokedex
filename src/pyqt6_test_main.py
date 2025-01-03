import sys
import sqlite3
import os

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QStackedWidget,
    QGridLayout,
    QFrame,
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QFontDatabase, QIcon
from PyQt6.QtCore import Qt, QSize


class MainMenu(QWidget):
    # The main menu of the application, containing buttons for different actions.
    def __init__(self, stacked_widget):
        # Initialize the parent class and create a vertical layout for the widget
        super().__init__()
        self.layout = QVBoxLayout(self)

        # Create a button for accessing the Pokédex
        self.pokedex_button = QPushButton("Pokédex")
        # Connect the button's clicked signal to hide the main menu and display the next index in the stacked widget
        self.pokedex_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(0)]
        )
        # Add the button to the layout
        self.layout.addWidget(self.pokedex_button)

        # Create a button for accessing the Trainer Card
        trainer_card_button = QPushButton("Trainer Card")
        trainer_card_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(1)]
        )
        self.layout.addWidget(trainer_card_button)

        # Create a button for accessing the Settings
        settings_button = QPushButton("Settings")
        settings_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(2)]
        )
        self.layout.addWidget(settings_button)


class PokedexPage(QWidget):
    def __init__(self, stacked_widget, main_menu):
        super().__init__()
        db_path = os.path.join("..", "database", "pokedex.db")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.pokemon_names = self.get_pokemon_names()
        layout = QVBoxLayout(self)
        self.name_label = QLabel("Select a Pokémon")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(self.name_label)

        # Create scrollable area for displaying Pokémon names
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        # Create a widget to hold the list
        list_widget = QWidget()
        list_layout = QVBoxLayout(list_widget)

        # Creeate list and populate with Pokémon names
        self.pokemon_list = QListWidget()
        self.pokemon_list.setViewMode(QListWidget.ViewMode.ListMode)
        self.pokemon_list.setIconSize(QSize(60, 60))
        # self.pokemon_list.setSpacing(3)  # Set the spacing to 4 pixels
        for id, name in self.pokemon_names:  # Iterate through the tuples
            item = QListWidgetItem(f"{id}: {name.upper()}")
            icon_path = os.path.join("..", "images", "pokemon", "sprites", f"{id}.png")
            icon = QIcon(icon_path)
            item.setIcon(icon)
            self.pokemon_list.addItem(item)  # Add id and name to the combobox
        # Open PokemonPage when an item is clicked
        self.pokemon_list.currentItemChanged.connect(
            lambda current: self.show_pokemon_page(stacked_widget, current)
        )
        list_layout.addWidget(self.pokemon_list)
        scroll_area.setWidget(
            list_widget
        )  # Set the list widget as the scroll area's widget
        layout.addWidget(scroll_area)  # Add the scroll area to the main layout

        # Add Back button
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ]  # Switch to MainMenu widget
        )
        layout.addWidget(self.back_button)

    def get_pokemon_names(self):
        # Function to get Pokemon names from the database
        self.cursor.execute("SELECT id, name FROM pokemon")
        return [
            (str(row[0]), row[1]) for row in self.cursor.fetchall()
        ]  # Return tuples of (id, name)

    def show_pokemon_page(self, stacked_widget, current_item):
        """
        Displays the PokemonPage for the selected Pokemon.

        This function is called when a new item is selected in the pokemon_list.
        It extracts the pokemon_id from the selected item's text, creates a
        PokemonPage instance with the ID, and adds it to the stacked_widget.
        """
        if current_item is not None:
            pokemon_id, _ = current_item.text().split(": ")
            pokemon_page = PokemonPage(stacked_widget, self, pokemon_id)
            stacked_widget.addWidget(pokemon_page)
            stacked_widget.setCurrentWidget(pokemon_page)


class PokemonPage(QWidget):
    def __init__(self, stacked_widget, pokedex_page, pokemon_id):
        super().__init__()
        self.stacked_widget = stacked_widget  # Store stacked_widget for later use

        # Initialize database lookup
        db_path = os.path.join("..", "database", "pokedex.db")
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

        # Build page layout
        layout = QVBoxLayout(self)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.name_label)
        self.image_label = QLabel()
        # Fetch and display Pokemon information from the database
        self.fetch_pokemon_info(pokemon_id)

        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        # Add a "Back" button
        back_button = QPushButton("Back")
        back_button.clicked.connect(
            lambda: stacked_widget.setCurrentWidget(
                pokedex_page
            )  # Go back to pokedex_page
        )
        layout.addWidget(back_button)

    def fetch_pokemon_info(self, pokemon_id):
        self.cursor.execute(
            "SELECT name, image_file FROM pokemon WHERE id = ?", (pokemon_id,)
        )
        result = self.cursor.fetchone()
        if result:
            self.name_label.setText(result[0].capitalize())
            image_path = os.path.join("..", "images", "pokemon", "large", result[1])
            pixmap = QPixmap(image_path)
            self.image_label.setPixmap(pixmap)


class TrainerCardPage(QWidget):
    def __init__(self, stacked_widget, main_menu):
        super().__init__()
        layout = QVBoxLayout(self)
        # self.name_label = QLabel("Trainer Card")
        # self.name_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        # layout.addWidget(self.name_label)

        trainer_info_widget = QWidget()
        trainer_info_layout = QHBoxLayout(trainer_info_widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        image_path = os.path.join("..", "images", "trainers", "trainer.jpeg")
        pixmap = QPixmap(image_path)
        smaller_pixmap = pixmap.scaled(
            256,
            400,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )
        image_label = QLabel()
        image_label.setPixmap(smaller_pixmap)
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # Center the image
        left_layout.addWidget(image_label)

        right_widget = QWidget()
        right_layout = QGridLayout(right_widget)

        name_label = QLabel(f"Name: ASH")
        right_layout.addWidget(name_label, 0, 0, 1, 2)  # Span 2 columns

        caught_label = QLabel(f"Caught: 135")
        right_layout.addWidget(caught_label, 1, 0)

        badges_label = QLabel(f"Badges: 2")
        right_layout.addWidget(badges_label, 2, 0)

        trainer_info_layout.addWidget(left_widget)
        trainer_info_layout.addWidget(right_widget)

        layout.addWidget(trainer_info_widget)

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
        """
        Initializes the PokedexApp instance.

        This is the entry point of the application. It sets up the main window,
        creates a database connection, and populates the Pokemon list with
        data from the database.
        """
        super().__init__()
        self.setWindowTitle("Pokédex")
        self.setFixedSize(640, 640)
        self.bind_keys()
        self.load_custom_font()  # Load the custom font

        # Create stacked widget to hold pages
        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        # Initialize main menu and add it to the stack
        self.main_menu = MainMenu(self.stacked_widget)  # Initialize main_menu first
        self.pokedex_page = PokedexPage(self.stacked_widget, self.main_menu)
        self.trainer_card_page = TrainerCardPage(self.stacked_widget, self.main_menu)
        self.settings_page = SettingsPage(self.stacked_widget, self.main_menu)

        # Add pages to the stack
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
