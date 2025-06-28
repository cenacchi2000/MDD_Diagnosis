"""
apply custom poses
"""
import os
import os.path as osp
import pickle
import time
from collections import OrderedDict
UTILS = system.import_library('./utils.py')


gaze_target_phi = system.control('Gaze Target Phi', 'Mesmer Gaze 1', ['demand'])
gaze_target_theta = system.control('Gaze Target Theta', 'Mesmer Gaze 1', ['demand'])

brow_inner_left = system.control('Brow Inner Left', 'Mesmer Brows 1', ['demand', 'position'])
brow_inner_right = system.control('Brow Inner Right', 'Mesmer Brows 1', ['demand', 'position'])
brow_outer_left = system.control('Brow Outer Left', 'Mesmer Brows 1', ['demand', 'position'])
brow_outer_right = system.control('Brow Outer Right', 'Mesmer Brows 1', ['demand', 'position'])

eyelid_lower_left = system.control('Eyelid Lower Left', 'Mesmer Eyelids 1', ['demand'])
eyelid_lower_right = system.control('Eyelid Lower Right', 'Mesmer Eyelids 1', ['demand'])
eyelid_upper_left = system.control('Eyelid Upper Left', 'Mesmer Eyelids 1', ['demand'])
eyelid_upper_right = system.control('Eyelid Upper Right', 'Mesmer Eyelids 1', ['demand'])

head_pitch = system.control('Head Pitch', 'Mesmer Neck 1', ['demand'])
head_roll = system.control('Head Roll', 'Mesmer Neck 1', ['demand'])
head_yaw = system.control('Head Yaw', 'Mesmer Neck 1', ['demand'])
neck_pitch = system.control('Neck Pitch', 'Mesmer Neck 1', ['demand'])
neck_roll = system.control('Neck Roll', 'Mesmer Neck 1', ['demand'])

nose_wrinkle = system.control('Nose Wrinkle', 'Mesmer Nose 1', ['demand'])
jaw_yaw = system.control('Jaw Yaw', 'Mesmer Mouth 2', ['demand'])

jaw_pitch = system.control('Jaw Pitch', None, ['demand'])
lip_bottom_curl = system.control('Lip Bottom Curl', None, ['demand'])
lip_bottom_depress_left = system.control('Lip Bottom Depress Left', None, ['demand'])
lip_bottom_depress_middle = system.control('Lip Bottom Depress Middle', None, ['demand'])
lip_bottom_depress_right = system.control('Lip Bottom Depress Right', None, ['demand'])
lip_corner_raise_left = system.control('Lip Corner Raise Left', None, ['demand'])
lip_corner_raise_right = system.control('Lip Corner Raise Right', None, ['demand'])
lip_corner_stretch_left = system.control('Lip Corner Stretch Left', None, ['demand'])
lip_corner_stretch_right = system.control('Lip Corner Stretch Right', None, ['demand'])
lip_top_curl = system.control('Lip Top Curl', None, ['demand'])
lip_top_raise_left = system.control('Lip Top Raise Left', None, ['demand'])
lip_top_raise_middle = system.control('Lip Top Raise Middle', None, ['demand'])
lip_top_raise_right = system.control('Lip Top Raise Right', None, ['demand'])
# mouth high-level
mouth_anger = system.control('Mouth Anger', 'Mesmer Mouth 2', ['demand'])
mouth_content = system.control('Mouth Content', 'Mesmer Mouth 2', ['demand'])
mouth_disgust = system.control('Mouth Disgust', 'Mesmer Mouth 2', ['demand'])
mouth_fear = system.control('Mouth Fear', 'Mesmer Mouth 2', ['demand'])
mouth_happy = system.control('Mouth Happy', 'Mesmer Mouth 2', ['demand'])
mouth_huh = system.control('Mouth Huh', 'Mesmer Mouth 2', ['demand'])
mouth_joy = system.control('Mouth Joy', 'Mesmer Mouth 2', ['demand'])
mouth_open = system.control('Mouth Open', 'Mesmer Mouth 2', ['demand'])
mouth_sad = system.control('Mouth Sad', 'Mesmer Mouth 2', ['demand'])
mouth_sneer = system.control('Mouth Sneer', 'Mesmer Mouth 2', ['demand'])
mouth_surprise = system.control('Mouth Surprise', 'Mesmer Mouth 2', ['demand'])
mouth_worried = system.control('Mouth Worried', 'Mesmer Mouth 2', ['demand'])


all_ctrls = [
    brow_inner_left, brow_inner_right, brow_outer_left, brow_outer_right, 
    eyelid_lower_left, eyelid_lower_right, eyelid_upper_left, eyelid_upper_right,
    gaze_target_phi, gaze_target_theta, head_pitch, head_roll, head_yaw, jaw_pitch, jaw_yaw,
    lip_bottom_curl, lip_bottom_depress_left, lip_bottom_depress_middle, lip_bottom_depress_right, 
    lip_corner_raise_left, lip_corner_raise_right, lip_corner_stretch_left, lip_corner_stretch_right,
    lip_top_curl, lip_top_raise_left, lip_top_raise_middle, lip_top_raise_right, neck_pitch, neck_roll, nose_wrinkle]

