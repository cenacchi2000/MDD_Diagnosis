from typing import Union, Optional
from dataclasses import dataclass

from tritium.world.geom import Rect, Point2, Point3, Matrix4


@dataclass
class FacePose:
    identifier: int
    detailed_keypoints: list[Point2]
    events: list[str]
    vvad: bool


@dataclass
class DetectedFace:
    identifier: int
    rect: Rect
    confidence: float
    # Right Eye, Left Eye, Nose, Mouth, Right Ear, Left Ear
    keypoints: list[Point2]
    name: Optional[str] = None
    face_pose: Optional[FacePose] = None


@dataclass
class FaceDetection:
    detections: list[DetectedFace]
    frame: str
    time_ns: int


@dataclass
class DetectedFace3D:
    """A world object suitable for visualization."""

    identifier: int
    position: Point3
    saccades: list[Point3]
    orientation: Matrix4
    time_ns: int
    name: Optional[str] = None
    text: Optional[str] = None


@dataclass(frozen=True)
class TTSVoiceInfo:
    name: Union[
        str,
        list[float],  # cloned user voices are represented by a list of embeddings
    ]

    # TTS Node engine e.g. "Service Proxy", "Polly", "espeak"
    engine: str

    # Service Proxy backend (if engine is not Service Proxy, this will be same as engine)
    backend: str

    languages: Optional[list[str]] = None

    def __eq__(self, other) -> bool:
        if other is None or other is False:
            return False
        return (
            self.name == other.name
            and self.engine == other.engine
            and self.backend == other.backend
        )


@dataclass
class SpeechItem:
    speech: str = ""
    language_code: Optional[str] = None
    is_thinking: Union[bool, str] = False
    item_id: Optional[str] = None
    parent_item_id: Optional[str] = None
    purpose: Optional[str] = None


@dataclass
class SpeechBubble:
    text: Optional[str]
    position: Point3
    instance_id: int