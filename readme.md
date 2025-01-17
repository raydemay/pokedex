# Raspberry Pi Pokédex Project

This project aims to create a fun and interactive Pokédex application using a Raspberry Pi Zero 2 W and a small TFT display. The Pokédex will allow users to browse through Pokémon, view their details, and track their "caught" Pokémon, similar to the Pokédex in the Pokémon games and anime.

## Project Goals

- Develop a user-friendly Pokédex application with a graphical interface.
- Display Pokémon sprites, names, types, and other relevant information.
- Allow users to navigate through the Pokédex and select Pokémon to view their details.
- Implement a "Trainer Card" feature to personalize the experience and track progress.
- Integrate with hardware buttons for navigation and interaction.
- Run the application on a Raspberry Pi Zero 2 W with a small TFT display.
- Ensure the Pokédex is fully functional offline.

## Current Progress

- **Database:**

  - Designed and created an SQLite database to store Pokémon data (names, types, evolutions, etc.).
  - Populated the database with information for the first 151 Pokémon (Generation 1) using the PokéAPI.
  - Implemented a `Pokemon` table to store core Pokémon information and an `Evolutions` table to track evolutionary relationships.
  - Created a `Trainer` table to store personalized trainer information for the Trainer Card feature.

- **Application Interface:**

  - Developed a PyQt6 application with a multi-page interface.
  - Implemented a `MainMenu` with buttons to navigate to different sections (Pokédex, Trainer Card, Settings).
  - Created a `PokedexPage` with a scrollable list to display Pokémon and allow selection.
  - Designed a `PokemonPage` to show detailed information for a selected Pokémon (name, image, types, etc.).
  - Implemented a basic `TrainerCardPage` to display trainer information.
  - Added "Back" button functionality to navigate between pages.
  - Applied custom styling using a stylesheet and a custom font.

- **Hardware Integration:**
  - (In progress) Plan to integrate with buttons for navigation and a small speaker for sound effects.

## Next Steps

- Complete the `TrainerCardPage` with additional features (e.g., displaying caught Pokémon, badges).
- Develop the `SettingsPage` with options for sound, display, and other preferences.
- Implement hardware integration with buttons and a speaker.
- Design and 3D print a case for the Raspberry Pi and the TFT display.
- Thoroughly test the application on the Raspberry Pi Zero 2 W.
- Optimize for performance and resource usage on the Pi Zero.

## Repository Structure

- `database/`: Contains the SQL scripts to create and populate the database.
- `images/`: Stores the Pokémon sprite images and other images used in the application.
- `sounds/`: (Planned) Will store sound effects or Pokémon cries.
- `src/`: Contains the Python scripts for the PyQt6 application.
- `README.md`: This file.
- `.gitignore`: Specifies files and folders to be ignored by Git.

This project is still in active development, and new features and improvements will be added over time.

## License

Pokémon and Pokémon character names are trademarks of Nintendo and Game Freak.

## Acknowledgements

- Special thanks to [PokéAPI](https://pokeapi.co/) for providing the data and images used in this application.
- Inspiration from various online resources, including Pokémon fan communities and game guides.
