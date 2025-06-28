from math import radians

from ea.math3d import Point, spherical_to_cartesian
from ea.util.number import clamp
from tritium.world.geom import Point3
from tritium.arbitration import arbitration

contributor = system.import_library("../../HB3/lib/contributor.py")


# TODO: World client should provide a way to get the natural location of frames
HEIGHT = 1.6


@device(name="Animation Driver - Gaze Target")
class Activity:
    """
    Provides robot-space gaze control for sequences

    TODO: Feedback from parameter demand when controlled from underneath
    """

    _phi = 0
    _theta = 0
    _dist = 1
    _last_dmd = None
    _demand_pending = False
    _arbitration_bid_id = None
    _arbitration_bid = None
    contributor = None

    def on_start(self):
        self.contributor = contributor.Contributor(
            "look",
            "sequence_gaze_target",
            reference_frame=system.world.ROBOT_SPACE,
        )

    @parameter("float", name="Gaze.Target Phi", min_value=-130, max_value=130)
    def phi(self):
        return self._phi

    @phi.setter
    def set_phi(self, value):
        self._phi = value

    @phi.on_demand
    def on_phi_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(arbitration_bid_id):
            return
        self.set_phi(clamp(value, -130, 130))  # TODO: Add sensible clamp

    @parameter("float", name="Gaze.Target Theta", min_value=-62, max_value=62)
    def theta(self):
        return self._theta

    @theta.setter
    def set_theta(self, value):
        self._theta = value

    @theta.on_demand
    def on_theta_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(arbitration_bid_id):
            return
        self.set_theta(clamp(value, -62, 62))  # TODO: Add sensible clamp

    @parameter("float", name="Gaze.Target Distance", min_value=0.3, max_value=5)
    def dist(self):
        return self._dist

    @dist.setter
    def set_dist(self, value):
        self._dist = value

    @dist.on_demand
    def on_dist_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(arbitration_bid_id):
            return
        self.set_dist(clamp(value, 0.3, 5))  # TODO: Add sensible clamp

    def on_any_demand_received(self, arbitration_bid_id):
        probe("last_dmd_bid", arbitration_bid_id)
        # Ignore demands without an arbitration bid for now - keeps our code simpler.
        if arbitration_bid_id is None:
            return False
        self._demand_pending = True
        # Reset as the arbitration bid (sequence) changed
        if self._arbitration_bid_id != arbitration_bid_id:
            self.set_theta(0)
            self.set_phi(0)
            self.set_dist(1)
            self._arbitration_bid_id = arbitration_bid_id
            self._arbitration_bid = None
        probe("arbitration_bid_id", arbitration_bid_id)
        self.on_frame.resume()
        return True

    def on_message(self, channel, message):
        if self.contributor:
            self.contributor.on_message(channel, message)

    def apply(self):
        p = Point(self._dist, radians(self._theta), radians(self._phi))
        v = spherical_to_cartesian(p)
        v = Point3([v.x, v.y, v.z + HEIGHT])

        self.contributor.update(
            [contributor.LookAtItem(identifier="animation_gaze_target", position=v)]
        )
        probe("status", "running")
        self.on_frame.resume()

    @system.tick(fps=60)
    def on_frame(self):
        if self._demand_pending:
            self._demand_pending = False
            self.apply()
        if self._arbitration_bid_id is None:
            probe("status", "paused")
            self.on_frame.pause()
            self.contributor.clear()
            return
        if self._arbitration_bid is None:
            arbitration_client = arbitration.get_client()
            if arbitration_client is None:
                probe("status", "paused")
                self.on_frame.pause()
                self._arbitration_bid = None
                self._arbitration_bid_id = None
                probe("arbitration_bid_id", None)
                self.contributor.clear()
                return
            try:
                bid = arbitration_client.arbitration_state.get_bid(
                    None, self._arbitration_bid_id
                )
            except KeyError:
                # Ignore, wait until we can find the bid
                # TODO: Do we need to remember all deleted bid ids?
                # There's a chance we miss the bid...
                return
            else:
                self._arbitration_bid = bid
        # Only cancel if we can get a reference to the bid, and/or we know it's
        if self._arbitration_bid is not None and not self._arbitration_bid.active:
            probe("status", "paused")
            self.on_frame.pause()
            self.contributor.clear()