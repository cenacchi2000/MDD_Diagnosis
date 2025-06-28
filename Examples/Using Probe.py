"""
Using Probe

>>> probe("name", value)
"""

from time import monotonic


class Activity:
    def on_start(self):
        self.started = monotonic()

    @system.tick(fps=10)
    def on_tick(self):
        # Probed variables can be monitored via the "Debug Data" panel in realtime
        probe("time since script started", monotonic() - self.started)
