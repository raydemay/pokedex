from __future__ import annotations

import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication

from main import PokedexApp, ROUND_DISPLAY_SIZE


class RoundPokedexApp(PokedexApp):
    """Pokédex interface pre-configured for a 1.75-inch 466x466 round touch display."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        super().__init__(db_path=db_path, round_mode=True)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = RoundPokedexApp()
    window.show()
    sys.exit(app.exec())
