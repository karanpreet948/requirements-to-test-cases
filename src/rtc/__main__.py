"""Allows running the package as ``python -m rtc ...``."""

import sys

from rtc.cli import main

if __name__ == "__main__":
    sys.exit(main())
