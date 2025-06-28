"""
To overwrite any values in here, create a file at "Config/Robot/LookAt.py", and put the appropriate values in.

e.g. saving the following to "Config/Robot/LookAt.py" will overwrite the priority for sound LookAtItems.

```
CONTRIBUTORS = {
    "sound": {
        "priority": Priority.NOT_VERY_INTERESTED,
        # You need to include all of the contributors config in your override.
        "lifetime": 0.5,
        "clear_after_look": True,
        "lookat_period": (0.6, 0.8),
    },
}
```
"""

from math import radians


class Priority:
    """
    List of interest levels
    """

    REJECT: int = -500
    BORED_OF_THIS_ITEM: int = -200
    NONE: int = 0
    NOT_VERY_INTERESTED: int = 50
    IDLE: int = 100
    FOUND: int = 200
    INTERESTED: int = 300
    VERY_INTERESTED: int = 400
    EXTREMELY_INTERESTED: int = 600
    FOCUSED: int = 800
    REQUESTED: int = 1000
    REQUIRED: int = 2000


# The amount of time that an item will be looked at for is controlled by a mixture of:
#  lookat_period
#  interested_period
#  bored_period
# Ensure lookat_period < interested_period < bored_period, or they can cancel each other out.

# Unless otherwise overriden in CONTRIBUTORS this is the lookat_period for an item.
# This should be short enough to keep the robot reactive, but long enough to stop the robot from
# seeming "glitchy". The two numbers define a random range, this is a common strategy to add some
# variation to the lookat timings which helps to keep the robot feeling natural and less robotic.
DEFAULT_LOOKAT_PERIOD = (0.2, 0.25)  # seconds

# During the interested period, apply this priority change.
INTERESTED_SCORE = Priority.FOUND

# Once the bored_period has elapsed, apply this priority change.
BORED_SCORE = Priority.BORED_OF_THIS_ITEM

# This score is added to the currently active item, for a similar reason to INTERESTED_SCORE.
# By subtly encouraging the robot to stay looking at the same thing, it is more likely to make
# more stable selections of which item to look at.
LAZY_ACTIVE_SCORE = Priority.NOT_VERY_INTERESTED


# Items outside of a specific angular range are sometimes detectable but the robot will look
# ridiculous if it tries to look at them with side-eye. We configure this range here along with
# the scale of the score to remove from the lookat.
ANGLE_OVER_MAX_SCORE = Priority.REJECT
ANGLE_MAX_THETA = radians(
    50
)  # Angle above or below the flat plane of the robot's head.
ANGLE_MAX_PHI = radians(
    70
)  # Angle left or right from the forward plane of the robot's origin.


# Parameters specific to each contributor, for each contributor, you can optionally define:
# - priority: the default score of the items from this contributor
# - lifetime: a limit on how long since the item was detected and can still be selected to look at
# - clear_after_look: if true, the item is cleared after being looked at. Defaults to false.
#      With clear_after_look this item will never be selected to be looked at for longer than its look_at_period
# - lookat_period: random range (min, max) in seconds
#      This is the _minimum_ amount of time the robot will look at this item. After this period the
#      robot will be free to re-evaluate which is the most interesting (highest priority) item to
#      look at, and switch target to that item. This setting helps to smooth out the robot's
#      decision making and prevent the robot from instantly switching between items too quickly.
# - interested_period: random range (min, max) in seconds
#      As the robot is looking at an item there is a period where it will give the item a boost in
#      priority. This is to gently encourage the robot to look at an item for longer if other items
#      are of very similar priority.
# - bored_period: random range (min, max) in seconds
#      After enough time of the robot looking at an item, it will drastically reduce its priority
#      level. This helps to prevent the robot from staring at the same item for too long in a
#      creepy way.
# - only_tags: if set, only consumers matching these tags are used
#      It can be helpful to limit which body parts, which are typically seperate "consumers", are affected by
#      each type of lookat targets
CONTRIBUTORS = {
    "sound": {
        # A sound has high priority, and a short lifetime. It is only looked at briefly when it is fresh.
        "priority": Priority.EXTREMELY_INTERESTED,
        "lifetime": 0.5,
        "clear_after_look": True,
        "lookat_period": (0.6, 0.8),
    },
    "glance": {
        # A glance has high priority - it should be prioritized over most other items. It only affects the eyes.
        "priority": Priority.EXTREMELY_INTERESTED,
        "lifetime": 0.2,
        # Because clear_after_look is set, the time at which we look is entirely the lookat_period
        "clear_after_look": True,
        "lookat_period": (0.3, 0.4),
        "only_tags": ("eyes",),
    },
    # "thinking_look_up": {
    #     # Thinking looking up is REQUIRED priority and a long lifetime as it should usually be disabled
    #     # by the thinking script before that lifetime is done
    #     "priority": Priority.REQUIRED,
    #     "lifetime": 8,
    #     "only_tags": ("eyes",),
    # },
    "look_around": {
        # Lookaround items are very low priority. They should only take effect when nothing else is active.
        # Not cleared_on_look so that there is always something to look at (prevents looking at a
        # rejected item if it was the only target)
        # No lifetime as script is responsible for moving the target when its old
        "priority": Priority.NOT_VERY_INTERESTED,
        "only_tags": ("eyes",),
    },
    "look_around_body": {
        # Lookaround items are very low priority. They should only take effect when nothing else is active.
        # Not cleared_on_look so that there is always something to look at (prevents looking at a
        # rejected item if it was the only target)
        # No lifetime as script is responsible for moving the target when its old
        "priority": Priority.NOT_VERY_INTERESTED,
        "only_tags": ("neck", "torso"),
    },
    "telepresence_click": {
        "priority": Priority.REQUESTED,
        "lifetime": 5,
        "clear_after_look": True,
        "lookat_period": (5, 5),
    },
    "viz_camera": {
        "priority": Priority.EXTREMELY_INTERESTED,
        "lifetime": 0.4,
    },
    "user_request": {
        # User requests (e.g. user says "Please look up") have Very high priority, and quite a long lifetime
        "priority": Priority.REQUESTED,
        "lifetime": 0.6,
        "clear_after_look": True,
        "lookat_period": (0.8, 1.0),
    },
    "sequence_gaze_target": {
        # sequence gaze targets have REQUIRED priority, and must be explicitly cancelled by scripts
        "priority": Priority.REQUIRED,
        "only_tags": ("eyes",),
    },
    "faces": {
        # Faces have quite high priority, and no lifetimes (they are explicitly dropped by the script) which
        # manages them. They are interesting when new, and get boring after being looked at for a while.
        "priority": Priority.INTERESTED,
        "bored_period": (5, 10),
        "interested_period": (2, 3),
    },
    "drawing_board_lookat": {
        # Drawing board item has the same priority as a face - the idea is that the robot will look between
        # it and the faces in front of it
        "priority": Priority.VERY_INTERESTED,
        "bored_period": (3, 6),
        "interested_period": (2, 3),
        "lookat_period": (1.5, 2),
    },
    "cameras": {
        # Cameras taking pictures of the robot have high priority, and no lifetimes (they are explicitly
        # dropped by the script) which manages them. They are interesting when new, and get boring
        # after being looked at for a while.
        "priority": Priority.FOCUSED,
        "bored_period": (8, 10),
        "interested_period": (4, 7),
    },
    "look_at_target": {
        # Persistent user-initiated look at targets from scripts
        "priority": Priority.REQUESTED,
    },
}


