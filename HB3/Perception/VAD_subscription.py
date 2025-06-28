from ea.util.event import WeakEvent


class VAD_subscription:

    def __init__(self):
        self._vad_socket = system.unstable.owner.subscribe_to(
            "ipc:///run/tritium/sockets/speech_recognition_vad",
            self._on_asr_vad,
            expect_json=True,
            description="speech recognition VAD",
        )

        # funcitons to be executed when _on_asr_vad is called
        self.executed_functions = WeakEvent()

    def _on_asr_vad(self, data: dict):
        # Call the functions the dependant scripts require
        self.executed_functions.fire(data)


VAD = VAD_subscription()