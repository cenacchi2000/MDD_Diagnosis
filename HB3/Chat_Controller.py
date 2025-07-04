from typing import List, Optional
import datetime

"""
System
"""
ROBOT_STATE = system.import_library("./robot_state.py")
robot_state = ROBOT_STATE.state

UTILS = system.import_library("./utils.py")
SCRIPTS_TO_START = [
    "./HB3_Controller.py",
    "./Robot_Default_Reset/Reset_Default_Voice.py",
]
SCRIPTS = [
    "./Perception/Add_Speech.py",
    "./Human_Animation/Anim_Talking_Sequence.py",
]

"""
Action Decider
"""
INTERACTION_HISTORY = system.import_library("./chat/knowledge/interaction_history.py")
ENVIRONMENT_KNOWLEDGE = system.import_library(
    "./chat/knowledge/environment_knowledge.py"
)
"""
Skills
"""
MODE_CONTROLLER = system.import_library("./chat/mode_controller.py")

CONFIG = system.import_library("../Config/Chat.py").CONFIG
HB3_CONFIG = system.import_library("../Config/HB3.py").CONFIG

RULES_BASED_CHATBOT_MODULE = system.import_library("./chat/rules_based_chatbot.py")


CHAT_SYSTEM_TYPE = CONFIG["CHAT_SYSTEM_TYPE"]

MODES_CONFIG_LIB = system.import_library("./modes_config.py")

VOICE_ID_UTIL = system.import_library("./Perception/lib/voice_id_util.py")
REMOTE_STORAGE = system.import_library("../Dev/Filippo/MDD/remote_storage.py")

default_voice_reset_evt = system.event("default_voice_reset")


