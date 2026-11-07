import sys
import sqlite3
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QWidget,
    QPushButton,
    QStackedWidget,
    QGridLayout,
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut, QFontDatabase, QIcon
from PyQt6.QtCore import Qt, QSize

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pokedex.db"
SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "sprites"
SHINY_SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "shiny"
LARGE_IMAGES_DIR = BASE_DIR / "images" / "pokemon" / "large"
TRAINER_IMAGE_PATH = BASE_DIR / "images" / "trainers" / "trainer.jpeg"
FONT_PATH = BASE_DIR / "src" / "fonts" / "PKMN_RBYGSC.ttf"
STYLES_PATH = BASE_DIR / "src" / "styles.qss"


class MainMenu(QWidget):
    """The main menu of the application, containing buttons for different sections."""

    def __init__(self, stacked_widget: QStackedWidget):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.layout = QVBoxLayout(self)

        self.pokedex_button = QPushButton("Pokédex")
        self.pokedex_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(0)]
        )
        self.layout.addWidget(self.pokedex_button)

        self.trainer_card_button = QPushButton("Trainer Card")
        self.trainer_card_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(1)]
        )
        self.layout.addWidget(self.trainer_card_button)

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(
            lambda: [self.hide(), stacked_widget.setCurrentIndex(2)]
        )
        self.layout.addWidget(self.settings_button)


