from time import time_ns as time_unix_ns

from tritium.world.geom import Rect, Point2

contributor = system.import_library("../../lib/contributor.py")

ActiveSensor = system.import_library("../../robot_state/ActiveSensor.py").ActiveSensor


class Activity:
    contributor = None

    def on_start(self):
        self.contributor = contributor.Contributor(
            "look",
            "telepresence_click",
            reference_frame=ActiveSensor.get().name,
        )

    @ActiveSensor.subscribe()
    def on_sensor_update(self, sensor) -> None:
        # Update the reference frame with the new sensor when a change is found
        self.contributor.update_config(reference_frame=sensor.name)

    def on_stop(self):
        if self.contributor is not None:
            self.contributor.clear()

    def new_item(self, position, time=None):
        if time is None:
            time = time_unix_ns()
        return contributor.LookAtItem(
            identifier="telepresence_click",
            position=position,
            sample_time_ns=time,
            distance=10,
        )

    def on_message(self, channel, message):
        if self.contributor:
            self.contributor.on_message(channel, message)
        if channel != "telepresence":
            return

        msg_type = message["type"]
        if msg_type == "location":
            data = message["data"]

            position = Point2([data["x"], data["y"]])
            self.contributor.update([self.new_item(position)])
            probe("status", "clicked point")
            probe("last_click", "point")

        elif msg_type == "feature_click":
            probe("status", "clicked feature")
            probe("last_click", "feature")
            data = message["data"]
            time = data["time"]

            if data["data"]["_"] == "Rect":
                position = Rect(data["data"]["elements"]).center()
            elif data["data"]["_"] == "Vector2":
                position = Point2(data["data"]["elements"])
            else:
                probe("last_click", "unknown feature")
            # TODO: Prioritise this face in the decider too (global resource probably)
            if position:
                time = data["time"]
                self.contributor.update([self.new_item(position, time)])

        elif msg_type == "session_active":
            if not message.get("value", False):
                self.contributor.clear()
                self.last_click = None
                probe("status", "session ended")