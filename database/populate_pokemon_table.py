import sqlite3
import urllib.request
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "database" / "pokedex.db"
SPRITES_DIR = BASE_DIR / "images" / "pokemon" / "sprites"
SHINY_DIR = BASE_DIR / "images" / "pokemon" / "shiny"


def get_pokemon_data(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()  # Get the data as a Python dictionary


def get_pokemon_species_data(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_name}"
    response = requests.get(url, timeout=15)
    response.raise_for_status()
    return response.json()


def clean_flavor_text(text):
    if not text:
        return ""
    cleaned = text.replace("\f", " ").replace("\n", " ").replace("\r", " ")
    return " ".join(cleaned.split())


def extract_english_description(pokemon_species_data):
    if not pokemon_species_data:
        return ""
    entries = pokemon_species_data.get("flavor_text_entries", [])
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


def extract_pokemon_info(pokemon_data, pokemon_species_data=None):
    name = pokemon_data["name"]
    type1 = pokemon_data["types"][0]["type"]["name"]
    type2 = None
    if len(pokemon_data["types"]) > 1:
        type2 = pokemon_data["types"][1]["type"]["name"]
    image_url = pokemon_data["sprites"]["front_default"]
    shiny_image_url = pokemon_data["sprites"].get("front_shiny")
    description = extract_english_description(pokemon_species_data)
    return name, type1, type2, image_url, shiny_image_url, description


def download_image(image_url, save_path):
    if not image_url:
        return
    save_path = Path(save_path)
    if save_path.exists():
        return
    save_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(image_url, str(save_path))


def insert_pokemon_into_db(
    name, type1, type2, image_file, description=None, pokemon_id=None, db_path=DB_PATH
):
    conn = None
    try:
        # 1. Establish a connection to the database
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()  # Create a cursor object to interact with the database

        # 2. Construct and execute the SQL INSERT / UPSERT statement
        if pokemon_id is not None:
            insert_query = """
                INSERT INTO pokemon (id, name, Type1, Type2, image_file, description)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    Type1 = excluded.Type1,
                    Type2 = excluded.Type2,
                    image_file = excluded.image_file,
                    description = excluded.description
            """
            cursor.execute(
                insert_query,
                (int(pokemon_id), name, type1, type2, image_file, description),
            )
        else:
            insert_query = """
                INSERT INTO pokemon (name, Type1, Type2, image_file, description)
                VALUES (?, ?, ?, ?, ?)
            """
            cursor.execute(insert_query, (name, type1, type2, image_file, description))

        # 3. Commit the changes to the database
        conn.commit()  # This saves the changes permanently
        print(f"Inserted {name} into database.")

    except Exception as e:
        print(f"Error inserting {name}: {e}")  # Print any errors that occur

    finally:
        # 4. Close the database connection (important to release resources)
        if conn:
            conn.close()


def main():
    for i in range(1, 152):
        pokemon_name = str(i)  # PokéAPI allows fetching by ID
        pokemon_data = get_pokemon_data(pokemon_name)
        pokemon_species_data = get_pokemon_species_data(pokemon_name)
        (
            name,
            type1,
            type2,
            image_url,
            shiny_image_url,
            description,
        ) = extract_pokemon_info(pokemon_data, pokemon_species_data)

        image_file = SPRITES_DIR / f"{pokemon_name}.png"
        shiny_image_file = SHINY_DIR / f"{pokemon_name}.png"
        download_image(image_url, image_file)
        download_image(shiny_image_url, shiny_image_file)

        image_filename = f"{pokemon_name}.png"
        insert_pokemon_into_db(
            name,
            type1,
            type2,
            image_filename,
            description=description,
            pokemon_id=i,
        )


if __name__ == "__main__":
    main()
