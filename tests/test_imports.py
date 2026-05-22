import importlib
from pathlib import Path


def test_every_src_module_imports():
    for path in sorted(Path("src").glob("*.py")):
        if path.name == "__init__.py":
            continue
        importlib.import_module(f"src.{path.stem}")