# Glance configuration
GLANCES_PERIOD_RANGE = (2, 4)  # Seconds
GLANCES_X_DIST = 5  # The range and distances are in meters.
GLANCES_Y_RANGE = (1, 2)  # This creates a square to look at X_DIST away
GLANCES_Z_RANGE = (-0.8, 0.8)


# Sound lookaround configuration
SOUND_COOLDOWN_TIME = 2  # Cooloff time for sounds from a given direction
SOUND_DIFF_THRESHOLD = 5  # Difference threshold for sounds from the same direction


# The lookaround contributor is designed to give the robot somewhere to look when there
# is nothing else particularly interesting to look at. It tries to get the robot to look
# around its space to increase the chances of the robot detecting people it might not
# be currently looking at.
# The delay defines how long to wait before changing locations
LOOKAROUND_DELAY = (1.4, 4)  # Seconds
# The following ranges form a rectangle 2 meters away that points will be chosen on.
# This range defines how far left/right the robot should look/scan
LOOKAROUND_Y_RANGE = (-2, 2)  # meters
# This range defines how high/low the robot should look (the robot thinks it' about 1.6m tall)
LOOKAROUND_Z_RANGE = (1.3, 1.8)  # meters
LOOKAROUND_N_Y_ZONES = 3  # These split up the 'square' into sub-sections to look at
LOOKAROUND_N_Z_ZONES = 2
LOOKAROUND_ZONE_COOLDOWN_TIME = 5  # Seconds

# The body lookaround contributor is designed to give an idly looking around robot a gentle
# movement side to side for the torso. If the torso simply follows the (fast) eyes it is hard
# to get both fast reactive movement for important targets (like people/sounds) as well as
# having a natural idle movement.
BODY_LOOKAROUND_DELAY = (2, 5)
BODY_LOOKAROUND_Y_RANGE = (-1.5, 1.5)
BODY_LOOKAROUND_MAX_MOVEMENT = 1
BODY_LOOKAROUND_Z_RANGE = (1.65, 1.85)

# The Neck movement tries to stick in one place and avoid many tiny micro-adjustments
# This helps give the head "weight" and reinforces the natural eyes-first movement for look-at.
# The neck "sticks" when the movement speed is below a certain amount.
# The angle is how far an adjustment should be before we consider un-sticking.
NECK_STICKY_ANGLE = 8  # degrees
# The duration is the maximum amount of time we're sticky for.
NECK_STICKY_DURATION = 4  # seconds

# Simple neck movement ranges and adjustments
# We scale down the head moves as it feels natural for the eyes to turn further
NECK_YAW_SCALER = 0.75
NECK_YAW_MIN = -65  # degrees
NECK_YAW_MAX = 65  # degrees
NECK_PITCH_SCALER = 0.6
NECK_PITCH_MIN = -17  # degrees
NECK_PITCH_MAX = 10  # degrees

# Sometimes a robot's demeanor is more characterful with a persistently raised/lowered head
# Positive values raise the head and create a "looking down the nose" effect
# Negative values lower the head and create an aggresive effect
NECK_PITCH_OFFSET = 0  # degrees
