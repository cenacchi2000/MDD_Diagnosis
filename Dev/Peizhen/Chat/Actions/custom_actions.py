"""Actions for interacting with people."""

import os
import re
import html
import asyncio
from typing import List, Literal, Optional

import aiohttp

CONST = system.import_library("../../const.py")
ENCODING = CONST.ENCODING
# ANIM2DURATION = CONST.ANIM2DURATION
CustomTasks = CONST.CustomTasks
ResponseCode = CONST.ResponseCode

STATIC_CONFIG = system.import_library("../../../../Config/Static.py")
INTERACTION_HISTORY = system.import_library("../../../../HB3/chat/knowledge/interaction_history.py")
ROBOT_STATE = system.import_library("../../../../HB3/robot_state.py")
robot_state = ROBOT_STATE.state

TYPES = system.import_library("../../../../HB3/lib/types.py")

voice_cloning = system.import_library("../../../../HB3/lib/voice_cloning.py")

stream_module = system.import_library("../../../../HB3/chat/lib/stream_outputs.py")


CyclingShuffleIterator = system.import_library(
    "../../../../HB3/lib/cycling_shuffle_iterator.py"
).CyclingShuffleIterator

ACTION_UTIL = system.import_library("../../../../HB3/chat/actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action
PARENT_ITEM_ID = ACTION_UTIL.PARENT_ITEM_ID




# @ActionRegistry.register_action
# async def recognize_faces():
#     """
#     Perfrom human face recognition
#     Call this function When someone say hi to Ameca, e.g.,"How are you", "Nice to meet you", "Ameca, how are you", "Ameca, Nice to meet you", "do you remember me?".
#     If the question is: "How do you know my name? " or "How did you recognize me? ", just provide answers like: 
#     "I can do visual reasoning based on what i can see, and thanks to the face recognition model"
#     The function will trigger background task and returns immediately.

#     """
#     print(f"=====\n!!!Do face recognition!!!\n=====")
@ActionRegistry.register_builder
class RecognizeFaces(ActionBuilder):
    def factory(self) -> list[Action]:
        """A factory to generate recognize_faces function."""
        async def recognize_faces():
            """
            Perfrom human face recognition
            For example when someone say hi to Ameca, e.g.,"How are you", "Nice to meet you", "Ameca, how are you", "Ameca, Nice to meet you", "do you remember me?",
            "Can you recognize me", "Do you recognise me" this function must be called.
            """
            system.messaging.post("deal_ctasks", [CustomTasks.FaceRecognition])
            print(f"[DEBUG] ➤ Do face recognition !!! \n=====")  
        return [recognize_faces]
        

@ActionRegistry.register_builder
class RecognizeActionFromVid(ActionBuilder):
    def factory(self) -> list[Action]:
        """A factory to generate recognize_action_from_vid function."""
        async def recognize_action_from_vid():
            """
            Query what happened or what's going on in the view or ask what the person is doing.
            Respond when being asked about what the person is doing. e.g., "what am i doing?", "what is going on?"
            The function will trigger background task and returns immediately.
            """
            system.messaging.post("deal_ctasks", [CustomTasks.VideoRecognition])
            print(f"[DEBUG] ➤ Do action recognition from video!!! \n=====")  
        return [recognize_action_from_vid]

@ActionRegistry.register_builder
class MimicEmotion(ActionBuilder):
    def factory(self) -> list[Action]:
        """A factory to generate mimic_emotion function."""
        async def mimic_emotion():
            """
            Call this function when being asked to imitate or mimic the emotion or facial expression.
            e.g., "can you mimic my emotion?", "can you mimic my facial expression?", 
            "can you imitate my emotion (or facial expression)?", "can you copy my emotion (or facial expression)?"
            """
            system.messaging.post("deal_ctasks", [CustomTasks.EmotionImitation])
            print(f"[DEBUG] ➤ Do emotion imitation!!! \n=====") 
        return [mimic_emotion]
            

    
# async def emotion_imitation_func():
#     """
#     Call this function when being asked to imitate or mimic the emotion or facial expression.
#     e.g., "can you mimic my emotion?", "can you mimic my facial expression?", "can you imitate my emotion?", 
#     "can you copy my emotion", 

#     The function will trigger background task and returns immediately.
    
#     """
#     system.messaging.post('deal_ctasks', [CustomTasks.EmotionImitation.encode(ENCODING)])
#     system.messaging.post('tts_say', ['emotion imitation task triggerred!!!', 'EN'])