class PokedexPage(QWidget):
    """Scrollable list page of all Pokémon in the Pokédex."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        main_menu: QWidget,
        pokemon_page: "PokemonPage | None" = None,
        db_path: Path | str | None = None,
    ):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.main_menu = main_menu
        self.pokemon_page = pokemon_page
        self.db_path = Path(db_path) if db_path else DB_PATH

        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()
        self.pokemon_names = self.get_pokemon_names()

        layout = QVBoxLayout(self)
        self.name_label = QLabel("Select a Pokémon")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self.pokemon_list = QListWidget()
        self.pokemon_list.setViewMode(QListWidget.ViewMode.ListMode)
        self.pokemon_list.setIconSize(QSize(60, 60))
        for pokemon_id, name in self.pokemon_names:
            item = QListWidgetItem(f"{pokemon_id}: {name.upper()}")
            icon_path = SPRITES_DIR / f"{pokemon_id}.png"
            icon = QIcon(str(icon_path))
            item.setIcon(icon)
            self.pokemon_list.addItem(item)

        # Open PokemonPage only when an item is explicitly activated (Enter/double-click)
        self.pokemon_list.itemActivated.connect(self.show_pokemon_page)
        layout.addWidget(self.pokemon_list)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                self.stacked_widget.setCurrentWidget(self.main_menu),
                self.main_menu.show(),
            ]
        )
        layout.addWidget(self.back_button)

    def get_pokemon_names(self) -> list[tuple[str, str]]:
        """Retrieve (id, name) tuples from the database."""
        self.cursor.execute("SELECT id, name FROM pokemon ORDER BY id")
        return [(str(row[0]), row[1]) for row in self.cursor.fetchall()]

    def show_pokemon_page(self, item_or_stack, maybe_item: QListWidgetItem | None = None):
        """
        Display the reusable PokemonPage for the activated Pokémon item.
        Supports both `show_pokemon_page(item)` and `show_pokemon_page(stacked_widget, item)`.
        """
        if isinstance(item_or_stack, QStackedWidget):
            stacked_widget = item_or_stack
            current_item = maybe_item
        else:
            stacked_widget = self.stacked_widget
            current_item = item_or_stack

        if current_item is not None:
            pokemon_id_str = current_item.text().split(":")[0].strip()
            pokemon_id = int(pokemon_id_str)
            if self.pokemon_page is None:
                self.pokemon_page = PokemonPage(
                    stacked_widget, self, db_path=self.db_path
                )
                stacked_widget.addWidget(self.pokemon_page)
            self.pokemon_page.load_pokemon(pokemon_id)
            stacked_widget.setCurrentWidget(self.pokemon_page)


class PokemonPage(QWidget):
    """Reusable detail page displaying full Pokémon information, evolutions, and caught status."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        pokedex_page: QWidget,
        pokemon_id: int | str | None = None,
        db_path: Path | str | None = None,
    ):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.pokedex_page = pokedex_page
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.current_pokemon_id: int | None = None
        self._caught: bool = False

        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()

        layout = QVBoxLayout(self)

        # Header row: ID and Name
        header_layout = QHBoxLayout()
        self.id_label = QLabel()
        self.id_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label = QLabel()
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.id_label)
        header_layout.addWidget(self.name_label)
        layout.addLayout(header_layout)

        # Artwork and Shiny sprite
        images_layout = QHBoxLayout()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.shiny_image_label = QLabel()
        self.shiny_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        images_layout.addWidget(self.image_label)
        images_layout.addWidget(self.shiny_image_label)
        layout.addLayout(images_layout)

        # Type1 / Type2 badges
        types_layout = QHBoxLayout()
        self.type1_label = QLabel()
        self.type1_label.setObjectName("typeBadge")
        self.type1_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.type2_label = QLabel()
        self.type2_label.setObjectName("typeBadge")
        self.type2_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        types_layout.addWidget(self.type1_label)
        types_layout.addWidget(self.type2_label)
        layout.addLayout(types_layout)

        # Word-wrapped flavor text description
        self.description_label = QLabel()
        self.description_label.setObjectName("descriptionLabel")
        self.description_label.setWordWrap(True)
        self.description_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.description_label)

        # Evolution links
        self.evolutions_label = QLabel()
        self.evolutions_label.setObjectName("evolutionsLabel")
        self.evolutions_label.setWordWrap(True)
        self.evolutions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.evolutions_label)

        self.evolutions_container = QWidget()
        self.evolutions_layout = QHBoxLayout(self.evolutions_container)
        self.evolution_buttons: list[QPushButton] = []
        layout.addWidget(self.evolutions_container)

        # Caught toggle button
        self.caught_button = QPushButton("Caught: No")
        self.caught_button.setCheckable(True)
        self.caught_button.clicked.connect(self.toggle_caught)
        layout.addWidget(self.caught_button)

        # Back button
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: self.stacked_widget.setCurrentWidget(self.pokedex_page)
        )
        layout.addWidget(self.back_button)

        if pokemon_id is not None:
            self.load_pokemon(pokemon_id)

    def load_pokemon(self, pokemon_id: int | str) -> None:
        """Load and display all database fields and evolutions for the given pokemon_id."""
        self.current_pokemon_id = int(pokemon_id)
        self.cursor.execute(
            """
            SELECT id, name, Type1, Type2, image_file, caught, description
            FROM pokemon
            WHERE id = ?
            """,
            (self.current_pokemon_id,),
        )
        result = self.cursor.fetchone()
        if not result:
            return

        pid, name, type1, type2, image_file, caught, description = result
        self.id_label.setText(f"#{pid:03d}")
        self.name_label.setText(name.capitalize())

        if type1:
            self.type1_label.setText(type1.capitalize())
            self.type1_label.show()
        else:
            self.type1_label.setText("")
            self.type1_label.hide()

        if type2:
            self.type2_label.setText(type2.capitalize())
            self.type2_label.show()
        else:
            self.type2_label.setText("")
            self.type2_label.hide()

        self.description_label.setText(description or "No description available.")

        self._caught = bool(caught)
        self.caught_button.blockSignals(True)
        self.caught_button.setChecked(self._caught)
        self.caught_button.setText("Caught: Yes" if self._caught else "Caught: No")
        self.caught_button.blockSignals(False)

        image_filename = image_file or f"{pid}.png"
        image_path = LARGE_IMAGES_DIR / image_filename
        pixmap = QPixmap(str(image_path))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                180,
                180,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        self.image_label.setPixmap(pixmap)

        shiny_path = SHINY_SPRITES_DIR / image_filename
        shiny_pixmap = QPixmap(str(shiny_path))
        if not shiny_pixmap.isNull():
            shiny_pixmap = shiny_pixmap.scaled(
                120,
                120,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        self.shiny_image_label.setPixmap(shiny_pixmap)

        self._load_evolutions(pid)

    fetch_pokemon_info = load_pokemon

    def _load_evolutions(self, pokemon_id: int) -> None:
        """Query the evolutions table and populate evolution link buttons."""
        for btn in self.evolution_buttons:
            self.evolutions_layout.removeWidget(btn)
            btn.deleteLater()
        self.evolution_buttons.clear()

        self.cursor.execute(
            """
            SELECT p.id, p.name
            FROM evolutions e
            JOIN pokemon p ON e.from_pokemon = p.id
            WHERE e.to_pokemon = ?
            ORDER BY p.id
            """,
            (pokemon_id,),
        )
        evolves_from = self.cursor.fetchall()

        self.cursor.execute(
            """
            SELECT p.id, p.name
            FROM evolutions e
            JOIN pokemon p ON e.to_pokemon = p.id
            WHERE e.from_pokemon = ?
            ORDER BY p.id
            """,
            (pokemon_id,),
        )
        evolves_to = self.cursor.fetchall()

        parts = []
        for evo_id, evo_name in evolves_from:
            parts.append(f"From: {evo_name.capitalize()}")
            btn = QPushButton(f"← #{evo_id} {evo_name.capitalize()}")
            btn.clicked.connect(
                lambda _checked=False, target_id=evo_id: self.load_pokemon(target_id)
            )
            self.evolutions_layout.addWidget(btn)
            self.evolution_buttons.append(btn)

        for evo_id, evo_name in evolves_to:
            parts.append(f"To: {evo_name.capitalize()}")
            btn = QPushButton(f"→ #{evo_id} {evo_name.capitalize()}")
            btn.clicked.connect(
                lambda _checked=False, target_id=evo_id: self.load_pokemon(target_id)
            )
            self.evolutions_layout.addWidget(btn)
            self.evolution_buttons.append(btn)

        if parts:
            self.evolutions_label.setText(" | ".join(parts))
        else:
            self.evolutions_label.setText("Evolutions: None")

    def toggle_caught(self, _checked: bool | None = None) -> None:
        """Toggle the caught status of the current Pokémon in SQLite."""
        if self.current_pokemon_id is None:
            return
        new_caught = 0 if self._caught else 1
        self.cursor.execute(
            "UPDATE pokemon SET caught = ? WHERE id = ?",
            (new_caught, self.current_pokemon_id),
        )
        self.conn.commit()
        self._caught = bool(new_caught)
        self.caught_button.blockSignals(True)
        self.caught_button.setChecked(self._caught)
        self.caught_button.setText("Caught: Yes" if self._caught else "Caught: No")
        self.caught_button.blockSignals(False)


class TrainerCardPage(QWidget):
    """Trainer card page displaying dynamic trainer stats from SQLite."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        main_menu: QWidget,
        db_path: Path | str | None = None,
    ):
        super().__init__()
        self.stacked_widget = stacked_widget
        self.main_menu = main_menu
        self.db_path = Path(db_path) if db_path else DB_PATH

        self.conn = sqlite3.connect(str(self.db_path))
        self.cursor = self.conn.cursor()

        layout = QVBoxLayout(self)

        trainer_info_widget = QWidget()
        trainer_info_layout = QHBoxLayout(trainer_info_widget)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        pixmap = QPixmap(str(TRAINER_IMAGE_PATH))
        if not pixmap.isNull():
            pixmap = pixmap.scaled(
                256,
                400,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.FastTransformation,
            )
        self.image_label = QLabel()
        self.image_label.setPixmap(pixmap)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(self.image_label)

        right_widget = QWidget()
        right_layout = QGridLayout(right_widget)

        self.name_label = QLabel("Name: ASH")
        right_layout.addWidget(self.name_label, 0, 0, 1, 2)

        self.caught_label = QLabel("Caught: 0")
        right_layout.addWidget(self.caught_label, 1, 0)

        self.badges_label = QLabel("Badges: 0")
        right_layout.addWidget(self.badges_label, 2, 0)

        trainer_info_layout.addWidget(left_widget)
        trainer_info_layout.addWidget(right_widget)
        layout.addWidget(trainer_info_widget)

        button_widget = QWidget()
        button_layout = QHBoxLayout(button_widget)
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                self.stacked_widget.setCurrentWidget(self.main_menu),
                self.main_menu.show(),
            ]
        )
        button_layout.addWidget(self.back_button)
        layout.addWidget(button_widget)

        self.refresh_trainer_info()

    def refresh_trainer_info(self) -> None:
        """Query trainers and caught Pokémon count from SQLite and update labels."""
        self.cursor.execute(
            "SELECT trainer_name, badges_earned FROM trainers ORDER BY trainer_id LIMIT 1"
        )
        trainer_row = self.cursor.fetchone()
        if trainer_row:
            trainer_name, badges_earned = trainer_row[0], trainer_row[1]
        else:
            trainer_name, badges_earned = "ASH", 0

        self.cursor.execute("SELECT COUNT(*) FROM pokemon WHERE caught = 1")
        caught_row = self.cursor.fetchone()
        caught_count = caught_row[0] if caught_row else 0

        self.name_label.setText(f"Name: {trainer_name}")
        self.caught_label.setText(f"Caught: {caught_count}")
        self.badges_label.setText(f"Badges: {badges_earned}")

    def showEvent(self, event) -> None:
        """Refresh trainer info and caught count every time the page is shown."""
        super().showEvent(event)
        self.refresh_trainer_info()


class SettingsPage(QWidget):
    """Application settings page."""

    def __init__(self, stacked_widget: QStackedWidget, main_menu: QWidget):
        super().__init__()
        layout = QVBoxLayout(self)
        self.name_label = QLabel("Settings")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ]
        )
        layout.addWidget(self.back_button)


class PokedexApp(QMainWindow):
    """Main window managing stacked pages of the Pokédex application."""

    def __init__(self, db_path: Path | str | None = None):
        super().__init__()
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.setWindowTitle("Pokédex")
        self.setFixedSize(640, 640)
        self.bind_keys()
        self.load_custom_font()

        self.stacked_widget = QStackedWidget(self)
        self.setCentralWidget(self.stacked_widget)

        self.main_menu = MainMenu(self.stacked_widget)
        self.pokedex_page = PokedexPage(
            self.stacked_widget, self.main_menu, db_path=self.db_path
        )
        self.pokemon_page = PokemonPage(
            self.stacked_widget, self.pokedex_page, db_path=self.db_path
        )
        self.pokedex_page.pokemon_page = self.pokemon_page
        self.trainer_card_page = TrainerCardPage(
            self.stacked_widget, self.main_menu, db_path=self.db_path
        )
        self.settings_page = SettingsPage(self.stacked_widget, self.main_menu)

        self.stacked_widget.addWidget(self.pokedex_page)
        self.stacked_widget.addWidget(self.trainer_card_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.pokemon_page)

        self.stacked_widget.setCurrentWidget(self.main_menu)

        if STYLES_PATH.exists():
            style = STYLES_PATH.read_text(encoding="utf-8")
            self.setStyleSheet(style)
            app_instance = QApplication.instance()
            if app_instance is not None:
                app_instance.setStyleSheet(style)

    def load_custom_font(self) -> None:
        font_id = QFontDatabase.addApplicationFont(str(FONT_PATH))
        font_families = QFontDatabase.applicationFontFamilies(font_id)
        if font_families:
            self.custom_font_family = font_families[0]
        else:
            self.custom_font_family = "Arial"

    def bind_keys(self) -> None:
        shortcut = QShortcut(QKeySequence("Esc"), self)
        shortcut.activated.connect(self.showNormal)

    def closeEvent(self, event) -> None:
        for page in (self.pokedex_page, self.pokemon_page, self.trainer_card_page):
            conn = getattr(page, "conn", None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokedexApp()
    window.show()
    sys.exit(app.exec())
