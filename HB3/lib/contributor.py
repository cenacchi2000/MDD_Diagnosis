from abc import abstractmethod
from time import time_ns as time_unix_ns
from time import monotonic
from random import uniform
from typing import List, Union, Callable, Iterable, Optional
from collections import OrderedDict
from dataclasses import dataclass

from tritium.world.geom import Ray3, Point2, Point3

sh_obj = system.import_library("./shared_objects.py")

LOOKAT_CONFIG = system.import_library("../../Config/LookAt.py").CONFIG


# How do we specify distance if we give a Vector2... do we need to?
# Is asking "do we need to" demonstrating the issue at hand?
# Trying to change conversion behaviour by type might actually be a pretty ugly solution?
# TODO: Add Rect to this Union once it exists for auto-saccades ;)
LookGeom = Union[Point2, Point3]


@dataclass(frozen=True)
class ContributorConfig:
    channel: str
    name: str
    identifier: str
    lookat_period: tuple[
        float, float
    ]  # The (min, max) time a lookat item must be looked at for (uniformly distributed).
    # If this is set to None, the minimum lookat time is taken to be the default value.
    reference_frame: Union[int, str] = system.world.ROBOT_SPACE
    clear_after_look: bool = (
        False,
    )  # If true, the item is cleared after being looked at for the lookat_period.
    # If false, the item will not get cleared, but the robot may choose ot look at a different higher priority item.
    lifetime: Optional[float] = (
        None  # The lifetime of the lookup item in seconds. Sample time must be defined when this is defined. An item is automatically dropped at sample_time + lifetime.
    )
    only_tags: tuple[str] = ()


@dataclass
class WorldLookupItemPosition:
    """A LookAtItem position and saccades which have been converted in the world reference frame."""

    position: Point3
    """
    List of locations to saccade between, if relevant
    TODO: Can also be a boolean to ask the lookat engine to randomly saccade.
    """
    saccades: Optional[List[Point3]] = None


@dataclass
class LookAtItem:
    identifier: str
    position: LookGeom
    """
    List of locations to saccade between, if relevant
    TODO: Can also be a boolean to ask the lookat engine to randomly saccade.
    """
    saccades: Optional[List[LookGeom]] = None
    """
    Estimated distance of Vector2 positions
    """
    distance: Optional[float] = None
    """
    The time in unix nanoseconds that the observation was made, used when converting
    reference frames.
    """
    sample_time_ns: Optional[int] = None
    config: Optional[ContributorConfig] = None
    world_position_cache: Optional[WorldLookupItemPosition] = None


class Contributor(sh_obj.SharedObject):
    identifier: str
    config: ContributorConfig

    def __init__(
        self,
        channel: str,
        name: str,
        reference_frame: Union[int, str] = system.world.ROBOT_SPACE,
    ):
        super().__init__(f"look-at-contrib-{channel}")
        self.identifier = id(self)

        contrib_config = LOOKAT_CONFIG["CONTRIBUTORS"].get(name, {})

        # Currently configs can only be set per-contributor, and are not adjustable per-item
        self.config = ContributorConfig(
            channel=channel,
            name=name,
            identifier=self.identifier,
            clear_after_look=contrib_config.get("clear_after_look", False),
            reference_frame=reference_frame,
            lifetime=contrib_config.get("lifetime", None),
            lookat_period=contrib_config.get(
                "lookat_period", LOOKAT_CONFIG["DEFAULT_LOOKAT_PERIOD"]
            ),
            only_tags=contrib_config.get("only_tags", ()),
        )

        self._items = {}

    def add(self, item: LookAtItem):
        self._items[item.identifier] = item
        item.config = self.config

    def remove(self, item: Union[str, LookAtItem]):
        if isinstance(item, LookAtItem):
            del self._items[item.identifier]
        else:
            del self._items[item]

    def update_config(
        self,
        reference_frame: Optional[Union[int, str]] = None,
    ):
        config = self.config
        self.config = ContributorConfig(
            channel=config.channel,
            name=config.name,
            identifier=config.identifier,
            clear_after_look=config.clear_after_look,
            reference_frame=(
                reference_frame if reference_frame else config.reference_frame
            ),
            lifetime=config.lifetime,
            lookat_period=config.lookat_period,
            only_tags=config.only_tags,
        )

    def update(self, items: Iterable[LookAtItem]):
        old_keys = set(self._items.keys())
        for item in items:
            ident = item.identifier
            old_keys.discard(ident)
            self._items[ident] = item
            item.config = self.config
        for k in old_keys:
            del self._items[k]

    def clear(self):
        self._items.clear()


