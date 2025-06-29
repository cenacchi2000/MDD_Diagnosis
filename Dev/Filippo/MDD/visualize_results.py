import os
import sys

# Ensure local imports work when run directly
try:
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    MODULE_DIR = os.getcwd()
if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

from web_dashboard import run

if __name__ == "__main__":
    run()
