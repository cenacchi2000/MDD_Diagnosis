"""
Script to monitor the power button on Ameca, and to trigger closing the
eyelids if a shutdown has been triggered.
"""


class Activity:
    @system.on_shutdown
    def on_shutdown(self):
        self.bid = system.arbitration.make_bid(
            specifiers=["Control/Direct Motors/Eyelid Motors"],
            precedence=Precedence.USER_MAXIMUM,
            bid_type=BidType.EXCLUSIVE,
        )
        with self.bid.use():
            close_eyelids = system.poses.get("eyelids_close")
            system.poses.apply(close_eyelids)
