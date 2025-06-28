import random

from ea.util.random import random_generator

MIN_INTERVAL = 2
MAX_INTERVAL = 10
MIN_DURATION = 0.075
MAX_DURATION = 0.15


human_behaviour_blink_evt = system.event("human-behaviour-blink")


class Activity:
    _task = None

    ##########################################################################

    def blink(self):
        duration = random.uniform(MIN_DURATION, MAX_DURATION)
        human_behaviour_blink_evt.emit({"duration": duration})

    def on_start(self):
        self._start_task()

    def on_stop(self):
        self._stop_task()

    ##########################################################################

    def _start_task(self):
        self._task = self.ioloop.repeat(
            self.blink,
            random_generator(MIN_INTERVAL, MAX_INTERVAL),
            description="blinking",
        )

    def _stop_task(self):
        if self._task:
            self._task.cancel()