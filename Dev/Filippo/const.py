"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""

ENCODING = "utf-8"
SOCK_DEALER_ID = b'task_dealer'

ANIM2DURATION = {
    'Chat Expressions.dir/Chat_G2_Neutral.project': 0,
    'Chat Expressions.dir/Chat_G2_Angry_1.project': 5.0,
    'Chat Expressions.dir/Chat_G2_Angry_2.project': 10.0,
    'Chat Expressions.dir/Chat_G2_Angry_3.project': 3.8,
    'Chat Expressions.dir/Chat_G2_Dislike_1.project': 3.7,
    'Chat Expressions.dir/Chat_G2_Dislike_2.project': 2.4,
    'Chat Expressions.dir/Chat_G2_Fear_1.project': 5.0,
	'Chat Expressions.dir/Chat_G2_Fear_2.project': 10.0,
    'Chat Expressions.dir/Chat_G2_Happy_1.project': 3.6,
	'Chat Expressions.dir/Chat_G2_Happy_2.project': 5.6,
    'Chat Expressions.dir/Chat_G2_Neutral.project': 1.0,
    'Chat Expressions.dir/Chat_G2_Sad_1.project': 4.0,
	'Chat Expressions.dir/Chat_G2_Sad_2.project': 7.8,
    'Chat Expressions.dir/Chat_G2_Surprised_1.project': 10.0,
	'Chat Expressions.dir/Chat_G2_Surprised_2.project': 5.0, }


class CustomTasks:
    VQA = 'VQA'     
    VideoRecognition = 'VideoRecognition' 
    FaceRecognition = 'FaceRecognition'
    EmotionImitation = 'EmotionImitation'  # emotion imitation by gpt-4o


class ResponseCode:
	KeepSilent = 0
	Success = 1
	Fail = 2



    

