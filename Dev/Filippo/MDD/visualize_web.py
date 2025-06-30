"""Launch the patient results dashboard using the built-in web server.

This module only exposes the :func:`run` function from ``web_dashboard`` so
existing scripts can ``import visualize_web`` without needing Flask or
Matplotlib.  The dashboard uses plain HTML and JavaScript and works in the
Tritium environment.
"""

from .web_dashboard import run

if __name__ == "__main__":
    run()
