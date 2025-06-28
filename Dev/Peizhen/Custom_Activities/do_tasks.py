import random
import time
import asyncio

FACE_REC_DEFAULT_ANS = ["nice to meet you", "how are you"]

TaskDealer = system.import_library('task_dealer.py').TaskDealer
CONST = system.import_library('../const.py')
ENCODING = CONST.ENCODING
ANIM2DURATION = CONST.ANIM2DURATION
CustomTasks = CONST.CustomTasks
ResponseCode = CONST.ResponseCode
# MultimodalTasks = common.MultimodalTasks
# NLPTasks = common.NLPTasks
# chat_mode_manager = common.chat_mode_manager

LANG_CODE = 'eng'


async def on_vqa_resp(response):
    if response[0] == 'None':
        system.messaging.post("tts_say", ["sorry, could you please repeat your question?", LANG_CODE])
        return
    # msg = f"There is {response[0]} in front of you.
    # system.messaging.post("speech_recognized", [msg, "EN"])
    system.messaging.post("tts_say", [response[0], LANG_CODE])

async def on_face_recog(response):
    ans = response[0]
    if ans == 'None':
        r = random.randint(0, 1)
        system.messaging.post("tts_say", [FACE_REC_DEFAULT_ANS[r], LANG_CODE])
        system.messaging.post("play_sequence", 'Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Happy_1.project')
        return
    # msg = # f"I am {name}"
    # system.messaging.post("speech_recognized", [msg, "EN"])
    system.messaging.post("play_sequence", 'Animations.dir/System.dir/Chat Expressions.dir/Chat_G2_Happy_1.project')
    system.messaging.post("tts_say", [ans, LANG_CODE])
    

async def on_vrec_resp(response):
    action = response[0]
    if action == 'None':
        system.messaging.post("tts_say", ['sorry, could you please repeat your question?', LANG_CODE])
        return
    system.messaging.post("tts_say", [f'I see you are {action}', LANG_CODE])


async def on_rag_resp(response):
    res = response[0]
    if res == 'None':
        return
    system.messaging.post("tts_say", [res, LANG_CODE])

async def on_emo_imitation_resp(response):
    # print(f'on emotionimitation resp: {type(response)}, {response}')
    try:
        anim, msg = response
    except ValueError("not enough values to unpack"):
        print(f'response: {response}')
        system.messaging.post("tts_say", ["Could you repeat your question?", LANG_CODE])
    if anim:
        system.messaging.post("play_sequence", anim)
    delay = ANIM2DURATION.get(anim, 0)
    await asyncio.sleep(delay)
    system.messaging.post("tts_say", [msg, LANG_CODE])
   
# async def on_vle_resp(response):
#     print(f'on vle response: {response}')
#     anim = response[0]
#     if anim == 'None':
#         anim = 'Chat Expressions.dir/Chat_G2_Neutral.project'
#     system.messaging.post("play_sequence", anim)


# exprimental function
# async def on_fall_detection_resp(response):
#     print(f'on fall detection resp \n *****')
#     fall = response[0]
#     if fall == 'None':
#         return
#     if int(fall):
#         msg = "Be careful Penny! Are you okay?"
#         # msg = "take care! my darling!"
#         system.messaging.post("tts_say", [msg, "EN"]) 
#         # delay = ANIM2DURATION.get(anim, 0)
#         await asyncio.sleep(2.0)
#         anim = 'Chat Expressions.dir/Chat_G2_Surprised_1.project'
#         system.messaging.post("play_sequence", anim)
        
 
RESP_DISPATCHER = {
    CustomTasks.VQA: on_vqa_resp,
    CustomTasks.FaceRecognition: on_face_recog,
    CustomTasks.VideoRecognition: on_vrec_resp,
    CustomTasks.EmotionImitation: on_emo_imitation_resp,    
}



class Activity:
    def on_start(self):
        self.task_dealer = TaskDealer()  
        self.bufferred_msg = None
        self.start_time = time.time()
        

    def on_stop(self):
        self.task_dealer = None
        self.bufferred_msg = None

    async def on_response(self, response, task_query):  # TODO refine the answer use GPT
        print(f'mq task on response: {response} , task query: {task_query} \n*****')
        res_code, ans = response[0], response[1:]
        # res code: 1, <class 'str'>, Penny, <class 'str'>
      
        if int(res_code) == ResponseCode.KeepSilent:
            return   # if keep silent then do nothing
        task_type = task_query[0]  
        msg = await RESP_DISPATCHER[task_type](ans)
        # TODO workaround
        if task_type == CustomTasks.EmotionImitation:
            anim, _ = ans
            self.bufferred_msg = msg
            self.start_time = time.time() + ANIM2DURATION.get(anim, 3.0)  # say sth after playing expression animation
            


    async def on_message(self, channel, message:list):
        if channel == "deal_ctasks":
            print('^-^ do custom tasks on message: ', message)
            # print('is instance bytes? ', isinstance(message[0], bytes), type(message[0]))
            # assert(isinstance(message[0], bytes), 'message should be a list of bytes-like object')
            # play a thinking anim while waiting for the answer
            # system.messaging.post("play_sequence", 'Chat Expressions.dir/Chat_G2_Confused_1.project')
            resp = await self.task_dealer.deal_custom_tasks(*message)
            await self.on_response(resp, message)
            # await self.on_response([item.decode(ENCODING) for item in resp], [item.decode(ENCODING) for item in message])
        # else:
        #     print(f'do tasks on message from {channel} \n =======')
        
    def on_pause(self):
        pass

    def on_resume(self):
        pass
        
    @system.tick(fps=1)
    def on_tick(self):
        now = time.time()
        if now < self.start_time or now > self.start_time + 15.0:
            return
        if self.bufferred_msg:
            system.messaging.post("tts_say", [self.bufferred_msg, LANG_CODE])
            self.bufferred_msg=None
        return
        
