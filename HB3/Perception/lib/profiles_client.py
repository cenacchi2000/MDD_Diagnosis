import asyncio
from typing import Optional

import aiohttp

CONFIG = system.import_library("../../../Config/HB3.py").CONFIG

PROFILES_SERVER_ADDRESS = CONFIG["PROFILES_SERVER_ADDRESS"]


class ProfilesClient:
    MAX_N = 5
    MAX_DISTANCE = 1.0

    def __init__(self):
        try:
            self.server = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=2))
        except Exception:
            self.server = None

    async def get_profile_from_face_embedding(
        self, face_embedding: str
    ) -> Optional[dict]:
        if self.server is None or PROFILES_SERVER_ADDRESS is None:
            return None
        try:
            # Get the face embedding
            async with self.server.get(
                PROFILES_SERVER_ADDRESS + "/profiles",
                params={
                    "face_embedding": face_embedding,
                    "max_n": self.MAX_N,
                    "max_distance": self.MAX_DISTANCE,
                },
            ) as resp:
                response = await resp.json()
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            asyncio.exceptions.TimeoutError,
        ) as e:
            print(e)
            print("Couldn't connect to server. Disconnecting.")
            self.server = None
        print(response)
        if len(response) == 0:
            return None
        if len(response) == 1:
            return response[0]
        else:
            print(f"Ambiguous person: {response}")
            return None

    async def add_profile(self, face_embeddings: list[str], info: dict) -> bool:
        if self.server is None or PROFILES_SERVER_ADDRESS is None:
            return False
        try:
            # First, we post the embedding images
            async with self.server.post(
                PROFILES_SERVER_ADDRESS + "/images",
                json={"embeddings": face_embeddings},
            ) as resp:
                resp_json = await resp.json()
                profile_id = resp_json["profile_id"]
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            asyncio.exceptions.TimeoutError,
        ) as e:
            print(e)
            print("Couldn't connect to server. Disconnecting.")
            self.server = None
            return False

        # Associate the info with the newly created profile
        return await self.update_profile_info(profile_id, info)

    async def update_profile_info(self, profile_id: int, info: dict) -> bool:
        if self.server is None or PROFILES_SERVER_ADDRESS is None:
            return False
        try:
            # Get the face embedding
            async with self.server.patch(
                f"{PROFILES_SERVER_ADDRESS}/profiles/{profile_id}", json={"info": info}
            ) as resp:
                await resp.json()
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            asyncio.exceptions.TimeoutError,
        ) as e:
            print(e)
            print("Couldn't connect to server. Disconnecting.")
            self.server = None
            return False
        return True

    async def delete_profile(self, profile_id: int) -> bool:
        if self.server is None or PROFILES_SERVER_ADDRESS is None:
            return False
        try:
            # Get the face embedding
            async with self.server.delete(
                f"{PROFILES_SERVER_ADDRESS}/profiles/{profile_id}",
            ) as resp:
                await resp.json()
        except (
            aiohttp.client_exceptions.ClientConnectorError,
            asyncio.exceptions.TimeoutError,
        ) as e:
            print(e)
            print("Couldn't connect to server. Disconnecting.")
            self.server = None
            return False
        return True
