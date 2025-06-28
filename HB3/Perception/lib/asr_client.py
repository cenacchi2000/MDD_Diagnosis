import aiohttp
from tritium.config import Protocol, get_service_config
from tritium.client.client import Client


class SpeechRecognitionClient(Client):
    """
    Client for the Speech Recognition node.
    """

    asr_enabled = False
    asr_paused = False
    manual_mode_enabled = False

    def __init__(
        self,
        owner,
        name="Speech Recognition",
        api_address="ipc:///run/tritium/sockets/speech_recognition",
        **settings,
    ):
        super().__init__(owner=owner, name=name, api_address=api_address, **settings)
        # self.listen_to_heartbeat(change_callback=self.try_restarting_speech_recognition)

    def start_speech_recognition(self):
        self.asr_enabled = True
        self.asr_paused = False
        self.send_api("start_speech_recognition")

    def stop_speech_recognition(self):
        self.asr_enabled = False
        self.asr_paused = False
        self.send_api("stop_speech_recognition")

    def pause_speech_recognition(self):
        if self.asr_enabled:
            self.asr_paused = True
            self.send_api("pause_speech_recognition")

    def resume_speech_recognition(self):
        if self.asr_enabled:
            self.asr_paused = False
            self.send_api("resume_speech_recognition")

    def activate_manual_mode(self):
        """
        Enable manual control of VAD deactivation.
        """
        self.manual_mode_enabled = True
        self.send_api("activate_manual_mode")

    def deactivate_manual_mode(self):
        self.manual_mode_enabled = False
        self.send_api("deactivate_manual_mode")

    def manual_mode_stop_listening(self):
        """
        Deactivates VAD when manual_mode is enabled.
        """
        self.send_api("deactivate_speech_recognition")

    # def try_restarting_speech_recognition(self, *args):
    #     print("Restart detected")
    #     if self.asr_enabled:
    #         self.send_api("start_speech_recognition")
    #         if self.asr_paused:
    #             self.send_api("pause_speech_recognition")
    #         else:
    #             self.send_api("resume_speech_recognition")
    #     else:
    #         self.send_api("stop_speech_recognition")

    async def clone_voice(self, item_id: str, backend: str):
        audio = await self.call_api("get_item_audio", item_id=item_id)
        if audio is None:
            raise RuntimeError(
                f"Can't get audio for ASR item {item_id}, most likely it is already discarded"
            )
        service_config = get_service_config(
            Protocol.HTTP,
            "api/v1/tts/voice/clone",
            "text_to_speech_service_proxy_plugin",
            True,
        )
        if service_config is None:
            raise RuntimeError("TTS credentials are not configured")
        async with aiohttp.ClientSession() as session:
            async with session.post(
                service_config[0].url,
                headers={
                    "x-tritium-system-uuid": service_config[0].identifier,
                    "x-tritium-system-token": service_config[0].token,
                    "x-tritium-service": backend,
                },
                data=audio,
            ) as response:
                if response.status != 200:
                    body = (await response.read()).decode(
                        encoding="utf-8", errors="replace"
                    )
                    raise RuntimeError(
                        f"Failed to clone voice, code: {response.status}, body: {body}"
                    )
                return await response.json()

    async def on_message(self, channel, message):
        pass