# @system.bind_to_state_engine_activity("chat_interacting") # Wait for UI to be ready
class Activity:
    silent_mode = False
    mode_controller = None
    MODES = {}

    async def on_start(self):
        if system.persona_manager.current_persona is None:
            if HB3_CONFIG["ROBOT_TYPE"] == HB3_CONFIG["ROBOT_TYPES"].AMECA_DESKTOP:
                log.info("Initialising Ameca_Core_Desktop persona")
                UTILS.start_other_script(system, "../Personas/Ameca_Core_Desktop.py")
            else:
                log.info("Initialising Ameca_Core persona")
                UTILS.start_other_script(system, "../Personas/Ameca_Core.py")
        self.probe_persona()
        if CONFIG["ENABLE_TIMED_INTERACTION_REFRESH"]:
            SCRIPTS.append("./Robot_Default_Reset/Timed_Interaction_Refresh.py")
        for script_path in SCRIPTS + SCRIPTS_TO_START:
            UTILS.start_other_script(system, script_path)

        for mode_module in MODES_CONFIG_LIB.MODE_MODULES:
            if mode_module and mode_module.MODE_NAME in CONFIG["MODES"]:
                mode = mode_module.MODE()
                self.MODES[mode_module.MODE_NAME] = mode
        self.chat_system: CHAT_SYSTEM_TYPE = CONFIG.get("CHAT_SYSTEM")
        ROBOT_STATE.interaction_history.reset()
        VOICE_ID_UTIL.load_know_voice_ids()
        self.telepresence_started = False
        starting_mode = MODES_CONFIG_LIB.STARTING_MODE
        self.mode_controller = (
            MODE_CONTROLLER.ModeController(self.MODES, starting_mode)
            if self.chat_system == CHAT_SYSTEM_TYPE.CHAT_FUNCTION_CALL
            else None
        )
        if self.chat_system == CHAT_SYSTEM_TYPE.RULES_BASED_CHATBOT:
            url: Optional[str] = CONFIG["RULES_BASED_CHATBOT_URL"]
            self.rules = RULES_BASED_CHATBOT_MODULE.RulesBasedChatbot(url)

        probe("Chat System", self.chat_system)
        probe("Speech Mode", None)

    def on_stop(self):
        system.messaging.post("tts_stop", False)
        default_voice_reset_evt.emit(__file__)
        for script_path in SCRIPTS:
            UTILS.stop_other_script(system, script_path)
        self.mode_name = None

    def probe_persona(self):
        if system.persona_manager.current_persona is None:
            return
        probe("Persona Name", system.persona_manager.current_persona.name)
        probe("Robot Name", system.persona_manager.current_persona.robot_name)
        probe("Location", system.persona_manager.current_persona.location)
        probe("Activity", system.persona_manager.current_persona.activity)
        probe("Topics", system.persona_manager.current_persona.topics)
        probe("Personality", system.persona_manager.current_persona.personality.name)
        probe("Default Voice", system.persona_manager.current_persona.default_voice)
        # probe(
        #     "Alternate Voices", system.persona_manager.current_persona.alternate_voices
        # )
        for backend in system.persona_manager.current_persona.backends:
            if "chat" in backend.used_for:
                probe("Backend Chat Model", backend.model)
            if "vision" in backend.used_for:
                probe("Backend Vision Model", backend.model)

    # Update when persona changes
    @system.watch_current_persona()
    def on_current_persona_changed(self):
        ROBOT_STATE.interaction_history.reset()  # Reset interaction history when persona changes
        self.probe_persona()
        self.mode_controller.mode.reset()

    async def on_message(self, channel, message):
        is_interaction: bool = False
        if channel == "speech_recognized":
            system.messaging.post("processing_speech", True)
            speaker: str | None = message.get("speaker", None)
            event = INTERACTION_HISTORY.SpeechRecognisedEvent(
                message["text"], speaker=speaker, id=message.get("id", None)
            )
            # Add ASR events to registered histories
            for active_history in INTERACTION_HISTORY.InteractionHistory.get_registered(
                "TTS"
            ):
                active_history.add_to_memory(event)
            log.info(f"{speaker if speaker else 'User'}: {message['text']}")
            try:
                REMOTE_STORAGE.send_to_server(
                    "conversation_history",
                    timestamp=datetime.datetime.now().isoformat(),
                    speaker=speaker or "user",
                    text=message["text"],
                    id=message.get("id") or "",
                )
            except Exception:
                pass
            is_interaction = True

        if channel == "non_verbal_interaction_trigger":
            event = INTERACTION_HISTORY.NonVerbalInteractionEvent(message)
            # Add non_verbal events to registered histories
            for active_history in INTERACTION_HISTORY.InteractionHistory.get_registered(
                "non_verbal"
            ):
                active_history.add_to_memory(event)
            is_interaction = True

        elif channel == "silent_mode":
            self.silent_mode = message
        elif channel == "telepresence":
            if message.get("type", "") == "session_active":
                self.telepresence_started = message.get("value", False)

        if self.mode_controller is not None:
            await self.mode_controller.on_message(channel, message)
        elif is_interaction:
            await self.react_to_interaction(message)
            robot_state.set_thinking(False)

        # Make sure that we post indicating that we have finished processing speech
        # when we have finished
        if channel == "speech_recognized":
            system.messaging.post("processing_speech", False)

    async def react_to_interaction(self, message: str):
        if self.telepresence_started:
            return

        if self.chat_system == CHAT_SYSTEM_TYPE.RULES_BASED_CHATBOT:
            speech_list: List[RULES_BASED_CHATBOT_MODULE.RulesBasedSpeech] = (
                await self.rules.call_rules_based_chatbot(message)
            )
            for speech in speech_list:
                if speech.animation_path:
                    system.messaging.post("play_sequence", speech.animation_path)
                else:
                    system.messaging.post("tts_say", [speech.speech, "eng"])

    @system.tick(fps=1)
    def on_tick(self):
        probe("Telepresence Started", self.telepresence_started)
        if self.mode_controller is not None:
            probe("Speech Mode", self.mode_controller.mode_name)