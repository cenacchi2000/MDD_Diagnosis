"""
from dataclasses import dataclass
sr = system.import_library("../lib/shared_resources.py")


@dataclass
class Details:
    intensity: str = 0.5
    probability: float = 0.5


@sr.global_resource
@dataclass
class SomethingStatus:
    current_description: str = ""
    details: Details = Details()


# MyActivity.py
SomethingStatus = system.import_library("./my_statuses.py").SomethingStatus

# Must be from within an Activity (automatically unsubscribes when the activity is stopped)
# The handlers are expected to always be methods (like in system.watch)
class MyActivity:
    @SomethingStatus.subscribe()
    def handler(self, status):
        probe("SomethingStatus", status)


# Can be from anywhere
SomethingStatus.set(SomethingStatus())


# Can also be from anywhere
SomethingStatus.get()
"""

import inspect
import weakref
import dataclasses

from ea.util.event import Event


class _GlobalResourceRegistry:
    def __init__(self, identifier, name):
        self.identifier = identifier
        self.name = name
        self.evt = Event()


_resources = weakref.WeakKeyDictionary()


def global_resource(cls):
    """
    Registers a dataclass as a global resource which can be pushed or subscribed to.
    """
    assert dataclasses.is_dataclass(cls)
    assert cls not in _resources

    # We store the value on the cls, not the registry object so that the ref cycles are
    # all contained within the cls, and the key of the WeakKeyDictionary can actually be gc
    # It also means we can have closures here with strong refs to the _GlobalResourceRegistry
    cls.__global__resource__value__ = cls()

    # TODO: The identifier should be: "{script_path.py}:{ClassName}"?
    grr = _resources[cls] = _GlobalResourceRegistry(cls.__name__, cls.__name__)

    @classmethod
    def _component_get(cls):
        return cls.__global__resource__value__

    cls.get = _component_get

    @classmethod
    def _component_set(cls, value):
        assert isinstance(value, cls)
        # TODO: Some sort of validation? Check we're not in a handler to help with infinite loops?
        # TODO: Force serialization before sending to event handlers.
        cls.__global__resource__value__ = value
        grr.evt.fire(value)

    cls.set = _component_set

    @classmethod
    def _component_subscribe(cls):
        def decorator(fn):
            # TODO: Support async functions
            assert not inspect.iscoroutinefunction(
                fn
            ), "global resource subscriptions cannot yet be coroutines"

            # TODO: Fix this for standalone functions as well as methods, or check fn is a method
            handler = None

            def on_start(other_activity):
                nonlocal handler

                def handler(value):
                    fn(other_activity, value)

                grr.evt.handle(handler)

            def on_stop(_other_activity):
                grr.evt.unhandle(handler)

            other_activity = system.hook_into_activity_script_lifecycle(
                inspect.getsourcefile(fn),
                on_start=on_start,
                on_pause=on_stop,
                on_resume=on_start,
                on_stop=on_stop,
            )
            if other_activity:
                on_start(other_activity)

            return fn

        return decorator

    cls.subscribe = _component_subscribe

    return cls


# TODO: Mutation in systems (would require specifying "worlds" for resources and systems, and dependency ordering)
# my_world.system([OtherThing], mutate=[Mood])
# def handler(self, mood):
#     return mood