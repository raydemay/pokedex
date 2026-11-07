from concurrent.futures import ThreadPoolExecutor
import sqlite3
import urllib.request
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pokedex.db"
SQL_PATH = BASE_DIR / "database" / "create_tables.sql"
SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "sprites"
SHINY_DIR = BASE_DIR / "images" / "pokemon" / "shiny"
LARGE_DIR = BASE_DIR / "images" / "pokemon" / "large"


def get_pokemon_data(pokemon_id: int | str) -> dict:
    """Fetch core Pokémon data from PokéAPI."""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def get_pokemon_species_data(pokemon_id: int | str) -> dict:
    """Fetch Pokémon species data (flavor text and evolution parent) from PokéAPI."""
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def clean_flavor_text(text: str) -> str:
    """Remove form-feed and newline characters from PokéAPI flavor text."""
    if not text:
        return ""
    cleaned = text.replace("\f", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(cleaned.split())


def extract_english_description(species_data: dict) -> str:
    """Extract the English Gen 1 flavor text (or fallback English entry) from species data."""
    entries = species_data.get("flavor_text_entries", [])
    gen1_versions = {"red", "blue", "yellow"}

    for entry in entries:
        lang = entry.get("language", {}).get("name")
        version = entry.get("version", {}).get("name")
        if lang == "en" and version in gen1_versions:
            return clean_flavor_text(entry.get("flavor_text", ""))

    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return clean_flavor_text(entry.get("flavor_text", ""))

    return ""


def extract_pokemon_info(pokemon_data: dict, species_data: dict) -> dict:
    """Extract fields required for seeding the pokemon and evolutions tables."""
    pokemon_id = int(pokemon_data["id"])
    name = pokemon_data["name"]
    types = pokemon_data.get("types", [])
    type1 = types[0]["type"]["name"] if types else "normal"
    type2 = types[1]["type"]["name"] if len(types) > 1 else None

    sprites = pokemon_data.get("sprites", {})
    sprite_url = sprites.get("front_default")
    shiny_url = sprites.get("front_shiny")
    large_url = (
        sprites.get("other", {})
        .get("official-artwork", {})
        .get("front_default")
        or sprite_url
    )

    description = extract_english_description(species_data)

    evolves_from = species_data.get("evolves_from_species")
    from_pokemon_name = evolves_from["name"] if evolves_from else None

    return {
        "id": pokemon_id,
        "name": name,
        "type1": type1,
        "type2": type2,
        "image_file": f"{pokemon_id}.png",
        "sprite_url": sprite_url,
        "shiny_url": shiny_url,
        "large_url": large_url,
        "description": description,
        "from_pokemon_name": from_pokemon_name,
    }


def download_image(image_url: str | None, save_path: Path) -> None:
    """Download an image to save_path only if it does not already exist locally."""
    save_path = Path(save_path)
    if save_path.exists() or not image_url:
        return
    save_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(image_url, str(save_path))


def execute_schema(cursor: sqlite3.Cursor, sql_path: Path = SQL_PATH) -> None:
    """Execute SQL statements from create_tables.sql within the current transaction."""
    sql_script = Path(sql_path).read_text(encoding="utf-8")
    for statement in sql_script.split(";"):
        stmt = statement.strip()
        if stmt:
            cursor.execute(stmt)


def _fetch_and_prepare(
    pokemon_id: int, sprites_dir: Path, shiny_dir: Path, large_dir: Path
) -> dict:
    pokemon_data = get_pokemon_data(pokemon_id)
    species_data = get_pokemon_species_data(pokemon_id)
    info = extract_pokemon_info(pokemon_data, species_data)

    download_image(info["sprite_url"], sprites_dir / f"{pokemon_id}.png")
    download_image(info["shiny_url"], shiny_dir / f"{pokemon_id}.png")
    download_image(info["large_url"], large_dir / f"{pokemon_id}.png")
    return info


def seed_database(
    db_path: Path = DB_PATH,
    sql_path: Path = SQL_PATH,
    sprites_dir: Path = SPRITES_DIR,
    large_dir: Path = LARGE_DIR,
    shiny_dir: Path = SHINY_DIR,
    max_pokemon: int = 151,
) -> None:
    """
    Create tables, seed a default trainer if empty, and populate all Gen 1 Pokémon
    and their evolutions in a single SQLite transaction.
    """
    db_path = Path(db_path)
    sql_path = Path(sql_path)
    sprites_dir = Path(sprites_dir)
    large_dir = Path(large_dir)
    shiny_dir = Path(shiny_dir)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=16) as executor:
        futures = [
            executor.submit(
                _fetch_and_prepare, pokemon_id, sprites_dir, shiny_dir, large_dir
            )
            for pokemon_id in range(1, max_pokemon + 1)
        ]
        pokemon_records = [f.result() for f in futures]

    pokemon_records.sort(key=lambda r: r["id"])

    conn = sqlite3.connect(str(db_path))
    try:
        with conn:
            cursor = conn.cursor()
            execute_schema(cursor, sql_path)

            # Seed a default row in trainers if empty
            cursor.execute("SELECT COUNT(*) FROM trainers")
            if cursor.fetchone()[0] == 0:
                cursor.execute(
                    """
                    INSERT INTO trainers (trainer_name, pokemon_caught, badges_earned)
                    VALUES (?, ?, ?)
                    """,
                    ("ASH", 0, 0),
                )

            name_to_id = {}
            for record in pokemon_records:
                name_to_id[record["name"]] = record["id"]
                cursor.execute(
                    """
                    INSERT INTO pokemon (id, name, Type1, Type2, image_file, description)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        Type1 = excluded.Type1,
                        Type2 = excluded.Type2,
                        image_file = excluded.image_file,
                        description = excluded.description
                    """,
                    (
                        record["id"],
                        record["name"],
                        record["type1"],
                        record["type2"],
                        record["image_file"],
                        record["description"],
                    ),
                )

            for record in pokemon_records:
                from_name = record["from_pokemon_name"]
                if from_name:
                    from_id = name_to_id.get(from_name)
                    if from_id is None:
                        cursor.execute(
                            "SELECT id FROM pokemon WHERE name = ?", (from_name,)
                        )
                        row = cursor.fetchone()
                        from_id = row[0] if row else None

                    if from_id is not None:
                        cursor.execute(
                            """
                            INSERT OR IGNORE INTO evolutions (from_pokemon, to_pokemon)
                            VALUES (?, ?)
                            """,
                            (from_id, record["id"]),
                        )
    finally:
        conn.close()


if __name__ == "__main__":
    seed_database()
