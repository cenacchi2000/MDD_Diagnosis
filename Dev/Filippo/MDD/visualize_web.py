"""Launch the patient results dashboard.

This module keeps compatibility with existing scripts that import
``visualize_web`` but avoids dependencies like Flask or Matplotlib.
It simply exposes the ``run`` function from ``web_dashboard`` which
serves the charts using the Python standard library.
See https://docs.engineeredarts.co.uk/ for more information.
"""

from .web_dashboard import run

if __name__ == "__main__":
    run()
