from concurrent.futures import ThreadPoolExecutor
import sqlite3
import threading
import urllib.request
from pathlib import Path
from PIL import Image
import requests
from requests.adapters import HTTPAdapter

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pokedex.db"
SQL_PATH = BASE_DIR / "database" / "create_tables.sql"
SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "sprites"
SHINY_DIR = BASE_DIR / "images" / "pokemon" / "shiny"
LARGE_DIR = BASE_DIR / "images" / "pokemon" / "large"

_thread_local = threading.local()


def _get_session() -> requests.Session:
    session = getattr(_thread_local, "session", None)
    if session is None:
        session = requests.Session()
        adapter = HTTPAdapter(pool_connections=32, pool_maxsize=32, max_retries=4)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        _thread_local.session = session
    return session


def get_pokemon_data(pokemon_id: int | str) -> dict:
    """Fetch core Pokémon data from PokéAPI."""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    response = _get_session().get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def get_pokemon_species_data(pokemon_id: int | str) -> dict:
    """Fetch Pokémon species data (flavor text and evolution parent) from PokéAPI."""
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
    response = _get_session().get(url, timeout=20)
    response.raise_for_status()
    return response.json()


def clean_flavor_text(text: str) -> str:
    """Remove form-feed and newline characters from PokéAPI flavor text."""
    if not text:
        return ""
    cleaned = text.replace("\f", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(cleaned.split())


def extract_english_description(species_data: dict) -> str:
    """Extract the English flavor text from species data."""
    entries = species_data.get("flavor_text_entries", [])
    classic_versions = {"red", "blue", "yellow", "gold", "silver", "crystal"}

    for entry in entries:
        lang = entry.get("language", {}).get("name")
        version = entry.get("version", {}).get("name")
        if lang == "en" and version in classic_versions:
            return clean_flavor_text(entry.get("flavor_text", ""))

    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return clean_flavor_text(entry.get("flavor_text", ""))

    return ""


def extract_pokemon_info(pokemon_data: dict, species_data: dict) -> dict:
    """Extract fields required for seeding the pokemon and evolutions tables."""
    pokemon_id = int(pokemon_data["id"])
    name = species_data.get("name") or pokemon_data["name"]
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


def _strip_icc_profile(png_path: Path) -> None:
    """Remove legacy iCCP chunks from a PNG file to prevent libpng sRGB warnings in Qt."""
    try:
        with Image.open(png_path) as img:
            if "icc_profile" in img.info:
                cleaned = img.copy()
                cleaned.info.pop("icc_profile", None)
                cleaned.save(png_path, "PNG")
    except Exception:
        pass


def download_image(
    image_url: str | None, save_path: Path, use_session: bool = False
) -> None:
    """Download an image to save_path only if it does not already exist locally."""
    save_path = Path(save_path)
    if save_path.exists() or not image_url:
        return
    save_path.parent.mkdir(parents=True, exist_ok=True)
    if use_session:
        resp = _get_session().get(image_url, timeout=20)
        resp.raise_for_status()
        save_path.write_bytes(resp.content)
    else:
        urllib.request.urlretrieve(image_url, str(save_path))
    _strip_icc_profile(save_path)


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

    download_image(
        info["sprite_url"], sprites_dir / f"{pokemon_id}.png", use_session=True
    )
    download_image(
        info["shiny_url"], shiny_dir / f"{pokemon_id}.png", use_session=True
    )
    download_image(
        info["large_url"], large_dir / f"{pokemon_id}.png", use_session=True
    )
    return info


def seed_database(
    db_path: Path = DB_PATH,
    sql_path: Path = SQL_PATH,
    sprites_dir: Path = SPRITES_DIR,
    large_dir: Path = LARGE_DIR,
    shiny_dir: Path = SHINY_DIR,
    max_pokemon: int = 1025,
) -> None:
    """
    Create tables, seed a default trainer if empty, and populate all Pokémon
    (Generations 1-9) and their evolutions in a single SQLite transaction.
    """
    db_path = Path(db_path)
    sql_path = Path(sql_path)
    sprites_dir = Path(sprites_dir)
    large_dir = Path(large_dir)
    shiny_dir = Path(shiny_dir)

    db_path.parent.mkdir(parents=True, exist_ok=True)

    with ThreadPoolExecutor(max_workers=24) as executor:
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
