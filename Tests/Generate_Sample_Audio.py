import os
import json
import time
import shutil
import asyncio
from typing import Optional
from dataclasses import dataclass

from tritium.client.client import Client


@dataclass
class Sample:
    text: str
    language: str
    voice: str


SAMPLES = [
    Sample("Ameca, how are you today?", "eng", "Amy"),
    Sample("アメカさん、今日はどうですか？", "jpn", "Mizuki"),
    Sample("阿梅卡，今天怎么样？", "cmn", "Zhiyu"),
    Sample("Ameca, comment vas-tu aujourd'hui ?", "fra", "Celine"),
    Sample("Ameca, wie geht es dir heute?", "deu", "Marlene"),
    Sample("Амека, как ты сегодня?", "rus", "Tatyana"),
    Sample("Ameca ¿cómo estás hoy?", "spa", "Conchita"),
    Sample("Ameca, ce mai faci azi?", "ron", "Carmen"),
]


PARENT_DIR = "/var/run/tritium/tmp/"


class Activity:
    async def on_start(self):
        self._recognized_queue = asyncio.Queue()
        self._said_queue = asyncio.Queue()
        self._asr_client = Client(
            owner=system.unstable.owner,
            name="Speech Recognition",
        )
        self._tts_client = Client(
            owner=system.unstable.owner,
            name="Text To Speech",
        )
        self._stop_asr()
        self._asr_sub = system.world.query_features(name="speech_recognition")
        self._tts_sub = self._tts_client.subscribe_to(
            self._tts_client.make_address("events"),
            self._on_tts_event_message,
            expect_json=True,
            description="TTS events",
        )
        await self._run()

    def _start_asr(self, audio_file: Optional[str] = None):
        self._asr_client.send_api("start_speech_recognition", audio_file=audio_file)

    def _stop_asr(self):
        self._asr_client.send_api("stop_speech_recognition")

    def on_stop(self):
        self._asr_sub.close()
        self._start_asr()
        self._asr_client.disconnect()
        self._asr_client = None
        self._tts_client.disconnect()
        self._tts_client = None

    @system.tick(fps=2)
    async def on_tick(self):
        async for evt in self._asr_sub.async_iter():
            if evt.type in ["speech_recognized", "speech_heard"]:
                self._recognized_queue.put_nowait(evt.text)

    def _on_tts_event_message(self, msg):
        if msg.get("type") == "play_finished":
            self._said_queue.put_nowait(True)

    async def _say(self, text: str, voice="Amy", timeout: float = 3):
        self._tts_client.send_api(
            "say",
            text=text,
            voice=voice,
            engine="Service Proxy",
        )
        # Wait for tts to finish
        start = time.time()
        while time.time() - start < timeout:
            try:
                if self._said_queue.get_nowait():
                    break
            except asyncio.QueueEmpty:
                await asyncio.sleep(0.2)

    async def _get_answer(self, audio_file: Optional[str] = None):
        # Discard all previous answers
        while True:
            try:
                text = self._recognized_queue.get_nowait()
                log.info(f"Discarding previous answer: {text}")
            except asyncio.QueueEmpty:
                break
        self._start_asr(audio_file=audio_file)
        log.info("Waiting for answer")
        answer = await self._recognized_queue.get()
        log.info(f"Got answer: {answer}")
        self._stop_asr()
        return answer

    async def _run(self):
        try:
            await self._say("Please say your name using a single word only.")
            self._name = (await self._get_answer()).strip(" .?!")
            dir = f"{PARENT_DIR}{self._name}"
            shutil.rmtree(dir, ignore_errors=True)
            os.mkdir(dir)
            await self._say(
                f"{self._name}, I will say {len(SAMPLES)} sentences in different languages."
            )
            await self._say("You will have to repeat them.")
            await self._say("Please try to speak without pauses.")
            await self._say(
                "If a sentence is too difficult for you to pronounce, say 'skip'."
            )
            for i in range(len(SAMPLES)):
                sample = SAMPLES[i]
                while True:
                    await self._say(f"Sentence {i + 1}.")
                    await self._say(sample.text, sample.voice)
                    transcription = (
                        await self._get_answer(audio_file=f"{dir}/{i}.raw")
                    ).strip()
                    log.info(f"Ameca heard: {transcription}")
                    if "skip" in transcription.lower():
                        os.remove(f"{dir}/{i}.raw")
                        break
                    await self._say("I heard:")
                    await self._say(transcription, voice=sample.voice)
                    await self._say("Are you satisfied with the result?")
                    proceed = (await self._get_answer()).lower()
                    log.info(f"User is satisfied with the result: {proceed}")

                    if "yes" in proceed:
                        with open(f"{dir}/{i}.json", "w", encoding="utf-8") as file:
                            json.dump(
                                {
                                    "audio_format": "pcm_s16le",
                                    "sample_rate": 16000,
                                    "text": sample.text,
                                    "language": sample.language,
                                    "recognized": transcription,
                                },
                                file,
                                indent=4,
                                ensure_ascii=False,
                            )
                        break
                    else:
                        os.remove(f"{dir}/{i}.raw")
                        if "skip" in proceed:
                            break
                        elif "stop" in proceed:
                            await self._say("Aborted.")
                            self.stop()
                            return
            await self._say("All done.")
        finally:
            self.stop()