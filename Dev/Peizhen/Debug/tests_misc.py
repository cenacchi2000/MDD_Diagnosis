"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""
from ea.util.number import clamp, remap
import os.path as osp
import random
from collections import defaultdict
import pickle
import urllib.request
import os
import os.path as osp
mode_conf = system.import_library("../../../HB3/modes_config.py")
ROBOT_STATE = system.import_library("../../../HB3/robot_state.py")
llm_interface = system.import_library("../../../HB3/lib/llm/llm_interface.py")
robot_state = ROBOT_STATE.state
CONST = system.import_library("../const.py")
ENCODING = CONST.ENCODING
CustomTasks = CONST.CustomTasks
SEQUENCE_PATH = "Animations.dir/System.dir/Chat Expressions.dir"


TEXTS = ["The pace of technology is faster than ever before.",
         "For those working in the field of AI, it can be overwhelming just to keep on top of latest developments." ,
         "In an attention economy, it’s become increasingly hard to switch off and it’s only going to get harder as AI becomes our productivity guru, our coach, our friend, our therapist, even our soul-mate."
         "In a world increasingly dominated by AI, where our attention is coupled to a machine, what does it mean to be human? How can we retain the best of human experience at the same time as reaping the benefits of AI?"
         "How should we try to influence the development of tech so that we end up with a society we want to live in, rather than one that’s been designed by accident?",
         # "what do you think?",
        ]
SPEAKERS = ["Prof. Usama Fayyad", "Prof. Jon Whittle", "Scientia Prof. Toby Walsh"]
LLM_TEST_CHANNEL = 'test_llm_run_chat'

jaw_pitch = system.control('Jaw Pitch', None, ['demand'])
brow_inner_left = system.control('Brow Inner Left', 'Mesmer Brows 1', ['demand', 'position'])

