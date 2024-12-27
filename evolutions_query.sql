SELECT 
    p1.name AS from_pokemon_name,  -- Name of the Pokemon that evolves
    p2.name AS to_pokemon_name    -- Name of the evolved form
FROM 
    Evolutions e  -- Start with the Evolutions table
JOIN 
    pokemon p1 ON e.from_pokemon = p1.pokedexid  -- Join with pokemon table for "from" Pokemon
JOIN 
    pokemon p2 ON e.to_pokemon = p2.pokedexid;   -- Join again for "to" Pokemon