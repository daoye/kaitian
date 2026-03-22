import pathlib
from typing import Final


SCRIPTS_DIR: Final[pathlib.Path] = pathlib.Path(__file__).parent


def load_script(name: str) -> str:
    script_path = SCRIPTS_DIR / f"{name}.js"
    return script_path.read_text(encoding="utf-8")
