import base64
import asyncio
from typing import Optional

DEFAULT_FACE_HEIGHT = 1.7  # In meters
FACE_HEIGHT_EXP_MASS = 0.9


class PerceptionState:
    last_image_bytes: Optional[bytes] = None
    _last_good_image_bytes: Optional[bytes] = None
    _last_good_image_b64: Optional[str] = None
    average_face_height: float = DEFAULT_FACE_HEIGHT

    def __init__(self):
        self._last_good_image_bytes = None
        self._last_good_image_b64 = None

    @property
    def last_good_image_b64(self):
        if self._last_good_image_b64 is not None:
            return self._last_good_image_b64
        elif self._last_good_image_bytes is not None:
            return f"data:image/jpeg;base64,{base64.b64encode(self._last_good_image_bytes).decode('utf-8')}"
        else:
            return None

    @last_good_image_b64.setter
    def last_good_image_b64(self, value: Optional[str]):
        self._last_good_image_b64 = value
        self._last_good_image_bytes = None

    @property
    def last_good_image_bytes(self):
        return self._last_good_image_bytes

    @last_good_image_bytes.setter
    def last_good_image_bytes(self, value: Optional[bytes]):
        self._last_good_image_b64 = None
        self._last_good_image_bytes = value

    def update_face_height(self, height):
        self.average_face_height = (
            FACE_HEIGHT_EXP_MASS * self.average_face_height
            + (1 - FACE_HEIGHT_EXP_MASS) * height
        )

    world_faces = set()

    faces_being_dropped = set()

    def drop_face(self, face):
        # Hold onto a reference for now so it is not destroyed before being closed
        self.faces_being_dropped.add(face)
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            # If there is no event loop, just return. The programme has stopped anyways
            return
        loop.create_task(self.drop_face_async(face))

    async def drop_face_async(self, face):
        await face.cleanup()
        self.faces_being_dropped.remove(face)


perception_state = PerceptionState()