import tkinter as tk
from tkinter import ttk  # For more modern widgets
from PIL import Image, ImageTk  # For image handling
import sqlite3
import os


class PokedexApp:
    def __init__(self, master):
        self.master = master
        master.title("Pokédex")

        self.conn = sqlite3.connect(r"..\database\pokedex.db")
        self.cursor = self.conn.cursor()

        self.create_widgets()

    def create_widgets(self):
        # Label for displaying Pokémon name
        self.name_label = ttk.Label(self.master, text="Select a Pokémon:")
        self.name_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

        # Combobox for selecting Pokémon
        self.pokemon_combobox = ttk.Combobox(self.master)
        self.pokemon_combobox["values"] = self.get_pokemon_names()
        self.pokemon_combobox.grid(row=1, column=0, columnspan=2, padx=10, pady=10)
        self.pokemon_combobox.bind("<<ComboboxSelected>>", self.display_pokemon_info)

        # Label for displaying the image
        self.image_label = ttk.Label(self.master)
        self.image_label.grid(row=2, column=0, columnspan=2, padx=10, pady=10)

    def get_pokemon_names(self):
        self.cursor.execute("SELECT Name FROM Pokemon")
        return [row[0] for row in self.cursor.fetchall()]

    def display_pokemon_info(self, event=None):
        selected_pokemon = self.pokemon_combobox.get()
        self.cursor.execute(
            "SELECT image_file FROM Pokemon WHERE Name=?", (selected_pokemon,)
        )
        image_file = self.cursor.fetchone()[0]
        image_path = os.path.join("..", "images", "pokemon", image_file)

        try:
            # Load and display the image
            img = Image.open(image_path)
            img = ImageTk.PhotoImage(img)
            self.image_label.config(image=img)
            self.image_label.image = img  # Keep a reference to avoid garbage collection

            self.name_label.config(text=selected_pokemon)
        except FileNotFoundError:
            self.name_label.config(
                text=f"Error: Image not found for {selected_pokemon}"
            )


root = tk.Tk()
app = PokedexApp(root)
root.mainloop()
