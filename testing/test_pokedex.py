import os
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QShowEvent
from PyQt6.QtWidgets import QApplication, QScrollArea

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "src"))
sys.path.insert(0, str(BASE_DIR / "database"))

import main as pokedex_main
import seed_database as seeder


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary SQLite database initialized from create_tables.sql with sample data."""
    db_file = tmp_path / "test_pokedex.db"
    sql_path = BASE_DIR / "database" / "create_tables.sql"

    conn = sqlite3.connect(str(db_file))
    with conn:
        cur = conn.cursor()
        seeder.execute_schema(cur, sql_path)
        cur.execute(
            "INSERT INTO trainers (trainer_name, pokemon_caught, badges_earned) VALUES (?, ?, ?)",
            ("ASH", 0, 3),
        )
        cur.executemany(
            """
            INSERT INTO pokemon (id, name, Type1, Type2, image_file, caught, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    1,
                    "bulbasaur",
                    "grass",
                    "poison",
                    "1.png",
                    0,
                    "A strange seed was planted on its back at birth.",
                ),
                (
                    2,
                    "ivysaur",
                    "grass",
                    "poison",
                    "2.png",
                    0,
                    "When the bulb on its back grows large, it appears to lose the ability to stand on its hind legs.",
                ),
                (
                    4,
                    "charmander",
                    "fire",
                    None,
                    "4.png",
                    0,
                    "Obviously prefers hot places.",
                ),
            ],
        )
        cur.execute(
            "INSERT INTO evolutions (from_pokemon, to_pokemon) VALUES (?, ?)",
            (1, 2),
        )
    conn.close()
    return db_file


def test_sqlite_schema_and_constraints(tmp_path):
    """Verify create_tables.sql has INTEGER PRIMARY KEY on pokemon and UNIQUE(from_pokemon, to_pokemon) on evolutions."""
    sql_path = BASE_DIR / "database" / "create_tables.sql"
    sql_text = sql_path.read_text(encoding="utf-8")
    assert "id INTEGER PRIMARY KEY" in sql_text
    assert "UNIQUE(from_pokemon, to_pokemon)" in sql_text

    db_file = tmp_path / "schema_check.db"
    conn = sqlite3.connect(str(db_file))
    try:
        with conn:
            cur = conn.cursor()
            seeder.execute_schema(cur, sql_path)
            cur.execute(
                "INSERT INTO pokemon (id, name, Type1) VALUES (?, ?, ?)",
                (1, "bulbasaur", "grass"),
            )
            cur.execute(
                "INSERT INTO pokemon (id, name, Type1) VALUES (?, ?, ?)",
                (2, "ivysaur", "grass"),
            )
            cur.execute(
                "INSERT INTO evolutions (from_pokemon, to_pokemon) VALUES (?, ?)",
                (1, 2),
            )
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute(
                    "INSERT INTO evolutions (from_pokemon, to_pokemon) VALUES (?, ?)",
                    (1, 2),
                )
    finally:
        conn.close()


def test_seed_database_and_flavor_text_cleaning(tmp_path):
    """Verify seed_database cleans form-feed/newline characters, seeds trainers, and populates tables."""
    raw_text = "A strange seed was\nplanted on its\fback at birth."
    assert seeder.clean_flavor_text(raw_text) == "A strange seed was planted on its back at birth."

    db_file = tmp_path / "seeded.db"
    sprites_dir = tmp_path / "sprites"
    large_dir = tmp_path / "large"
    sprites_dir.mkdir()
    large_dir.mkdir()

    # Pre-create existing sprite and large files so download_image skips network calls
    for pid in (1, 2):
        (sprites_dir / f"{pid}.png").write_bytes(b"fake")
        (large_dir / f"{pid}.png").write_bytes(b"fake")

    fake_pokemon = {
        1: {
            "id": 1,
            "name": "bulbasaur",
            "types": [
                {"type": {"name": "grass"}},
                {"type": {"name": "poison"}},
            ],
            "sprites": {
                "front_default": "https://example.com/1.png",
                "other": {"official-artwork": {"front_default": "https://example.com/large/1.png"}},
            },
        },
        2: {
            "id": 2,
            "name": "ivysaur",
            "types": [
                {"type": {"name": "grass"}},
                {"type": {"name": "poison"}},
            ],
            "sprites": {
                "front_default": "https://example.com/2.png",
                "other": {"official-artwork": {"front_default": "https://example.com/large/2.png"}},
            },
        },
    }
    fake_species = {
        1: {
            "flavor_text_entries": [
                {
                    "flavor_text": "Bulbasaur\fGen 1\ntext.",
                    "language": {"name": "en"},
                    "version": {"name": "red"},
                }
            ],
            "evolves_from_species": None,
        },
        2: {
            "flavor_text_entries": [
                {
                    "flavor_text": "Ivysaur\fGen 1\ntext.",
                    "language": {"name": "en"},
                    "version": {"name": "blue"},
                }
            ],
            "evolves_from_species": {"name": "bulbasaur"},
        },
    }

    with (
        patch.object(seeder, "get_pokemon_data", side_effect=lambda pid: fake_pokemon[int(pid)]),
        patch.object(seeder, "get_pokemon_species_data", side_effect=lambda pid: fake_species[int(pid)]),
        patch("urllib.request.urlretrieve") as mock_retrieve,
    ):
        seeder.seed_database(
            db_path=db_file,
            sql_path=BASE_DIR / "database" / "create_tables.sql",
            sprites_dir=sprites_dir,
            large_dir=large_dir,
            max_pokemon=2,
        )
        # Files already existed locally, so urlretrieve should not have been called
        mock_retrieve.assert_not_called()

    conn = sqlite3.connect(str(db_file))
    try:
        cur = conn.cursor()
        assert cur.execute("SELECT COUNT(*) FROM trainers").fetchone()[0] == 1
        rows = cur.execute("SELECT id, name, Type1, Type2, description FROM pokemon ORDER BY id").fetchall()
        assert rows == [
            (1, "bulbasaur", "grass", "poison", "Bulbasaur Gen 1 text."),
            (2, "ivysaur", "grass", "poison", "Ivysaur Gen 1 text."),
        ]
        evos = cur.execute("SELECT from_pokemon, to_pokemon FROM evolutions").fetchall()
        assert evos == [(1, 2)]
    finally:
        conn.close()


