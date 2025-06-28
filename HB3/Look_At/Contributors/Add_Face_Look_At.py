from tritium.world.geom import Point3

contributor = system.import_library("../../lib/contributor.py")


class Activity:
    contributor = None

    async def on_start(self):
        self.contributor = contributor.Contributor(
            "look",
            "faces",
            reference_frame=system.world.ROBOT_SPACE,
        )

        async with system.world.query_features(name="faces") as sub:
            async for s in sub.async_iter():
                if s is not None:
                    self.update_contributor(s)

    def on_stop(self):
        if self.contributor:  # async on_start so we check this
            self.contributor.clear()

    def update_contributor(self, faces):
        if len(faces) == 0:
            self.contributor.clear()
        else:
            time_ns = faces[0].time_ns

            def center_squeeze(saccades, center, scale):
                squeezed = []
                for s in saccades:
                    squeezed.append(
                        Point3(
                            [
                                scale * (s.x - center.x) + center.x,
                                scale * (s.y - center.y) + center.y,
                                scale * (s.z - center.z) + center.z,
                            ]
                        )
                    )
                return squeezed

            self.contributor.update(
                [
                    contributor.LookAtItem(
                        identifier=str(face.identifier),
                        position=face.position,
                        sample_time_ns=time_ns,
                        saccades=center_squeeze(face.saccades, face.position, 0.3),
                    )
                    for face in faces
                ]
            )

    def on_message(self, channel, message):
        if self.contributor:
            self.contributor.on_message(channel, message)