all_ctrls_hlv = [
    brow_inner_left, brow_inner_right, brow_outer_left, brow_outer_right, 
    eyelid_lower_left, eyelid_lower_right, eyelid_upper_left, eyelid_upper_right,
    gaze_target_phi, gaze_target_theta, head_pitch, head_roll, head_yaw, jaw_yaw, 
    mouth_anger, mouth_content, mouth_disgust, mouth_fear, mouth_happy, mouth_huh,
    mouth_joy, mouth_open, mouth_sad, mouth_sneer, mouth_surprise, mouth_worried,
    neck_pitch, neck_roll, nose_wrinkle
]

script_dir = os.path.dirname(os.path.abspath(__file__))

class Activity:
    def get_demand_vals(self):
        print(f'scripts dir: {script_dir}')
        destination = osp.join(script_dir, "../Data/proj_ctrls_0.pkl")
        if osp.exists(destination):
            print(f'file already exists!!!')
            with open(destination, 'rb') as f:
                data = pickle.load(f)
            print(data.keys())
            for proj_name, ctrl_values in data.items():
                print(f'proj: {proj_name}, ctrl_values: {len(ctrl_values)}')

            return data  # {anim: ctrls}
        return {}

    def get_demand_vals_from_prediction(self):
        predicted_cvals = system.import_library('../Data/Predicted_CVals/penny2_hy.py').predicted_cvals
        return predicted_cvals

    def reset(self, on_start=False):
        # # ===== debug =====
        # for anim, ctrls in self.anim_ctrls.items():
        #     if anim == 'System_Angry_3':
        #         self.curr_anim = anim
        #         self.curr_ctrls = ctrls
        #         self.curr_anim_len = len(self.curr_ctrls)
        #         self.curr_idx = 0
        #         return
        # return
        # # =================
        # Penny note: start with neutral anim
        self.curr_anim = 'Neutral' if on_start else next(self.anims_iter, None)
        if self.curr_anim is None:
            print(f'do pose ends!!!')
            return
        self.curr_ctrls = self.anim_ctrls[self.curr_anim]
        self.curr_anim_len = len(self.curr_ctrls)
        self.curr_idx = 0  # index of pose within an animation
        # print(f'reset! curr anim: {self.curr_anim}; len: {self.curr_anim_len}')
        
        
    def do_pose_hlv(self, demand_vals):
        with self.bid.use():
            for i, val in enumerate(demand_vals):
                all_ctrls_hlv[i].demand = float(val)  # convert from np.float32 to float
                probe(f"{i}", all_ctrls_hlv[i].demand)


    def do_pose(self, demand_vals):
        with self.bid.use():
            for i, val in enumerate(demand_vals):
                all_ctrls[i].demand = float(val)

        
    def on_start(self):
        UTILS.stop_other_scripts()
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
        # ======set up data from dataset=====
        self.anim_ctrls = self.get_demand_vals()
        self.anims_iter = iter(self.anim_ctrls.keys())     # 
        # self.ctrl_vals_iter = iter(self.anim_ctrls.values())
        self.reset(on_start=True)
        print(f'do pose start!!!')
        # ====================================
        # ======set up data from model predition=====
        # self.predicted_cvals = self.get_demand_vals_from_prediction()
        # print(f'len self.predicted cvals: {len(self.predicted_cvals)}')
        # self.curr_idx = 0
        # self.curr_anim_len = len(self.predicted_cvals)
        # ============================================
        
       
        # self.do_pose(demand_vals=ctrl_values)

    def on_stop(self):
        mouth_neutral = system.poses.get('Mouth Neutral')
        system.poses.apply(mouth_neutral)
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass


    @system.tick(fps=20)
    def on_tick(self):  # play several animations in a row
        # ------for inference results-------
        # if self.curr_idx >= self.curr_anim_len:
        #     return
        # self.do_pose(self.predicted_cvals[self.curr_idx])
        # self.curr_idx += 1
        # ---------------------------------
        # ------for dataset collection------
        if self.curr_anim is None:
            return
        if self.curr_idx >= self.curr_anim_len:
            # return  # only do the first animation
            self.reset()
            return
        self.do_pose(self.curr_ctrls[self.curr_idx])
        print(f'do pose completed!!{self.curr_anim} : {self.curr_idx}')
        self.curr_idx += 1
            
        # if self.curr_idx >= self.total_len:
        #     return
        # self.do_pose(self.ctrl_values[self.curr_idx])
        # print(f'do pose completed!! cur idx: {self.curr_idx}')
        # self.curr_idx += 1
        # pass
