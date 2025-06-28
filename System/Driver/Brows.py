from ea.util.number import clamp

brow_inner_left_control = system.control("Brow Inner Left", None, acquire=["position"])
brow_outer_left_control = system.control("Brow Outer Left", None, acquire=["position"])
brow_inner_right_control = system.control(
    "Brow Inner Right", None, acquire=["position"]
)
brow_outer_right_control = system.control(
    "Brow Outer Right", None, acquire=["position"]
)

BROW_NEUTRAL_POSE = "Brow_Neutral"


# warp range from [0 -> 0.5 -> 1] to [0 -> midpoint -> 1]
def warp(value, midpoint):
    if value <= 0.5:
        return 2 * midpoint * value
    else:
        return 2 * (1 - midpoint) * (value - 0.5) + midpoint


# warp range from [0 -> midpoint -> 1] to [0 -> 0.5 -> 1]
def unwarp(value, midpoint):
    if value <= midpoint:
        return value / (2 * midpoint)
    else:
        return ((value - midpoint) / (2 * (1 - midpoint))) + 0.5


@device(name="Human Behaviour - Brows")
class Activity:
    """
    Provides device driver parameters for Brow controls from poses page
    """

    _brow_inner_left = 0
    _brow_inner_left_feedback = _brow_inner_left

    _brow_outer_left = 0
    _brow_outer_left_feedback = _brow_outer_left

    _brow_inner_right = 0
    _brow_inner_right_feedback = _brow_inner_right

    _brow_outer_right = 0
    _brow_outer_right_feedback = _brow_outer_right

    def on_start(self):
        self.bid = system.arbitration.make_bid(
            specifiers=["Control/Direct Motors/Brow Motors"],
            # Needs to be higher than sequences. Almost all control will go through this.
            precedence=Precedence.VERY_HIGH,
            bid_type=BidType.ON_DEMAND,
        )

    def _midpoint(self, control_name):
        return system.poses.get(BROW_NEUTRAL_POSE)[(control_name, None)]

    @parameter("float", name="Brow Inner Left", min_value=0, max_value=1)
    def brow_inner_left(self):
        return self._brow_inner_left

    @brow_inner_left.setter
    def set_brow_inner_left(self, value):
        self._brow_inner_left = value
        with self.bid.use():
            brow_inner_left_control.demand = warp(
                value, self._midpoint("Brow Inner Left")
            )

    @brow_inner_left.on_demand
    def on_brow_inner_left_demand(self, value, arbitration_bid_id):
        self.set_brow_inner_left(clamp(value, 0, 1))

    @parameter("float", name="Brow Inner Left Feedback", min_value=0, max_value=1)
    def brow_inner_left_feedback(self):
        return self._brow_inner_left_feedback

    @brow_inner_left_feedback.setter
    def set_brow_inner_left_feedback(self, value):
        self._brow_inner_left_feedback = value

    @parameter("float", name="Brow Outer Left", min_value=0, max_value=1)
    def brow_outer_left(self):
        return self._brow_outer_left

    @brow_outer_left.setter
    def set_brow_outer_left(self, value):
        self._brow_outer_left = value
        with self.bid.use():
            brow_outer_left_control.demand = warp(
                value, self._midpoint("Brow Outer Left")
            )

    @brow_outer_left.on_demand
    def on_brow_outer_left_demand(self, value, arbitration_bid_id):
        self.set_brow_outer_left(clamp(value, 0, 1))

    @parameter("float", name="Brow Outer Left Feedback", min_value=0, max_value=1)
    def brow_outer_left_feedback(self):
        return self._brow_outer_left_feedback

    @brow_outer_left_feedback.setter
    def set_brow_outer_left_feedback(self, value):
        self._brow_outer_left_feedback = value

    @parameter("float", name="Brow Inner Right", min_value=0, max_value=1)
    def brow_inner_right(self):
        return self._brow_inner_right

    @brow_inner_right.setter
    def set_brow_inner_right(self, value):
        self._brow_inner_right = value
        with self.bid.use():
            brow_inner_right_control.demand = warp(
                value, self._midpoint("Brow Inner Right")
            )

    @brow_inner_right.on_demand
    def on_brow_inner_right_demand(self, value, arbitration_bid_id):
        self.set_brow_inner_right(clamp(value, 0, 1))

    @parameter("float", name="Brow Inner Right Feedback", min_value=0, max_value=1)
    def brow_inner_right_feedback(self):
        return self._brow_inner_right_feedback

    @brow_inner_right_feedback.setter
    def set_brow_inner_right_feedback(self, value):
        self._brow_inner_right_feedback = value

    @parameter("float", name="Brow Outer Right", min_value=0, max_value=1)
    def brow_outer_right(self):
        return self._brow_outer_right

    @brow_outer_right.setter
    def set_brow_outer_right(self, value):
        self._brow_outer_right = value
        with self.bid.use():
            brow_outer_right_control.demand = warp(
                value, self._midpoint("Brow Outer Right")
            )

    @brow_outer_right.on_demand
    def on_brow_outer_right_demand(self, value, arbitration_bid_id):
        self.set_brow_outer_right(clamp(value, 0, 1))

    @parameter("float", name="Brow Outer Right Feedback", min_value=0, max_value=1)
    def brow_outer_right_feedback(self):
        return self._brow_outer_right_feedback

    @brow_outer_right_feedback.setter
    def set_brow_outer_right_feedback(self, value):
        self._brow_outer_right_feedback = value

    @system.watch(
        [
            brow_inner_left_control,
            brow_inner_right_control,
            brow_outer_left_control,
            brow_outer_right_control,
        ]
    )
    def watcher(self, changed, *args):

        if brow_inner_left_control in changed:
            p = brow_inner_left_control.position
            if p is not None:
                self.set_brow_inner_left_feedback(
                    unwarp(p, self._midpoint("Brow Inner Left"))
                )

        if brow_outer_left_control in changed:
            p = brow_outer_left_control.position
            if p is not None:
                self.set_brow_outer_left_feedback(
                    unwarp(p, self._midpoint("Brow Outer Left"))
                )

        if brow_inner_right_control in changed:
            p = brow_inner_right_control.position
            if p is not None:
                self.set_brow_inner_right_feedback(
                    unwarp(p, self._midpoint("Brow Inner Right"))
                )

        if brow_outer_right_control in changed:
            p = brow_outer_right_control.position
            if p is not None:
                self.set_brow_outer_right_feedback(
                    unwarp(p, self._midpoint("Brow Outer Right"))
                )