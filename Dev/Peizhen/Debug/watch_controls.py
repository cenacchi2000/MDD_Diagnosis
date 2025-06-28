"""
Add a short description of your script here

See https://docs.engineeredarts.co.uk/ for more information
"""
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
jaw_yaw = system.control('Jaw Yaw', 'Mesmer Mouth 2', ['demand', 'position'])

jaw_pitch = system.control('Jaw Pitch', None, ['demand', 'position'])
lip_bottom_curl = system.control('Lip Bottom Curl', None, ['demand', 'position'])
lip_bottom_depress_left = system.control('Lip Bottom Depress Left', None, ['demand', 'position'])
lip_bottom_depress_middle = system.control('Lip Bottom Depress Middle', None, ['demand', 'position'])
lip_bottom_depress_right = system.control('Lip Bottom Depress Right', None, ['demand', 'position'])
lip_corner_raise_left = system.control('Lip Corner Raise Left', None, ['demand', 'position'])
lip_corner_raise_right = system.control('Lip Corner Raise Right', None, ['demand', 'position'])
lip_corner_stretch_left = system.control('Lip Corner Stretch Left', None, ['demand', 'position'])
lip_corner_stretch_right = system.control('Lip Corner Stretch Right', None, ['demand', 'position'])
lip_top_curl = system.control('Lip Top Curl', None, ['demand', 'position'])
lip_top_raise_left = system.control('Lip Top Raise Left', None, ['demand', 'position'])
lip_top_raise_middle = system.control('Lip Top Raise Middle', None, ['demand', 'position'])
lip_top_raise_right = system.control('Lip Top Raise Right', None, ['demand', 'position'])

all_ctrls = [
    brow_inner_left, brow_inner_right, brow_outer_left, brow_outer_right, 
    eyelid_lower_left, eyelid_lower_right, eyelid_upper_left, eyelid_upper_right,
    gaze_target_phi, gaze_target_theta, head_pitch, head_roll, head_yaw, jaw_pitch, jaw_yaw,
    lip_bottom_curl, lip_bottom_depress_left, lip_bottom_depress_middle, lip_bottom_depress_right, 
    lip_corner_raise_left, lip_corner_raise_right, lip_corner_stretch_left, lip_corner_stretch_right,
    lip_top_curl, lip_top_raise_left, lip_top_raise_middle, lip_top_raise_right, neck_pitch, neck_roll, nose_wrinkle]

class Activity:

    @system.watch([jaw_pitch, jaw_yaw])
    def on_jaw_ctrl_update(self, changed, *args):
        if jaw_pitch in changed:
            print(f'jaw pitch: {jaw_pitch.demand} | {jaw_pitch.position}')


    
    # @system.watch([brow_inner_left, brow_inner_right, brow_outer_left, brow_outer_right, 
    # eyelid_lower_left, eyelid_lower_right, eyelid_upper_left, eyelid_upper_right,
    # gaze_target_phi, gaze_target_theta, head_pitch, head_roll, head_yaw, jaw_pitch, jaw_yaw,
    # lip_bottom_curl, lip_bottom_depress_left, lip_bottom_depress_middle, lip_bottom_depress_right, 
    # lip_corner_raise_left, lip_corner_raise_right, lip_corner_stretch_left, lip_corner_stretch_right,
    # lip_top_curl, lip_top_raise_left, lip_top_raise_middle, lip_top_raise_right, neck_pitch, neck_roll, nose_wrinkle])
    # def on_all_ctrl_update(self, changed, *args):
    #     demand_to_print, position_to_print = [], []
    #     for ctrl in all_ctrls:
    #         val = ctrl.demand if ctrl in changed else 0
    #         demand_to_print.append(val)
        
    #     print(demand_to_print)
    # @system.watch(brow_inner_left)
    # def on_brow_inner_left_update(self, updates):
    #     for u in updates:
    #         print(f'brow inner left: {u.position}')
   
    @system.watch([brow_inner_left, brow_inner_right, brow_outer_left, brow_outer_right])
    def on_brow_update(self, changed, *args):
        demand_to_print, position_to_print = [], []
        if brow_inner_left in changed:
            demand_to_print.append(brow_inner_left.demand)
            position_to_print.append(brow_inner_left.position)
            # to_print[0], to_print[1] = brow_inner_left.demand, brow_inner_left.position
        
    
    @system.watch([lip_bottom_curl, lip_bottom_depress_left])
    def on_lip_motor_update(self, changed, *args):
        demand_to_print, position_to_print = [], []
        if lip_bottom_curl in changed:
            demand_to_print.append(lip_bottom_curl.demand)
            position_to_print.append(lip_bottom_curl.position)
        if lip_bottom_depress_left in changed:
            demand_to_print.append(lip_bottom_depress_left.demand)
            position_to_print.append(lip_bottom_depress_left.position)
        # print(f'demand: {demand_to_print} \n position: {position_to_print}')
            

        
    def on_start(self):
        pass

    def on_stop(self):
        pass

    def on_pause(self):
        pass

    def on_resume(self):
        pass

    @system.tick(fps=10)
    def on_tick(self):
        pass
