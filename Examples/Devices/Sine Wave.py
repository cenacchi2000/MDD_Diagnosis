"""
Sine Wave

>>> @device(name=device_name)
... class Activity:
>>> @parameter(type)
... def example_parameter(self):
>>> @example_parameter.setter
>>> @example_parameter.on_demand
"""

from math import pi, sin
from time import time


# run and check in Devices for a "Sine Wave" device
@device(name="Sine Wave")
class Activity:
    _sine = 0
    _frequency = 1

    @parameter("double", min_value=-1, max_value=1)
    def sine(self):
        return self._sine

    @sine.setter
    def set_sine(self, value):
        self._sine = value

    @parameter("double", min_value=0.1, max_value=1)
    def frequency(self):
        return self._frequency

    @frequency.setter
    def set_frequency(self, value):
        self._frequency = value

    @frequency.on_demand
    def frequency_demand(self, value):
        self.set_frequency(value)

    @system.tick(fps=100)
    def on_tick(self):
        t = time()
        f = self._frequency
        self.set_sine(sin(t * 2 * pi * f))