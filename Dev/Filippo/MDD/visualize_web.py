"""Launch the patient results dashboard using the built-in web server.

This module only exposes the :func:`run` function from ``web_dashboard`` so
existing scripts can ``import visualize_web`` without needing Flask or
Matplotlib.  The dashboard uses plain HTML and JavaScript and works in the
Tritium environment.
"""

import os
import sys

# Ensure the web dashboard module can be imported when this script
# is run directly or from another location. The directory containing
# this file isn't a Python package, so we manually add it to sys.path.
try:
    MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:
    MODULE_DIR = os.getcwd()
if MODULE_DIR not in sys.path:
    sys.path.append(MODULE_DIR)

from web_dashboard import run

if __name__ == "__main__":
    run()
