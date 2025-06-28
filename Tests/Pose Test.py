class Activity:
    def on_start(self):
        eyelids_wide = system.poses.get("Viseme_M")
        system.poses.apply(eyelids_wide)

    def on_stop(self):
        default_pose = system.poses.get("Viseme_KK")
        print("HI")
        system.poses.apply(default_pose)
