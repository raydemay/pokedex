-- Create the Pokémon table with necessary fields.
CREATE TABLE IF NOT EXISTS pokemon (
    id INT PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    Type1 VARCHAR(50) NOT NULL,
    Type2 VARCHAR(50),
    image_file VARCHAR(255),
    caught BOOLEAN DEFAULT FALSE,
    description TEXT
);

-- Create table to track evolutions between Pokémon.
CREATE TABLE IF NOT EXISTS evolutions (
    from_pokemon INT,
    to_pokemon INT,
    condition VARCHAR(255), 
    FOREIGN KEY (from_pokemon) REFERENCES pokemon(id),
    FOREIGN KEY (to_pokemon) REFERENCES pokemon(id)
);

-- Create the trainer table to store information about trainers.
CREATE TABLE IF NOT EXISTS trainers (
    trainer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    trainer_name VARCHAR(255) NOT NULL,
    pokemon_caught INTEGER DEFAULT 0,
    badges_earned INTEGER DEFAULT 0
);