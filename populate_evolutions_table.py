import requests
import os
import urllib.request
import sqlite3


def get_pokedex_id(pokemon_name):
    try:
        conn = sqlite3.connect("pokedex.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM pokemon WHERE name = ?", (pokemon_name,))
        result = cursor.fetchone()  # Fetch the result

        if result:  # Check if a result was found
            pokedex_id = result[0]  # Access the ID if it exists
            return pokedex_id
        else:
            return None  # Return None if the Pokemon is not found

    except Exception as e:
        print(f"Error getting pokedexID for {pokemon_name}: {e}")
        return None

    finally:
        if conn:
            conn.close()


def get_pokemon_data(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_name}"
    response = requests.get(url)
    return response.json()  # Get the data as a Python dictionary


def get_pokemon_species_data(pokemon_name):
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_name}"
    response = requests.get(url)
    return response.json()


def extract_pokemon_info(
    pokemon_data, pokemon_species_data
):  # Add pokemon_species_data as argument
    name = pokemon_data["name"]
    # ... (extract other fields from pokemon_data as before) ...

    # Extract evolution information from pokemon_species_data
    evolves_from_species = pokemon_species_data.get("evolves_from_species")
    if evolves_from_species:
        from_pokemon = evolves_from_species["name"]
        from_pokedex_id = get_pokedex_id(from_pokemon)
        from_pokedex_id = get_pokedex_id(from_pokemon)

        # Check if Pokemon exists in database
        # This is in place for Pokemon like Pichu since this is only gen 1
        if from_pokedex_id is None:  # If not found, skip this evolution
            return None, None
        to_pokedex_id = get_pokedex_id(name)
        # ... (extract condition if needed) ...
        return from_pokedex_id, to_pokedex_id
    else:
        return None, None


def insert_evolution_into_db(from_pokemon, to_pokemon):
    try:
        conn = sqlite3.connect("pokedex.db")
        cursor = conn.cursor()

        insert_query = """
            INSERT INTO Evolutions (from_pokemon, to_pokemon) 
            VALUES (?, ?)
        """

        cursor.execute(insert_query, (from_pokemon, to_pokemon))
        conn.commit()
        print(f"Inserted evolution: {from_pokemon} -> {to_pokemon}")

    except Exception as e:
        print(f"Error inserting evolution: {e}")

    finally:
        if conn:
            conn.close()


def main():
    for i in range(1, 152):
        pokemon_name = str(i)
        pokemon_data = get_pokemon_data(pokemon_name)
        pokemon_species_data = get_pokemon_species_data(pokemon_name)
        from_pokedex_id, to_pokedex_id = extract_pokemon_info(
            pokemon_data, pokemon_species_data
        )

        if from_pokedex_id is not None:
            insert_evolution_into_db(from_pokedex_id, to_pokedex_id)


if __name__ == "__main__":
    main()
