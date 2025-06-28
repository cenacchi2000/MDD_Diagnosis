from math import asin, sqrt, atan2
from time import monotonic
from random import uniform
from typing import Dict, Callable, Iterable, Optional

contributor = system.import_library("../lib/contributor.py")

LOOKAT_CONFIG = system.import_library("../../Config/LookAt.py").CONFIG


class Activity:
    decider = None

    def on_start(self):
        self.decider = contributor.Decider(
            "look",
            contributor.Decider.FALLBACK,
            [
                TypeScorer(),
                AngleScorer(),
                BoredScorer(),
                LazyScorer(),
            ],
        )

    def on_message(self, t, d):
        if self.decider:
            self.decider.on_message(t, d)


class TypeScorer(contributor.MapScorer):
    _unknown_contributors = set()

    def score(self, consumer: contributor.Consumer, item, probe_fn: Optional[Callable]):
        n = item.config.name
        if v := LOOKAT_CONFIG["CONTRIBUTORS"].get(n):
            score = v.get("priority", None)
        else:
            score = None
        if score is None and n not in self._unknown_contributors:
            self._unknown_contributors.add(n)
            if probe_fn:
                probe_fn("unscored contributors", self._unknown_contributors)
        return score or 0


class AngleScorer(contributor.MapScorer):
    """
    Reject items that are too far out of a sensible range.
    """

    rejected_time_by_item: Dict[str, int] = {}
    rejection_cooldown = 0.5  # seconds

    def score(
        self,
        consumer: contributor.Consumer,
        item: contributor.LookAtItem,
        probe_fn: Optional[Callable],
    ):
        now = monotonic()
        v_global = self.convert(item, system.world.ROBOT_SPACE)
        v_head = self.convert(item, "Head")
        if v_global is None or v_head is None:
            return 0
        x, y, z = v_global.elements
        # Account for the height of the robot's head
        z = v_head.elements[2]
        r = sqrt(x * x + y * y + z * z)

        theta = asin(z / r)
        phi = atan2(y, x)

        # remove targets off cooldown
        self.rejected_time_by_item = {
            ident: time
            for ident, time in self.rejected_time_by_item.items()
            if now - time < self.rejection_cooldown
        }

        # add target on cooldown if outside acceptable range
        if (
            abs(theta) > LOOKAT_CONFIG["ANGLE_MAX_THETA"]
            or abs(phi) > LOOKAT_CONFIG["ANGLE_MAX_PHI"]
        ):
            self.rejected_time_by_item[item.identifier] = now

        if probe_fn:
            probe_fn("rejected targets", self.rejected_time_by_item)

        if self.rejected_time_by_item.get(item.identifier):
            return LOOKAT_CONFIG["ANGLE_OVER_MAX_SCORE"]
        return LOOKAT_CONFIG["Priority"].NONE


class BoredScorer(contributor.ListScorer):
    """
    Look for items you have not looked at yet, and reject items you have been looking at a while
    """

    last_time = None
    last_active = None
    time_on_active = 0  # How long have you been looking at the currently active item
    looking_time_by_item = {}  # How long you have looked at an item for

    # The time after which you will get bored of the current item
    bored_time: Optional[int] = None
    # The time after which you will stop being interested by the current item
    interested_time_by_item: Optional[dict[str, int]] = {}

    def score(
        self,
        consumer: contributor.Consumer,
        items: Iterable[contributor.LookAtItem],
        probe_fn: Optional[Callable],
    ):
        # Get time since last score
        time = monotonic()
        time_passed = time - self.last_time if self.last_time is not None else 0
        self.last_time = time

        scores = []
        new_looking_time_by_item = {}
        new_interested_time_by_item = {}

        # Update the time you have been looking at the active item
        if consumer.active:
            contributor_config = LOOKAT_CONFIG["CONTRIBUTORS"].get(
                consumer.active.config.name, {}
            )
            if consumer.active.identifier == self.last_active:
                self.time_on_active += time_passed
            else:
                # Change of target
                self.time_on_active = 0
                bored_time_range = contributor_config.get("bored_period", None)
                self.bored_time = (
                    uniform(*bored_time_range) if bored_time_range else None
                )

            self.last_active = consumer.active.identifier

        for item in items:
            time_spent = self.looking_time_by_item.get(item.identifier, 0)
            if consumer.active is not None and consumer.active.identifier == str(
                item.identifier
            ):
                # Active item
                if (
                    self.bored_time is not None
                    and self.time_on_active > self.bored_time
                ):
                    # Bored of this item. Takes precedence over new items.
                    scores.append(LOOKAT_CONFIG["BORED_SCORE"])
                    continue
                looking_time = time_spent + time_passed
            else:
                looking_time = time_spent
            new_looking_time_by_item[item.identifier] = looking_time

            if item.identifier in self.interested_time_by_item:
                interested_time = self.interested_time_by_item[item.identifier]
            elif (
                item.config.name in LOOKAT_CONFIG["CONTRIBUTORS"]
                and "interested_period"
                in LOOKAT_CONFIG["CONTRIBUTORS"][item.config.name]
            ):
                interested_time = uniform(
                    *LOOKAT_CONFIG["CONTRIBUTORS"][item.config.name][
                        "interested_period"
                    ]
                )
            else:
                interested_time = None

            new_interested_time_by_item[item.identifier] = interested_time

            scores.append(
                LOOKAT_CONFIG["INTERESTED_SCORE"]
                if interested_time is not None and looking_time < interested_time
                else LOOKAT_CONFIG["Priority"].NONE
            )

        if probe_fn:
            probe_fn("boredom", scores)

        self.looking_time_by_item = new_looking_time_by_item
        self.interested_time_by_item = new_interested_time_by_item
        return scores


class LazyScorer(contributor.MapScorer):
    """
    Adds priority to the item that is currently being looked at.

    This means the robot is more "lazy" and avoids darting around between different targets too often.
    """

    def score(
        self,
        consumer: contributor.Consumer,
        item: contributor.LookAtItem,
        probe_fn: Optional[Callable],
    ):
        # Get time since last score
        return (
            LOOKAT_CONFIG["LAZY_ACTIVE_SCORE"]
            if consumer.active is not None
            and consumer.active.identifier == str(item.identifier)
            else LOOKAT_CONFIG["Priority"].NONE
        )


# class CenterScorer(contributor.ListScorer):
#     def score(
#         self,
#         consumer: contributor.Consumer,
#         items: Iterable[contributor.LookAtItem],
#         probe_fn: Optional[Callable],
#     ):
#         # TODO: We don't want to hardcode the eye camera here...
#         scores = [0] * len(items)
#         closest_idx = None
#         closest_dist = None
#         v_half = Vector2([0.5, 0.5])
#         v_half = V2(0.5, 0.5)
#         for idx, item in enumerate(items):
#             v = self.convert(item, "Left Eye Camera")
#             if v is None:
#                 continue
#             if len(v.elements) != 2:
#                 print("AHH", item, v)
#                 continue
#             v = V2(*v.elements)  # __sub__ missing from DDS Vector2
#             dist = (v - v_half).length_squared
#             if closest_idx is None or closest_dist > dist:
#                 closest_dist = dist
#                 closest_idx = idx

#         if closest_idx is not None:
#             scores[closest_idx] = 1

#         return scores