class HasConverters:
    def __init__(self):
        self._converters = {}

    def converter(self, from_ref, to_ref):
        k = (from_ref, to_ref)
        if k not in self._converters:
            self._converters[k] = system.world.converter(*k)
        return self._converters[k]

    def convert_item_to_world(self, item: LookAtItem) -> WorldLookupItemPosition:
        converter = self.converter(
            item.config.reference_frame, system.world.ROBOT_SPACE
        )

        position = converter.convert(item.position, item.sample_time_ns)
        saccades = (
            [converter.convert(s, item.sample_time_ns) for s in item.saccades]
            if item.saccades
            else None
        )
        if isinstance(position, Ray3):
            assert (
                item.distance is not None
            ), "Item provided in image frame without distance specified"
            position = position.point(item.distance)
            saccades = (
                [s.point(item.distance) for s in saccades] if item.saccades else None
            )
        return WorldLookupItemPosition(position, saccades)

    def convert(self, item, reference_frame, saccade_index=None) -> Point3:
        world_position = item.world_position_cache
        if world_position is None:
            world_position = self.convert_item_to_world(item)
            item.world_position_cache = world_position

        if saccade_index is None or not world_position.saccades:
            p = world_position.position
        else:
            p = world_position.saccades[saccade_index % len(world_position.saccades)]

        if p is None:
            return None
        converter = self.converter(system.world.ROBOT_SPACE, reference_frame)
        r = converter.convert(p, None)
        if isinstance(r, Ray3):
            # TODO: Resolve distance properly, in the original reference frame...
            r = r.point(2)
        return r


class Consumer(HasConverters, sh_obj.SharedObject):
    def __init__(self, channel):
        self.contributors = sh_obj.SharedObjectSet(f"look-at-contrib-{channel}")
        self.deciders = sh_obj.SharedObjectSet(f"look-at-decider-{channel}")
        HasConverters.__init__(self)
        sh_obj.SharedObject.__init__(self, f"look-at-consumer-{channel}")
        # Runtime data caching
        self.active = None
        self.active_changed_at = monotonic()
        self._current_active_expiration_time = None
        self.items = OrderedDict()

    def _decider(self):
        return min(self.deciders.objects, key=lambda d: d.priority, default=None)

    def _contributors(self):
        yield from self.contributors.objects

    def on_message(self, channel, message):
        self.contributors.on_message(channel, message)
        self.deciders.on_message(channel, message)
        sh_obj.SharedObject.on_message(self, channel, message)

    _max_probed = 0

    def update_choices(self, probe_fn=None):
        old_item_identifiers = set(self.items.keys())
        t_unix_ns = time_unix_ns()
        for c in self._contributors():
            expired = set()
            for key, item in c._items.items():
                full_key = (c.identifier, item.identifier)
                self.items[full_key] = item
                old_item_identifiers.discard(full_key)
                if (
                    # Expire items which have outlived their lifetimes
                    item.config.lifetime is not None
                    and (t_unix_ns - item.sample_time_ns) > item.config.lifetime * 1e9
                ) or (
                    # Also expire items which have a set lookat time and have been looked at
                    item.config.clear_after_look
                    and self.active is not None
                    and item.identifier == self.active.identifier
                    and item.config.identifier == self.active.config.identifier
                ):
                    expired.add(key)
                    continue

            for expired_key in expired:
                c._items.pop(expired_key)

        # Make sure we update the cached active object if the identifier is the same
        # but the LookAtItem object's identity changed
        if self.active:
            new_item = self.items.get(
                (self.active.config.identifier, self.active.identifier), None
            )
            if new_item is not None:
                self.active = new_item

        # First check if we are still within the lookat period
        # If we are, we do not change the choice sorting at all
        t_monotonic = monotonic()
        if (
            self._current_active_expiration_time is not None
            and t_monotonic < self._current_active_expiration_time
        ):
            return

        for key in old_item_identifiers:
            self.items.pop(key)

        # Select the decider to use
        d = self._decider()

        # SPEED: a 2d array here might make more sense, as we know the number of scorers
        scores = [[] for _ in self.items]
        if d is not None:
            for scorer in d._scorers:
                scorer.contrib_score(self, self.items.values(), scores, probe_fn)
        else:
            scores = [[0] for _ in self.items]

        sorted_scores = sorted(
            zip(self.items.values(), scores), key=lambda x: sum(x[1]), reverse=True
        )
        self.items = OrderedDict(
            ((i.config.identifier, i.identifier), i) for i, _score in sorted_scores
        )
        if probe_fn:
            item_length = len(sorted_scores)
            if item_length > self._max_probed:
                self._max_probed = item_length
            for i, (item, s) in enumerate(sorted_scores):
                probe_fn(f"#{i}", [item.identifier, item.config.name, s])
            for i in range(item_length, self._max_probed):
                probe_fn(f"#{i}", [])

        if not sorted_scores:
            self.active = None
            return

        # Update active
        top = sorted_scores[0][0]
        if self.active != top:
            self.active = top
            self.active_changed_at = t_monotonic
            lookat_period = (
                self.active.config.lookat_period
                if self.active.config.lookat_period is not None
                else LOOKAT_CONFIG["DEFAULT_LOOKAT_PERIOD"]
            )
            self._current_active_expiration_time = t_monotonic + uniform(*lookat_period)

    def get_current_position(self, reference_frame, saccade_index=None):
        if self.active is None:
            return None
        return self.convert(self.active, reference_frame, saccade_index)


