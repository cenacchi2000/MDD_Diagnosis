import re
from abc import abstractmethod
from typing import Any, Type, Callable, Awaitable, TypeAlias
from asyncio import iscoroutinefunction
from contextvars import ContextVar

Action: TypeAlias = Callable[..., Awaitable[str]]

PARENT_ITEM_ID = ContextVar("parent_item_id")


def is_valid_action(func: Any) -> bool:
    if not callable(func):
        return False
    if not iscoroutinefunction(func):
        return False
    return bool(func.__doc__)


class ActionBuilder:
    """Action builder that hold states across interactions"""

    @classmethod
    def get_action_id(cls):
        """convert class name to snake case"""
        interim_string = re.sub(r"[\s\-.]+", "_", cls.__name__)
        snake_case_string = re.sub(r"(?<!^)(?=[A-Z])", "_", interim_string).lower()
        snake_case_string = snake_case_string.strip("_")
        return snake_case_string

    def reset(self):
        """Reset the state of this builder"""
        pass

    @abstractmethod
    def factory(self) -> list[Action]:
        """This will be call on every interaction trigger to update the action"""
        pass


class ActionRegistry:

    _ACTION_REGISTRY: dict[str, Action] = {}
    _ACTION_BUILDER_REGISTRY: dict[str, Type[ActionBuilder]] = {}

    @classmethod
    def register_action(cls, action: Action):
        if not is_valid_action(action):
            raise TypeError(
                f"Attempting to register invalid action: {action}, {type(action)}"
            )
        cls._ACTION_REGISTRY[action.__name__] = action
        return action

    @classmethod
    def register_builder(cls, action_builder):
        if not issubclass(action_builder, ActionBuilder):
            raise TypeError(
                f"Attempting to register invalid ActionBuilder: {action_builder}"
            )
        cls._ACTION_BUILDER_REGISTRY[action_builder.get_action_id()] = action_builder
        return cls

    @classmethod
    def get_ids(cls) -> list[str]:
        return list(cls._ACTION_REGISTRY.keys()) + list(
            cls._ACTION_BUILDER_REGISTRY.keys()
        )

    @classmethod
    def parse(
        cls, action_ids: list[str]
    ) -> tuple[dict[str, Action], dict[str, Type[ActionBuilder]]]:
        return {
            i: cls._ACTION_REGISTRY[i] for i in action_ids if i in cls._ACTION_REGISTRY
        }, {
            i: cls._ACTION_BUILDER_REGISTRY[i]
            for i in action_ids
            if i in cls._ACTION_BUILDER_REGISTRY
        }

    def __init__(
        self,
        action_ids: list[str] = [],
        actions: list[Action] = [],
        builders: list[ActionBuilder] = [],
    ) -> None:
        self.active_actions = {}
        self.active_builders = {}
        self.update(action_ids, replace_builders=True)
        self.active_actions.update({a.__name__: a for a in actions})
        self.active_builders.update({b.get_action_id(): b for b in builders})

    def get(self):
        return [action for _, action in self.active_actions.items()], [
            b for _, b in self.active_builders.items()
        ]

    def get_action(self, action_id: str) -> Action | None:
        return self.active_actions.get(action_id)

    def get_builder(self, builder_id: str) -> ActionBuilder | None:
        return self.active_builders.get(builder_id)

    def update(self, action_ids: list[str], replace_builders: bool = False):
        self.active_actions, builder_classes = self.parse(action_ids)
        if replace_builders:
            self.active_builders = {k: b() for k, b in builder_classes.items()}

        if missing := [
            i
            for i in action_ids
            if i not in self.active_actions and i not in self.active_builders
        ]:
            log.warning(
                f"ActionRegistry.update(): Unable to find the following {missing}"
            )

    def reset(self):
        [b.reset() for _, b in self.active_builders.items()]