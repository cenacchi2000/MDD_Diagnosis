from time import monotonic

HB3_CONFIG = system.import_library("../../Config/HB3.py").CONFIG
contributor = system.import_library("../lib/contributor.py")
robot_state = system.import_library("../robot_state.py").state

ObjectDetectionClient = system.import_library(
    "./lib/obj_detection_client.py"
).ObjectDetectionClient

SELF_IDENTIFIER = "ADD_POSE_FOR_CAMERA"

# List of mix pose sources we want to block when we are looking for cameras
# to reduce movement when person stood very close to robot
SRC_DENY_LIST = [
    # Prevent recoil if face is too close (for selfies)
    "ADD_PROXIMITY_RECOIL",
    # Prevent arm movement applied when talking
    "ANIM_TALKING_ARM_MOVEMENTS:gesture loop",
    # Dont prevent slight arm sway, breathing,
    # or request for movement such as 'give us a wave'
]


class Activity:
    MAX_TRACKING_TIME = 45  # Max time to be looking for cameras in seconds
    # So that in crowds of people filming we dont get stuck in here forever
    MIN_TRACKING_TIME = 5  # Min time to be looking for cameras in seconds
    # Can help deal with unreliable detecton
    NO_DETECTION_TIMEOUT = 1  # Exit early if no cameras detected for this many seconds
    # Timer doesnt start until after the first detection

    client: ObjectDetectionClient | None = None
    consumer: contributor.ConsumerRef | None = None

    def on_start(self):
        self.client = ObjectDetectionClient(system.unstable.owner)
        self.consumer = contributor.ConsumerRef("look")

        self.tracking_started_at = None
        self.last_detection_at = None

        # Only reduce body animations for full body Amecas. We don't want to mess
        # up drawing Ameca, as no-one would be standing close to them anyway
        self.limit_idle_movement = (
            HB3_CONFIG["ROBOT_TYPE"] == HB3_CONFIG["ROBOT_TYPES"].AMECA
        )

    def start_camera_tracking(self):
        if self.tracking_started_at is None:
            self.tracking_started_at = monotonic()
            robot_state.is_camera_tracking = True

            # Start node running CV. See below comment
            self.client.start_object_detection()

            if self.limit_idle_movement:
                self.mix_pose_set_filters()

    def stop_camera_tracking(self):
        self.tracking_started_at = None
        self.last_detection_at = None
        robot_state.is_camera_tracking = False

        # This stops the node doing any computer vision stuff to save cpu
        # Might not be viable once the node is doing more than just cameras
        self.client.stop_object_detection()

        self.mix_pose_clean_self()
        if self.limit_idle_movement:
            self.mix_pose_clear_filters()

    def on_stop(self):
        self.stop_camera_tracking()

        self.client.disconnect()
        self.client = None

    @system.on_event("camera_tracking")
    def on_tracking_request(self, message: bool):
        if message:
            self.start_camera_tracking()
        else:
            self.stop_camera_tracking()

    def on_message(self, channel, message):
        if self.consumer:
            self.consumer.on_message(channel, message)

    def mix_pose_add_absolute(self, ctrl, val):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.add_absolute(SELF_IDENTIFIER, ctrl, val)

    def mix_pose_clean_self(self):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.clean(SELF_IDENTIFIER)

    def mix_pose_set_filters(self):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.set_filters(SELF_IDENTIFIER, deny_list=SRC_DENY_LIST)

    def mix_pose_clear_filters(self):
        mix_pose = getattr(system.unstable.owner, "mix_pose", None)
        if mix_pose is not None:
            mix_pose.clear_filters(SELF_IDENTIFIER)

    @system.tick(fps=10)
    def on_tick(self):
        track_time_elapsed = (
            monotonic() - self.tracking_started_at
            if self.tracking_started_at is not None
            else 0
        )
        track_time_remaining = (
            self.MAX_TRACKING_TIME - track_time_elapsed
            if self.tracking_started_at is not None
            else 0
        )
        last_detection_time_elapsed = (
            monotonic() - self.last_detection_at
            if self.last_detection_at is not None
            else 0
        )
        last_detection_time_remaining = (
            self.NO_DETECTION_TIMEOUT - last_detection_time_elapsed
            if self.last_detection_at is not None
            else 0
        )
        probe("is_camera_tracking", robot_state.is_camera_tracking)
        probe("time since started tracking cameras", track_time_elapsed)
        probe("time until max tracking time reached", track_time_remaining)
        probe("time since last detection", last_detection_time_elapsed)
        probe("time until no detection timeout reached", last_detection_time_remaining)

        # Handle if someone changes robot state without going via this script
        if not robot_state.is_camera_tracking:
            if self.tracking_started_at is not None:
                self.stop_camera_tracking()
            return
        elif self.tracking_started_at is None:
            self.start_camera_tracking()

        # If robot thinks it will look up and lose focus
        # There isn't much we can do if it can't find the phone again,
        # but we can give it more time by overriding the timeout
        if self.last_detection_at is not None and (
            robot_state.is_thinking or robot_state.speaking
        ):
            self.last_detection_at = monotonic()

        # Check timeout
        if track_time_elapsed >= self.MAX_TRACKING_TIME or (
            self.last_detection_at is not None
            and last_detection_time_elapsed >= self.NO_DETECTION_TIMEOUT
            and track_time_elapsed >= self.MIN_TRACKING_TIME
        ):
            self.stop_camera_tracking()
            return

        # Get the current lookAt target
        target, _, _ = self.consumer.get_private_target()
        if target and target.identifier.startswith("object_cellphone"):
            self.last_detection_at = monotonic()

        if self.last_detection_at is not None:
            # Smile
            self.mix_pose_add_absolute(("Mouth Happy", "Mesmer Mouth 2"), 1)