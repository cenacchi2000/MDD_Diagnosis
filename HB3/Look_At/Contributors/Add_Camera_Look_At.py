contributor = system.import_library("../../lib/contributor.py")
robot_state = system.import_library("../../robot_state.py").state


class Activity:
    contrib = None

    async def on_start(self):
        self.contrib = contributor.Contributor(
            "look",
            "cameras",
            reference_frame=system.world.ROBOT_SPACE,
        )

        async with system.world.query_features(name="objects") as sub:
            async for s in sub.async_iter():
                self.update_contributor(s)

    def on_stop(self):
        if self.contrib:  # async on_start so we need to check this
            self.contrib.clear()

    def update_contributor(self, objects):
        probe("is_camera_tracking", robot_state.is_camera_tracking)
        if not robot_state.is_camera_tracking:
            self.contrib.clear()
            return

        if objects is None:
            # world feature isn't just empty, it doesnt exist => node offline
            return

        cameras = [obj for obj in objects if obj.class_label == "cellphone"]

        if not cameras:
            self.contrib.clear()
        else:
            time_ns = cameras[0].time_ns

            self.contrib.update(
                [
                    contributor.LookAtItem(
                        identifier=f"object_{cam.class_label}_{cam.identifier}",
                        position=cam.position,
                        sample_time_ns=time_ns,
                    )
                    for cam in cameras
                ]
            )

    def on_message(self, channel, message):
        if self.contrib:
            self.contrib.on_message(channel, message)