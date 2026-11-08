from __future__ import annotations

import sqlite3
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

from PyQt6.QtCore import QSize, Qt
from PyQt6.QtGui import (
    QCloseEvent,
    QFontDatabase,
    QIcon,
    QKeySequence,
    QPixmap,
    QShortcut,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pokedex.db"
SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "sprites"
SHINY_SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "shiny"
LARGE_IMAGES_DIR = BASE_DIR / "images" / "pokemon" / "large"
TRAINER_IMAGE_PATH = BASE_DIR / "images" / "trainers" / "trainer.jpeg"
FONT_PATH = BASE_DIR / "src" / "fonts" / "PKMN_RBYGSC.ttf"
STYLES_PATH = BASE_DIR / "src" / "styles.qss"
DARK_STYLES_PATH = BASE_DIR / "src" / "dark_styles.qss"

DEX_REGIONS: dict[str, tuple[int, int] | None] = {
    "National": None,
    "Kanto": (1, 151),
    "Johto": (152, 251),
}


def _connect(signal: Any, slot: Callable[..., Any]) -> None:
    """Connect a Qt signal to a callable slot without triggering PyQt6 ClassVar stub errors."""
    signal.connect(slot)


class MainMenu(QWidget):
    """The main menu of the application, containing buttons for different sections."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        region_select_page: QWidget | None = None,
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.region_select_page: QWidget | None = region_select_page
        layout = QVBoxLayout(self)

        self.pokedex_button = QPushButton("Pokédex")
        _connect(self.pokedex_button.clicked, self._open_pokedex_menu)
        layout.addWidget(self.pokedex_button)

        self.trainer_card_button = QPushButton("Trainer Card")
        _connect(
            self.trainer_card_button.clicked,
            lambda: [self.hide(), stacked_widget.setCurrentIndex(1)],
        )
        layout.addWidget(self.trainer_card_button)

        self.settings_button = QPushButton("Settings")
        _connect(
            self.settings_button.clicked,
            lambda: [self.hide(), stacked_widget.setCurrentIndex(2)],
        )
        layout.addWidget(self.settings_button)

    def _open_pokedex_menu(self) -> None:
        self.hide()
        if self.region_select_page is not None:
            self.stacked_widget.setCurrentWidget(self.region_select_page)
        else:
            self.stacked_widget.setCurrentIndex(0)


class RegionSelectPage(QWidget):
    """Page allowing the user to choose the National Dex or a Regional Pokédex."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        main_menu: QWidget,
        pokedex_page: PokedexPage,
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.main_menu: QWidget = main_menu
        self.pokedex_page: PokedexPage = pokedex_page

        layout = QVBoxLayout(self)
        self.name_label = QLabel("Select a Pokédex")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self.region_buttons: dict[str, QPushButton] = {}
        for region_name in DEX_REGIONS:
            btn = QPushButton(f"{region_name} Pokédex")
            _connect(
                btn.clicked,
                lambda _checked=False, r=region_name: self.select_region(r),
            )
            layout.addWidget(btn)
            self.region_buttons[region_name] = btn

        self.national_button: QPushButton = self.region_buttons["National"]
        self.kanto_button: QPushButton = self.region_buttons["Kanto"]
        self.johto_button: QPushButton = self.region_buttons["Johto"]

        self.back_button = QPushButton("Back")
        _connect(
            self.back_button.clicked,
            lambda: [
                self.stacked_widget.setCurrentWidget(self.main_menu),
                self.main_menu.show(),
            ],
        )
        layout.addWidget(self.back_button)

    def select_region(self, region: str) -> None:
        """Filter PokedexPage by the selected region and navigate to it."""
        self.pokedex_page.load_region(region)
        self.stacked_widget.setCurrentWidget(self.pokedex_page)


class PokedexPage(QWidget):
    """Scrollable list page of Pokémon in the selected Pokédex."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        main_menu: QWidget,
        pokemon_page: PokemonPage | None = None,
        region_select_page: QWidget | None = None,
        db_path: Path | str | None = None,
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.main_menu: QWidget = main_menu
        self.pokemon_page: PokemonPage | None = pokemon_page
        self.region_select_page: QWidget | None = region_select_page
        self.db_path: Path = Path(db_path) if db_path else DB_PATH
        self.current_region: str = "National"
        self.pokemon_names: list[tuple[str, str]] = []

        self.conn = sqlite3.connect(str(self.db_path))
        self.db_cursor = self.conn.cursor()

        layout = QVBoxLayout(self)
        self.name_label = QLabel("Select a Pokémon")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self.pokemon_list = QListWidget()
        self.pokemon_list.setViewMode(QListWidget.ViewMode.ListMode)
        self.pokemon_list.setIconSize(QSize(60, 60))

        # Open PokemonPage only when an item is explicitly activated (Enter/double-click)
        _connect(self.pokemon_list.itemActivated, self.show_pokemon_page)
        layout.addWidget(self.pokemon_list)

        self.back_button = QPushButton("Back")
        _connect(self.back_button.clicked, self._go_back)
        layout.addWidget(self.back_button)

        self.load_region("National")

    def _go_back(self) -> None:
        if self.region_select_page is not None:
            self.stacked_widget.setCurrentWidget(self.region_select_page)
        else:
            self.stacked_widget.setCurrentWidget(self.main_menu)
            self.main_menu.show()

    def get_pokemon_names(self, region: str = "National") -> list[tuple[str, str]]:
        """Retrieve (id, name) tuples from the database for the given region."""
        id_range = DEX_REGIONS.get(region)
        if id_range is not None:
            start_id, end_id = id_range
            self.db_cursor.execute(
                "SELECT id, name FROM pokemon WHERE id BETWEEN ? AND ? ORDER BY id",
                (start_id, end_id),
            )
        else:
            self.db_cursor.execute("SELECT id, name FROM pokemon ORDER BY id")
        return [(str(row[0]), row[1]) for row in self.db_cursor.fetchall()]

    def load_region(self, region: str = "National") -> None:
        """Populate pokemon_list with Pokémon belonging to the specified region."""
        self.current_region = region
        self.pokemon_names = self.get_pokemon_names(region)
        self.name_label.setText(f"{region} Pokédex")
        self.pokemon_list.clear()
        for pokemon_id, name in self.pokemon_names:
            item = QListWidgetItem(f"{pokemon_id}: {name.upper()}")
            icon_path = SPRITES_DIR / f"{pokemon_id}.png"
            icon = QIcon(str(icon_path))
            item.setIcon(icon)
            self.pokemon_list.addItem(item)

    def show_pokemon_page(
        self,
        item_or_stack: QListWidgetItem | QStackedWidget | None,
        maybe_item: QListWidgetItem | None = None,
    ) -> None:
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

        if isinstance(current_item, QListWidgetItem):
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
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.pokedex_page: QWidget = pokedex_page
        self.db_path: Path = Path(db_path) if db_path else DB_PATH
        self.current_pokemon_id: int | None = None
        self._caught: bool = False

        self.conn = sqlite3.connect(str(self.db_path))
        self.db_cursor = self.conn.cursor()

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
        _connect(self.caught_button.clicked, self.toggle_caught)
        layout.addWidget(self.caught_button)

        # Back button
        self.back_button = QPushButton("Back")
        _connect(
            self.back_button.clicked,
            lambda: self.stacked_widget.setCurrentWidget(self.pokedex_page),
        )
        layout.addWidget(self.back_button)

        if pokemon_id is not None:
            self.load_pokemon(pokemon_id)

    def load_pokemon(self, pokemon_id: int | str) -> None:
        """Load and display all database fields and evolutions for the given pokemon_id."""
        self.current_pokemon_id = int(pokemon_id)
        self.db_cursor.execute(
            """
            SELECT id, name, Type1, Type2, image_file, caught, description
            FROM pokemon
            WHERE id = ?
            """,
            (self.current_pokemon_id,),
        )
        result = self.db_cursor.fetchone()
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

    def fetch_pokemon_info(self, pokemon_id: int | str) -> None:
        """Alias for load_pokemon."""
        self.load_pokemon(pokemon_id)

    def _load_evolutions(self, pokemon_id: int) -> None:
        """Query the evolutions table and populate evolution link buttons."""
        for btn in self.evolution_buttons:
            self.evolutions_layout.removeWidget(btn)
            btn.deleteLater()
        self.evolution_buttons.clear()

        self.db_cursor.execute(
            """
            SELECT p.id, p.name
            FROM evolutions e
            JOIN pokemon p ON e.from_pokemon = p.id
            WHERE e.to_pokemon = ?
            ORDER BY p.id
            """,
            (pokemon_id,),
        )
        evolves_from = self.db_cursor.fetchall()

        self.db_cursor.execute(
            """
            SELECT p.id, p.name
            FROM evolutions e
            JOIN pokemon p ON e.to_pokemon = p.id
            WHERE e.from_pokemon = ?
            ORDER BY p.id
            """,
            (pokemon_id,),
        )
        evolves_to = self.db_cursor.fetchall()

        parts = []
        for evo_id, evo_name in evolves_from:
            parts.append(f"From: {evo_name.capitalize()}")
            btn = QPushButton(f"← #{evo_id} {evo_name.capitalize()}")
            _connect(
                btn.clicked,
                lambda _checked=False, target_id=evo_id: self.load_pokemon(target_id),
            )
            self.evolutions_layout.addWidget(btn)
            self.evolution_buttons.append(btn)

        for evo_id, evo_name in evolves_to:
            parts.append(f"To: {evo_name.capitalize()}")
            btn = QPushButton(f"→ #{evo_id} {evo_name.capitalize()}")
            _connect(
                btn.clicked,
                lambda _checked=False, target_id=evo_id: self.load_pokemon(target_id),
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
        self.db_cursor.execute(
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
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.main_menu: QWidget = main_menu
        self.db_path: Path = Path(db_path) if db_path else DB_PATH

        self.conn = sqlite3.connect(str(self.db_path))
        self.db_cursor = self.conn.cursor()

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
        _connect(
            self.back_button.clicked,
            lambda: [
                self.stacked_widget.setCurrentWidget(self.main_menu),
                self.main_menu.show(),
            ],
        )
        button_layout.addWidget(self.back_button)
        layout.addWidget(button_widget)

        self.refresh_trainer_info()

    def refresh_trainer_info(self) -> None:
        """Query trainers and caught Pokémon count from SQLite and update labels."""
        self.db_cursor.execute(
            "SELECT trainer_name, badges_earned FROM trainers ORDER BY trainer_id LIMIT 1"
        )
        trainer_row = self.db_cursor.fetchone()
        if trainer_row:
            trainer_name, badges_earned = trainer_row[0], trainer_row[1]
        else:
            trainer_name, badges_earned = "ASH", 0

        self.db_cursor.execute("SELECT COUNT(*) FROM pokemon WHERE caught = 1")
        caught_row = self.db_cursor.fetchone()
        caught_count = caught_row[0] if caught_row else 0

        self.name_label.setText(f"Name: {trainer_name}")
        self.caught_label.setText(f"Caught: {caught_count}")
        self.badges_label.setText(f"Badges: {badges_earned}")

    def showEvent(self, a0: QShowEvent | None) -> None:
        """Refresh trainer info and caught count every time the page is shown."""
        super().showEvent(a0)
        self.refresh_trainer_info()


class SettingsPage(QWidget):
    """Application settings page with Light/Dark mode toggle."""

    def __init__(
        self,
        stacked_widget: QStackedWidget,
        main_menu: QWidget,
        app_window: PokedexApp | None = None,
    ) -> None:
        super().__init__()
        self.stacked_widget: QStackedWidget = stacked_widget
        self.main_menu: QWidget = main_menu
        self.app_window: PokedexApp | None = app_window
        self.dark_mode: bool = False

        layout = QVBoxLayout(self)
        self.name_label = QLabel("Settings")
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(self.name_label)

        self.theme_button = QPushButton("Theme: Light Mode")
        self.theme_button.setCheckable(True)
        _connect(self.theme_button.clicked, self.toggle_theme)
        layout.addWidget(self.theme_button)

        self.back_button = QPushButton("Back")
        _connect(
            self.back_button.clicked,
            lambda: [
                stacked_widget.setCurrentWidget(main_menu),
                main_menu.show(),
            ],
        )
        layout.addWidget(self.back_button)

    def toggle_theme(self, _checked: bool | None = None) -> None:
        """Toggle between Light Mode and Dark Mode."""
        self.dark_mode = not self.dark_mode
        self.theme_button.blockSignals(True)
        self.theme_button.setChecked(self.dark_mode)
        self.theme_button.setText(
            "Theme: Dark Mode" if self.dark_mode else "Theme: Light Mode"
        )
        self.theme_button.blockSignals(False)

        if self.app_window is not None:
            self.app_window.apply_theme(self.dark_mode)


class PokedexApp(QMainWindow):
    """Main window managing stacked pages of the Pokédex application."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        super().__init__()
        self.db_path: Path = Path(db_path) if db_path else DB_PATH
        self.dark_mode: bool = False
        self.custom_font_family: str = "Arial"
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
        self.region_select_page = RegionSelectPage(
            self.stacked_widget, self.main_menu, self.pokedex_page
        )
        self.main_menu.region_select_page = self.region_select_page
        self.pokedex_page.region_select_page = self.region_select_page
        self.pokemon_page = PokemonPage(
            self.stacked_widget, self.pokedex_page, db_path=self.db_path
        )
        self.pokedex_page.pokemon_page = self.pokemon_page
        self.trainer_card_page = TrainerCardPage(
            self.stacked_widget, self.main_menu, db_path=self.db_path
        )
        self.settings_page = SettingsPage(
            self.stacked_widget, self.main_menu, app_window=self
        )

        self.stacked_widget.addWidget(self.pokedex_page)
        self.stacked_widget.addWidget(self.trainer_card_page)
        self.stacked_widget.addWidget(self.settings_page)
        self.stacked_widget.addWidget(self.main_menu)
        self.stacked_widget.addWidget(self.pokemon_page)
        self.stacked_widget.addWidget(self.region_select_page)

        self.stacked_widget.setCurrentWidget(self.main_menu)
        self.apply_theme(self.dark_mode)

    def apply_theme(self, dark_mode: bool = False) -> None:
        """Apply light or dark stylesheet across the window and QApplication."""
        self.dark_mode = bool(dark_mode)
        target_qss = DARK_STYLES_PATH if self.dark_mode else STYLES_PATH
        if target_qss.exists():
            style = target_qss.read_text(encoding="utf-8")
            self.setStyleSheet(style)
            app_instance = QApplication.instance()
            if isinstance(app_instance, QApplication):
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
        _connect(shortcut.activated, self.showNormal)

    def closeEvent(self, a0: QCloseEvent | None) -> None:
        for page in (self.pokedex_page, self.pokemon_page, self.trainer_card_page):
            conn = getattr(page, "conn", None)
            if conn is not None:
                try:
                    conn.close()
                except Exception:
                    pass
        super().closeEvent(a0)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = PokedexApp()
    window.show()
    sys.exit(app.exec())