class ConsumerRef(sh_obj.SharedObjectRef):
    active = None

    def __init__(self, channel):
        super().__init__(f"look-at-consumer-{channel}")

    def get_private_target(self, *, tag=None, ignore_exclusive_tag=None):
        """
        Fetch and remember the current target privately within this consumer.
        By remembering the target we can return a flag when the tag changes.
        """
        c = self.object()
        if not c:
            return None, False, c

        active = None
        if tag is not None:
            # Skip items missing the requested tags (no tags = all tags)
            for item in c.items.values():
                if not item.config.only_tags or tag in item.config.only_tags:
                    active = item
                    break
        elif ignore_exclusive_tag is not None:
            # Skip items tagged solely with the given tag
            # This is to support some consumers wanting to ignore eyes-only items
            tag_tuple = (ignore_exclusive_tag,)
            for item in c.items.values():
                if (
                    not item.config.only_tags
                    or tuple(item.config.only_tags) == tag_tuple
                ):
                    active = item
                    break
        else:
            active = c.active

        changed = False
        if active is not self.active:
            changed = True
            # We check for differences using identifiers instead of identity to allow contributors to rebuild their lists
            if (
                self.active
                and active
                and self.active.config.identifier == active.config.identifier
                and self.active.identifier == active.identifier
            ):
                changed = False

        self.active = active

        return active, changed, c


class Scorer(HasConverters):
    @abstractmethod
    def contrib_score(self, items: Iterable[LookAtItem]) -> Iterable[int]:
        pass


class ListScorer(Scorer):
    @abstractmethod
    def score(
        self,
        consumer: Consumer,
        items: Iterable[LookAtItem],
        probe_fn: Optional[Callable],
    ) -> Iterable[int]:
        pass

    def contrib_score(
        self,
        consumer: Consumer,
        items: Iterable[LookAtItem],
        out: List[List[int]],
        probe_fn: Callable,
    ):
        for o, s in zip(out, self.score(consumer, items, probe_fn)):
            o.append(s)


class MapScorer(Scorer):
    @abstractmethod
    def score(
        self, consumer: Consumer, item: LookAtItem, probe_fn: Optional[Callable]
    ) -> int:
        pass

    def contrib_score(
        self,
        consumer: Consumer,
        items: Iterable[LookAtItem],
        out: List[List[int]],
        probe_fn,
    ):
        for o, item in zip(out, items):
            o.append(self.score(consumer, item, probe_fn))


class Decider(sh_obj.SharedObject):
    FALLBACK = 500
    DEFAULT = 100
    OVERRIDE = 50
    MAXIMUM = 10

    # deciders could have priorities, and consumer uses the highest decider?
    # so that old deciders can be left running but never really used?
    def __init__(self, channel: str, priority: int, scorers: List[Scorer]):
        super().__init__(f"look-at-decider-{channel}")

        self._scorers = scorers
        self._channel = channel
        self.priority = priority

    # impl contrib_score so that there can be a Decider hierarchy?
    # No, if we do this, have a scorer type that wraps a decider, so that output can be weighted