def test_caught_toggle_persistence_and_trainer_card(qapp, temp_db):
    """Verify PokemonPage displays all fields, persists caught toggles in SQLite, and TrainerCardPage updates on showEvent."""
    app_win = pokedex_main.PokedexApp(db_path=temp_db)
    try:
        pokemon_page = app_win.pokemon_page
        pokemon_page.load_pokemon(1)

        assert pokemon_page.id_label.text() == "#001"
        assert pokemon_page.name_label.text() == "Bulbasaur"
        assert pokemon_page.type1_label.text() == "Grass"
        assert pokemon_page.type2_label.text() == "Poison"
        assert pokemon_page.description_label.wordWrap() is True
        assert "strange seed" in pokemon_page.description_label.text()
        assert "Ivysaur" in pokemon_page.evolutions_label.text()
        assert len(pokemon_page.evolution_buttons) == 1
        assert pokemon_page.caught_button.isChecked() is False

        # Toggle caught ON via button click
        pokemon_page.caught_button.click()
        assert pokemon_page.caught_button.isChecked() is True

        # Verify persistence in SQLite via a separate connection
        with sqlite3.connect(str(temp_db)) as check_conn:
            caught_val = check_conn.execute(
                "SELECT caught FROM pokemon WHERE id = 1"
            ).fetchone()[0]
            assert caught_val == 1

        # Verify TrainerCardPage updates dynamically on showEvent
        trainer_page = app_win.trainer_card_page
        trainer_page.showEvent(QShowEvent())
        assert trainer_page.name_label.text() == "Name: ASH"
        assert trainer_page.badges_label.text() == "Badges: 3"
        assert trainer_page.caught_label.text() == "Caught: 1"

        # Toggle caught OFF and verify persistence
        pokemon_page.caught_button.click()
        assert pokemon_page.caught_button.isChecked() is False
        with sqlite3.connect(str(temp_db)) as check_conn:
            caught_val = check_conn.execute(
                "SELECT caught FROM pokemon WHERE id = 1"
            ).fetchone()[0]
            assert caught_val == 0

        trainer_page.showEvent(QShowEvent())
        assert trainer_page.caught_label.text() == "Caught: 0"
    finally:
        app_win.close()


def test_navigation_and_no_widget_leaks(qapp, temp_db):
    """Verify PokedexPage has no outer QScrollArea, arrow navigation does not auto-open pages, and PokemonPage is reused without leaks."""
    app_win = pokedex_main.PokedexApp(db_path=temp_db)
    try:
        pokedex_page = app_win.pokedex_page
        stacked = app_win.stacked_widget
        initial_widget_count = stacked.count()

        # Verify redundant outer QScrollArea was removed
        assert len(pokedex_page.findChildren(QScrollArea)) == 0

        # Navigate to PokedexPage
        stacked.setCurrentWidget(pokedex_page)
        assert stacked.currentWidget() is pokedex_page

        # Changing currentRow (Up/Down arrow selection) should NOT switch pages
        pokedex_page.pokemon_list.setCurrentRow(0)
        pokedex_page.pokemon_list.setCurrentRow(1)
        assert stacked.currentWidget() is pokedex_page
        assert stacked.count() == initial_widget_count

        # Activating items repeatedly should reuse the single PokemonPage instance without adding widgets
        item0 = pokedex_page.pokemon_list.item(0)
        pokedex_page.pokemon_list.itemActivated.emit(item0)
        assert stacked.currentWidget() is app_win.pokemon_page
        assert app_win.pokemon_page.current_pokemon_id == 1
        assert stacked.count() == initial_widget_count

        # Navigate via evolution button to Ivysaur (#2)
        app_win.pokemon_page.evolution_buttons[0].click()
        assert app_win.pokemon_page.current_pokemon_id == 2
        assert app_win.pokemon_page.name_label.text() == "Ivysaur"
        assert stacked.count() == initial_widget_count

        # Return to PokedexPage and activate another Pokémon (#4 Charmander)
        app_win.pokemon_page.back_button.click()
        assert stacked.currentWidget() is pokedex_page

        item2 = pokedex_page.pokemon_list.item(2)
        pokedex_page.pokemon_list.itemActivated.emit(item2)
        assert stacked.currentWidget() is app_win.pokemon_page
        assert app_win.pokemon_page.current_pokemon_id == 4
        assert app_win.pokemon_page.name_label.text() == "Charmander"
        assert app_win.pokemon_page.type2_label.isHidden() is True
        assert stacked.count() == initial_widget_count
    finally:
        app_win.close()


def test_default_pokedex_db_and_base_dir_paths(qapp, monkeypatch, tmp_path):
    """Verify PokedexApp initializes cleanly from any working directory using BASE_DIR."""
    monkeypatch.chdir(tmp_path)
    app_win = pokedex_main.PokedexApp()
    try:
        assert app_win.pokedex_page.pokemon_list.count() == 151
        assert app_win.trainer_card_page.name_label.text().startswith("Name: ")
    finally:
        app_win.close()

