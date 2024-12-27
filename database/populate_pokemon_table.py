import requests
import os
import urllib.request
import sqlite3


def get_pokemon_data(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    response = requests.get(url)
    return response.json()  # Get the data as a Python dictionary


def extract_pokemon_info(pokemon_data):
    name = pokemon_data["name"]
    type1 = pokemon_data["types"][0]["type"]["name"]
    type2 = None
    if len(pokemon_data["types"]) > 1:
        type2 = pokemon_data["types"][1]["type"]["name"]
    image_url = pokemon_data["sprites"]["front_default"]
    # ... extract other fields as needed ...
    return name, type1, type2, image_url


def download_image(image_url, save_path):
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    urllib.request.urlretrieve(image_url, save_path)


def insert_pokemon_into_db(name, type1, type2, image_file):
    try:
        # 1. Establish a connection to the database
        conn = sqlite3.connect("pokedex.db")
        cursor = conn.cursor()  # Create a cursor object to interact with the database

        # 2. Construct the SQL INSERT statement
        insert_query = """
            INSERT INTO pokemon (name, type1, type2, image_file) 
            VALUES (?, ?, ?, ?)
        """
        # Using parameterized SQL helps prevent SQL injection vulnerabilities

        # 3. Execute the INSERT statement with the provided data
        cursor.execute(insert_query, (name, type1, type2, image_file))

        # 4. Commit the changes to the database
        conn.commit()  # This saves the changes permanently
        print(f"Inserted {name} into database.")

    except Exception as e:
        print(f"Error inserting {name}: {e}")  # Print any errors that occur

    finally:
        # 5. Close the database connection (important to release resources)
        if conn:
            conn.close()


def main():
    for i in range(1, 152):
        pokemon_name = str(i)  # PokéAPI allows fetching by ID
        pokemon_data = get_pokemon_data(pokemon_name)
        name, type1, type2, image_url = extract_pokemon_info(pokemon_data)

        image_file = f"images\pokemon\{pokemon_name}.png"
        download_image(image_url, image_file)
        image_filename = f"{pokemon_name}.png"
        insert_pokemon_into_db(name, type1, type2, image_filename)


if __name__ == "__main__":
    main()
