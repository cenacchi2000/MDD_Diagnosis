"""The default HB3 config.

To overwrite any values in here, create a file at "Config/Robot/HB3.py", and put the appropriate values in.

e.g. saving the following to "Config/Robot/HB3.py" will overwrite the value for FACE_REC_SERVER_ADDRESS

```
FACE_REC_SERVER_ADDRESS = "0.0.0.0:0000"
```
"""

from enum import Enum
from typing import Optional


class ROBOT_HEAD_TYPES:
    GEN1 = 1
    GEN2 = 2


class ROBOT_TYPES:
    AMECA = 1
    AMECA_DESKTOP = 2
    AMECA_DRAWING = 3


class LED_TYPES(Enum):
    ADDRESSABLE_LEDs = 1
    NON_ADDRESSABLE_LEDs = 2


ROBOT_HEAD_TYPE = ROBOT_HEAD_TYPES.GEN2
ROBOT_TYPE = ROBOT_TYPES.AMECA
LED_TYPE: LED_TYPES = LED_TYPES.ADDRESSABLE_LEDs

NEUTRAL_BODY_POSE: str = "HB3_Body_Neutral"
NEUTRAL_FACE_POSE: str = "EXP_neutral"

# Face recognition address. Set to None to disable face recognition
FACE_REC_SERVER_ADDRESS: Optional[str] = None
PROFILES_SERVER_ADDRESS: Optional[str] = None

# Flappy mouth lipsync is where the robot automatically moves it's mouth based on the volume of
# some audio output streams (such as Telepresence audio). Sometimes depending on the microphone and
# audio settings on the Telepresence operator's PC, you may want to adjust these settings.
# Some text to speech backends might also rely on flappy mouth lipsync if that backend does not
# provide well-timed viseme information.
FLAPPY_SILENCE_THRESHOLD = 0.05  # peak level < than this value will disable flappy
FLAPPY_GAIN: float = 30

# The robot will automatically move it's arms in reaction to audio similarly to the flappy mouth.
# This offers an effect of the robot gesturing automatically as a Telepresence operator speaks.
ARM_MOVE_GAIN: float = FLAPPY_GAIN / 3
