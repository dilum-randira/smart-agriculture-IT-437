"""Stage 1 check: is the C3 development environment ready?

Run from the backend/ folder with:
    python -m app.c3.check_setup
"""

import importlib
import sys

from app.c3 import config

# (import name, why C3 needs it)
REQUIRED_PACKAGES = [
    ("numpy", "fast maths on arrays of daily values"),
    ("pandas", "reading and cleaning CSV tables of weather / soil data"),
    ("matplotlib", "charts of water balance and schedules"),
    ("sklearn", "water-stress classifier and baselines in later stages"),
    ("pymoo", "NSGA-II multi-objective optimiser"),
    ("fastapi", "C3 API endpoints for C4 and the dashboard"),
    ("pytest", "automatic tests"),
]


def check_python_version() -> bool:
    version = sys.version_info
    print(f"Python version: {version.major}.{version.minor}.{version.micro}")
    if version < (3, 10):
        print("  PROBLEM: please use Python 3.10 or newer (the team uses 3.11).")
        return False
    return True


def check_packages() -> bool:
    all_ok = True
    print("\nPackages:")
    for name, reason in REQUIRED_PACKAGES:
        try:
            module = importlib.import_module(name)
            version = getattr(module, "__version__", "unknown")
            print(f"  OK       {name:<11} {version:<10} -> {reason}")
        except ImportError:
            print(f"  MISSING  {name:<11} -> {reason}")
            all_ok = False
    return all_ok


def check_nsga2_import() -> bool:
    """Only checks that NSGA-II can be imported. It does NOT run it."""
    try:
        from pymoo.algorithms.moo.nsga2 import NSGA2  # noqa: F401
        print("\nNSGA-II class can be imported from pymoo.")
        return True
    except ImportError as error:
        print(f"\nCould not import NSGA-II: {error}")
        return False


def create_data_folders() -> None:
    print("\nData folders:")
    for folder in config.ALL_DATA_FOLDERS:
        folder.mkdir(parents=True, exist_ok=True)
        print(f"  ready    {folder}")


def main() -> None:
    print("=== C3 setup check ===")
    results = [check_python_version(), check_packages(), check_nsga2_import()]
    create_data_folders()

    if all(results):
        print("\nAll good. Your environment is ready for Stage 2.")
    else:
        print("\nSomething is missing. Activate your virtual environment and run:")
        print("  python -m pip install -r requirements-c3.txt")
        sys.exit(1)


if __name__ == "__main__":
    main()
