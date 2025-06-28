import io
import asyncio
from typing import Optional

import aiohttp
from PIL import Image

# CONFIG
CONFIG = system.import_library("../../../Config/HB3.py").CONFIG

FACE_REC_SERVER_ADDRESS = CONFIG["FACE_REC_SERVER_ADDRESS"]


class FaceEmbeddingClient:
    def __init__(self):
        try:
            self.server = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2))
        except Exception:
            self.server = None

    async def get_face_embedding(self, image: Image) -> Optional[str]:
        if self.server is None or FACE_REC_SERVER_ADDRESS is None:
            return None

        arr = io.BytesIO()
        image.save(arr, format="PNG")
        arr.seek(0)

        # Prepare a message for the face embedding server
        data = aiohttp.FormData()
        data.add_field("image", arr, content_type="multipart/form-data")

        try:
            # Get the face embedding
            async with self.server.post(FACE_REC_SERVER_ADDRESS, data=data) as resp:
                resp_json = await resp.json()
                return resp_json["embedding"]

        except (
            aiohttp.client_exceptions.ClientConnectorError,
            asyncio.exceptions.TimeoutError,
        ) as e:
            print(e)
            print("Couldn't connect to server. Disconnecting.")
            self.server = None