class Activity:
    # def get_custom_persona(self):
    #     persona_prompt, llm_model, llm_backend_params, robot_name, language_voice_map = CUSTOM_PERSONA_UTIL.get_llm_persona_info(use_for="chat")
    #     print(f'prompt: \n {persona_prompt}; \n language map: {language_voice_map}')
    def download_data(self):
       
        print(f'os.getcwd: {os.getcwd()}')
        print(os.listdir(osp.join(os.getcwd(),'home/tritium/repos')))
        from pathlib import Path
        home_path = Path.home()
        print(f'home: {Path.home()} \n {os.listdir(home_path)}')
        print(f'repos: {os.listdir(osp.join(home_path, "repos"))}')
        print(f'repos: {os.listdir(osp.join(home_path, "repos/embedded"))}')
        print(f'repos: {os.listdir(osp.join(home_path, "repos/embedded/scripts"))}')
        # current_file_path = os.path.abspath(__file__) # /var/opt/tritium/scripts/Dev/Peizhen/Debug/tests_misc.py
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f'scripts dir: {script_dir}')
        destination = osp.join(script_dir, "../Data/proj_ctrls_2.pkl")
        # if osp.exists(destination):
        #     print(f'file already exists!!!')

        #     with open(destination, 'rb') as f:
        #         data = pickle.load(f)
        #     print(data.keys())
        #     for proj_name, ctrl_values in data.items():
        #         print(f'proj: {proj_name}, ctrl_values: {len(ctrl_values)}')

        #     return
        # return
        url = "https://drive.google.com/file/d/1ZeDVd2JqerAOU8fjlnU_y607DindtaBw/view?usp=sharing"
        # "https://drive.google.com/file/d/1vHF_WIjx_GpnwQKXMq25gsjVTgyRdNH3/view?usp=sharing" prj_1
        #"https://drive.google.com/file/d/1wQRRQ6sciV_fqvaQcPGhOH-mjGxb95Ac/view?usp=sharing" prj_0
        # https://drive.google.com/file/d/1r6RNtUzBf4fdjJpGhsEzqXpeol6NZGs-/view?usp=sharing
       
        file_id = "1ZeDVd2JqerAOU8fjlnU_y607DindtaBw"
        # "1vHF_WIjx_GpnwQKXMq25gsjVTgyRdNH3" prj_1
        # "1wQRRQ6sciV_fqvaQcPGhOH-mjGxb95Ac" # proj_0
        # all: "1uTVMWulX-REv8J9b8NR81fR5wlwdLmvN"
        
        base_url = "https://drive.google.com/uc?export=download&id=" + file_id
        urllib.request.urlretrieve(base_url, destination)
        print("Download complete.")
        # import requests
        # url = "https://mqoutlook-my.sharepoint.com/:u:/g/personal/peizhen_li1_hdr_mq_edu_au/EYMXnyLD-TlOknNLOTZ-h7EBDVW0pECStR677FcrNUlwuA?e=eqgAFn"
        # response = requests.get(url)
        # print(f'resonse: {response.content}')

    async def llm_run_chat(self):
        messages = [
            {"role": "system", "content": "You are participating an AI forum at PAKDD 2025"},
            {"role": "user", "content": """
            Summarize the following remarks provided by the keynote speaker:
            "The pace of technology is faster than ever before.",
         "For those working in the field of AI, it can be overwhelming just to keep on top of latest developments." ,
         "In an attention economy, it’s become increasingly hard to switch off and it’s only going to get harder as AI becomes our productivity guru, our coach, our friend, our therapist, even our soul-mate."
         "In a world increasingly dominated by AI, where our attention is coupled to a machine, what does it mean to be human? How can we retain the best of human experience at the same time as reaping the benefits of AI?"
         "How should we try to influence the development of tech so that we end up with a society we want to live in, rather than one that’s been designed by accident?",
         
            """},
        ]
        response = await llm_interface.run_chat(
            model="gpt-4o", messages=messages
        )
        return response
        
    async def on_message(self, channel, message):
        if channel == 'speech_recognized':
            print(f'inspect history len: {type(ROBOT_STATE.interaction_history)}, {len(ROBOT_STATE.interaction_history)}')
            history = ROBOT_STATE.interaction_history.to_message_list()
            len_history = len(history)
            print(f'len history: {len_history}')
            if len_history:
                print(f'latest: {history[-1]}')
            # print(f'len history: {len(history)} \n {history[-1]}')
        # if channel == LLM_TEST_CHANNEL:
        #     response = await self.llm_run_chat()
        #     print(f'[summary]:\n {response}')
        # pass
        
    def test_prompt_format(self):
        persona_prompt = """
        Your name is {ROBOT_NAME}
        You are a humnoid robot
        """
        robot_name = "Ameca"
        format_mapping = defaultdict(
            str,
            ROBOT_NAME=robot_name,
        )
        persona_prompt = persona_prompt.format_map(format_mapping)
        print(f'persona prompt: {persona_prompt}')
        
    def get_system_persona(self, use_for="vision"): # "chat" or "vision"
        """
        == chat and vision are the same==
        robot_name: Ameca
        llm_model: gpt-4o
        max_tokens: 100; n: 1; frequency_penalty: 0.5; presence_penalty: 0.2; temperature: 0.75;
        logit_bias: {'1008': -100, '112251': -100}   # prevent some tokens from generating
        """
        persona = system.persona_manager.current_persona
        robot_name = persona.robot_name
        print(f'robot name: {robot_name}')
        print(f'location: {persona.location}; activity: {persona.activity}')
        print(f'topics: {persona.topics}')
        persona_prompt = "\n".join([p.value for p in persona.personality.prompts])
        print(f'persons prompt: \n {persona_prompt}')
        for backend in persona.backends:
            if use_for not in backend.used_for:
                continue
            llm_model = backend.model
            llm_backend_params = {param.name: param.value for param in backend.parameters}
            print(f'llm model: {llm_model}; \n llm params: {llm_backend_params}')
            for name, value in llm_backend_params.items():
                print(f'{name}: {value}')

    def test_remap_func(self):
        for val in [0.7, 0.75, 0.8, 0.85, 0.9, 0.99]:
            print(remap(val, 0.5, 1, 1, 0))
        pass
        
    def test_play_sequence(self):
        system.messaging.post(
            "play_sequence",
            osp.join(SEQUENCE_PATH, 'Surprised_3.project')
            # "Animations.dir/System.dir/Chat Expressions.dir/Angry_1.project",
        )

    def test_apply_pose(self):
        # mouth_anger = system.control('Mouth Anger', 'Mesmer Mouth 2', ['demand'])
        # mouth_anger = system.control('Mouth Anger', 'Human Behaviour - Mouth G2', ['demand'])
        mouth_control = system.control('Human Behaviour - Mouth G2', None, ['Mouth Anger'])
        print(f'mouth anger: {mouth_control}')
        with self.bid.use():
            print(f'mouth control: {mouth_control}')
            # print(f'mouth anger demand: {mouth_anger.demand}')
            # mouth_anger.set_property('demand', 0.5)
        # mouth_anger = system.poses.get('Mouth Anger')
        # system.poses.apply(mouth_anger)
        pass

    def test_write_file(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        print(f'scripts dir: {script_dir}')
        filepath = osp.join(script_dir, "../Data/test_write_file.txt")
        if osp.exists(filepath):
            print('file already exists!!!')
            return
        with open(filepath, 'w') as f:
            for s in ['rrrr', 'ttttt', 'yyyy']:
                f.write(f'{s}\n')
        print('write file done!!!')
               
    def on_start(self):
        self.bid = system.arbitration.make_bid(
            specifiers=[
                "Control/Direct Motors/Lip Motors",
                "Control/Direct Motors/Mouth Motors",
                "Control/Mesmer Mouth 2",
                "Control/Mesmer Eyelids 1",
                "Control/Mesmer Neck 1",
                "Control/Mesmer Brows 1",
                "Control/Mesmer Gaze 1",
                "Control/Mesmer Nose 1",   # penny NOTE: pay attention to the namespace 
            ],
            precedence=Precedence.VERY_HIGH,
            bid_type=BidType.ON_DEMAND,
        )
        self.download_data()
        # self.test_write_file()
        # pose_anger = system.poses.get('Mouth Anger')
        # system.poses.apply(pose_anger)
        # self.test_play_sequence()
        # self.test_remap_func()
        # self.test_apply_pose()
        
        # import pickle
        # self.test_play_sequence()
        # await llm_interface.start()
        # system.messaging.post(LLM_TEST_CHANNEL, '')
        # response = llm_interface.run_chat()  # async
        # self.get_custom_persona()
        # self.test_prompt_format()
        # self.get_system_persona()
        
        # system.messaging.post("deal_ctasks", [CustomTasks.EmotionImitation,])
        # system.messaging.post("tts_say", ['nice to meet you', 'eng'])
        # system.messaging.post("speech_recognized", {"speaker": "Penny", "text": "let's chat about AI"})
        # print(f'mode conf starting mode: {mode_conf.STARTING_MODE}')
        pass

    def on_stop(self):
        pose_neutral = system.poses.get('Mouth Neutral')
        system.poses.apply(pose_neutral)
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=60)
    def on_tick(self):
        # with self.bid.use():
        #     print(f'jaw pitch: {jaw_pitch.demand} || brow inner left: {brow_inner_left.demand}')
        
        # if not robot_state.speaking:
        #     system.messaging.post("speech_recognized", {"speaker": random.choice(SPEAKERS), "text": random.choice(TEXTS)})
        pass
