from ea.util.number import clamp, remap
from tritium.arbitration import arbitration


class DemandGroup:
    VISEME = 0
    MOUTH = 1


direct_controls = [
    "Lip Corner Raise Left",
    "Lip Corner Raise Right",
    "Jaw Pitch",
    # "Jaw Yaw"
    "Lip Corner Stretch Left",
    "Lip Corner Stretch Right",
    "Lip Bottom Depress Left",
    "Lip Bottom Depress Right",
    "Lip Bottom Depress Middle",
    "Lip Top Raise Left",
    "Lip Top Raise Middle",
    "Lip Top Raise Right",
    "Lip Top Curl",
    "Lip Bottom Curl",
]
controls = {(c, None): system.control(c, None) for c in direct_controls}


@device(name="Human Behaviour - Mouth G2")
class Activity:
    """
    Provides device driver parameters for Mouth control from poses page and sequences

    Also accepts viseme queues from TTS watching scripts and blends everything together.

    Visemes and direct jaw control are mutually exclusive.

    TODO: Animation layer arbitration
    TODO: Control warm-up from arbitration-changes? - maybe will never happen other than user control
    """

    VISEME_NAMES = [
        "Viseme A",
        "Viseme CH",
        "Viseme Closed",
        "Viseme E",
        "Viseme F",
        "Viseme I",
        "Viseme ING",
        "Viseme KK",
        "Viseme M",
        "Viseme NN",
        "Viseme O",
        "Viseme RR",
        "Viseme SS",
        "Viseme U",
    ]

    MOUTH_NAMES = [
        "Mouth Open",
        "Mouth Anger",
        "Mouth Content",
        "Mouth Disgust",
        "Mouth Fear",
        "Mouth Happy",
        "Mouth Huh",
        "Mouth Joy",
        "Mouth Sad",
        "Mouth Sneer",
        "Mouth Surprise",
        "Mouth Worried",
    ]

    _demand_pending = False

    neutral_pose_name = "Mouth Neutral"

    viseme_demands = {key: 0 for key in VISEME_NAMES}
    mouth_demands = {key: 0 for key in MOUTH_NAMES}
    direct_control_demands = {key[0]: 0 for key in controls}

    def on_start(self):
        system.unstable.owner.mouth_driver = self
        self._arbitration_bid_ids = {}
        self._arbitration_bids = {}

        self.neut = system.poses.get(self.neutral_pose_name)

        self.bid = system.arbitration.make_bid(
            specifiers=[
                "Control/Direct Motors/Lip Motors",
                "Control/Direct Motors/Mouth Motors",
            ],
            precedence=Precedence.VERY_HIGH,
            bid_type=BidType.ON_DEMAND,
        )
        # Needs to be higher than sequences. Almost all control will go through this.
        self.update_poses()
        self.reset_viseme_demands()
        self.reset_mouth_demands()
        self.reset_direct_control_demands()
        self.apply()

    def on_stop(self):
        system.unstable.owner.mouth_driver = None

    def direct_control_add_mix(self, ctrl, value):
        if ctrl in direct_controls:
            self.direct_control_demands[ctrl] = value
        self._demand_pending = True

    def reset_viseme_demands(self):
        for ctrl in self.viseme_demands:
            self.viseme_demands[ctrl] = 0

    def reset_mouth_demands(self):
        for ctrl in self.mouth_demands:
            self.mouth_demands[ctrl] = 0

    def reset_direct_control_demands(self):
        for ctrl in self.direct_control_demands:
            self.direct_control_demands[ctrl] = self.neut.get((ctrl, None), 0)

    @system.tick(fps=60)
    def on_tick(self):
        if self._demand_pending:
            self._demand_pending = False
            self.apply()

        arbitration_client = arbitration.get_client()
        if arbitration_client is None:
            probe("status", "paused")
            self.on_tick.pause()
            self._arbitration_bids = {}
            self._arbitration_bid_ids = {}
            probe("arbitration_bid_id", None)
            return

        for key, bid_id in self._arbitration_bid_ids.items():
            if bid_id is None:
                continue
            else:
                bid = self._arbitration_bids.get(key, None)
                if bid is None:
                    try:
                        bid = arbitration_client.arbitration_state.get_bid(None, bid_id)
                    except KeyError:
                        continue
                    else:
                        self._arbitration_bids[key] = bid
                if bid.active:
                    # Alles ist gut Und die Blumen werden dich anlächeln.
                    pass
                else:
                    # Bad.
                    self._arbitration_bids[key] = None
                    self._arbitration_bid_ids[key] = None

    @system.tick(fps=0.5)
    def update_poses(self):
        self.viseme_poses = {key: system.poses.get(key) for key in self.VISEME_NAMES}
        self.mouth_poses = {
            key: system.poses.get(key)
            for key in self.MOUTH_NAMES
            if key != "Mouth Open"
        }

        self.jaw_speaking_pose = system.poses.get("AU4 Jaw Speaking")
        self.jaw_wide_pose = system.poses.get("AU4 Jaw Wide")

    def reset_demands(self, demand_group: DemandGroup):
        if demand_group == DemandGroup.VISEME:
            self.reset_viseme_demands()
        elif demand_group == DemandGroup.MOUTH:
            self.reset_mouth_demands()
        self.reset_direct_control_demands()

    def on_any_demand_received(self, demand_group: DemandGroup, arbitration_bid_id):
        # Ignore demands without an arbitration bid for now - keeps our code simpler.
        if arbitration_bid_id is None:
            return False
        self._demand_pending = True
        # Reset as the arbitration bid (sequence) changed
        if self._arbitration_bid_ids.get(demand_group, None) != arbitration_bid_id:
            self.reset_demands(demand_group)
            self._arbitration_bid_ids[demand_group] = arbitration_bid_id
            self._arbitration_bids[demand_group] = None
            probe(f"arbitration_bid_id {demand_group}", arbitration_bid_id)
        self.on_tick.resume()
        return True

    @parameter("float", name="Viseme A", min_value=0, max_value=1)
    def viseme_a(self):
        return self.viseme_demands["Viseme A"]

    @viseme_a.setter
    def set_viseme_a(self, value):
        self.viseme_demands["Viseme A"] = value

    @viseme_a.on_demand
    def on_viseme_a_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_a(clamp(value, 0, 1))

    @parameter("float", name="Viseme CH", min_value=0, max_value=1)
    def viseme_ch(self):
        return self.viseme_demands["Viseme CH"]

    @viseme_ch.setter
    def set_viseme_ch(self, value):
        self.viseme_demands["Viseme CH"] = value

    @viseme_ch.on_demand
    def on_viseme_ch_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_ch(clamp(value, 0, 1))

    @parameter("float", name="Viseme Closed", min_value=0, max_value=1)
    def viseme_closed(self):
        return self.viseme_demands["Viseme Closed"]

    @viseme_closed.setter
    def set_viseme_closed(self, value):
        self.viseme_demands["Viseme Closed"] = value

    @viseme_closed.on_demand
    def on_viseme_closed_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_closed(clamp(value, 0, 1))

    @parameter("float", name="Viseme E", min_value=0, max_value=1)
    def viseme_e(self):
        return self.viseme_demands["Viseme E"]

    @viseme_e.setter
    def set_viseme_e(self, value):
        self.viseme_demands["Viseme E"] = value

    @viseme_e.on_demand
    def on_viseme_e_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_e(clamp(value, 0, 1))

    @parameter("float", name="Viseme I", min_value=0, max_value=1)
    def viseme_i(self):
        return self.viseme_demands["Viseme I"]

    @viseme_i.setter
    def set_viseme_i(self, value):
        self.viseme_demands["Viseme I"] = value

    @viseme_i.on_demand
    def on_viseme_i_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_i(clamp(value, 0, 1))

    @parameter("float", name="Viseme F", min_value=0, max_value=1)
    def viseme_f(self):
        return self.viseme_demands["Viseme F"]

    @viseme_f.setter
    def set_viseme_f(self, value):
        self.viseme_demands["Viseme F"] = value

    @viseme_f.on_demand
    def on_viseme_f_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_f(clamp(value, 0, 1))

    @parameter("float", name="Viseme ING", min_value=0, max_value=1)
    def viseme_ing(self):
        return self.viseme_demands["Viseme ING"]

    @viseme_ing.setter
    def set_viseme_ing(self, value):
        self.viseme_demands["Viseme ING"] = value

    @viseme_ing.on_demand
    def on_viseme_ing_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_ing(clamp(value, 0, 1))

    @parameter("float", name="Viseme KK", min_value=0, max_value=1)
    def viseme_kk(self):
        return self.viseme_demands["Viseme KK"]

    @viseme_kk.setter
    def set_viseme_kk(self, value):
        self.viseme_demands["Viseme KK"] = value

    @viseme_kk.on_demand
    def on_viseme_kk_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_kk(clamp(value, 0, 1))

    @parameter("float", name="Viseme M", min_value=0, max_value=1)
    def viseme_m(self):
        return self.viseme_demands["Viseme M"]

    @viseme_m.setter
    def set_viseme_m(self, value):
        self.viseme_demands["Viseme M"] = value

    @viseme_m.on_demand
    def on_viseme_m_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_m(clamp(value, 0, 1))

    @parameter("float", name="Viseme NN", min_value=0, max_value=1)
    def viseme_nn(self):
        return self.viseme_demands["Viseme NN"]

    @viseme_nn.setter
    def set_viseme_nn(self, value):
        self.viseme_demands["Viseme NN"] = value

    @viseme_nn.on_demand
    def on_viseme_nn_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_nn(clamp(value, 0, 1))

    @parameter("float", name="Viseme O", min_value=0, max_value=1)
    def viseme_o(self):
        return self.viseme_demands["Viseme O"]

    @viseme_o.setter
    def set_viseme_o(self, value):
        self.viseme_demands["Viseme O"] = value

    @viseme_o.on_demand
    def on_viseme_o_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_o(clamp(value, 0, 1))

    @parameter("float", name="Viseme RR", min_value=0, max_value=1)
    def viseme_rr(self):
        return self.viseme_demands["Viseme RR"]

    @viseme_rr.setter
    def set_viseme_rr(self, value):
        self.viseme_demands["Viseme RR"] = value

    @viseme_rr.on_demand
    def on_viseme_rr_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_rr(clamp(value, 0, 1))

    @parameter("float", name="Viseme SS", min_value=0, max_value=1)
    def viseme_ss(self):
        return self.viseme_demands["Viseme SS"]

    @viseme_ss.setter
    def set_viseme_ss(self, value):
        self.viseme_demands["Viseme SS"] = value

    @viseme_ss.on_demand
    def on_viseme_ss_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_ss(clamp(value, 0, 1))

    @parameter("float", name="Viseme U", min_value=0, max_value=1)
    def viseme_u(self):
        return self.viseme_demands["Viseme U"]

    @viseme_u.setter
    def set_viseme_u(self, value):
        self.viseme_demands["Viseme U"] = value

    @viseme_u.on_demand
    def on_viseme_u_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.VISEME, arbitration_bid_id):
            return
        self.set_viseme_u(clamp(value, 0, 1))

    @parameter("float", name="Mouth Open", min_value=0, max_value=2)
    def mouth_open(self):
        return self.mouth_demands["Mouth Open"] * 2

    @mouth_open.setter
    def set_mouth_open(self, value):
        # change from 0 to 2 range to 0 to 1
        self.mouth_demands["Mouth Open"] = value / 2

    @mouth_open.on_demand
    def on_mouth_open_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_open(clamp(value, 0, 2))

    @parameter("float", name="Mouth Anger", min_value=0, max_value=1)
    def mouth_anger(self):
        return self.mouth_demands["Mouth Anger"]

    @mouth_anger.setter
    def set_mouth_anger(self, value):
        self.mouth_demands["Mouth Anger"] = value

    @mouth_anger.on_demand
    def on_mouth_anger_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_anger(clamp(value, 0, 1))

    @parameter("float", name="Mouth Content", min_value=0, max_value=1)
    def mouth_content(self):
        return self.mouth_demands["Mouth Content"]

    @mouth_content.setter
    def set_mouth_content(self, value):
        self.mouth_demands["Mouth Content"] = value

    @mouth_content.on_demand
    def on_mouth_content_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_content(clamp(value, 0, 1))

    @parameter("float", name="Mouth Disgust", min_value=0, max_value=1)
    def mouth_disgust(self):
        return self.mouth_demands["Mouth Disgust"]

    @mouth_disgust.setter
    def set_mouth_disgust(self, value):
        self.mouth_demands["Mouth Disgust"] = value

    @mouth_disgust.on_demand
    def on_mouth_disgust_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_disgust(clamp(value, 0, 1))

    @parameter("float", name="Mouth Fear", min_value=0, max_value=1)
    def mouth_fear(self):
        return self.mouth_demands["Mouth Fear"]

    @mouth_fear.setter
    def set_mouth_fear(self, value):
        self.mouth_demands["Mouth Fear"] = value

    @mouth_fear.on_demand
    def on_mouth_fear_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_fear(clamp(value, 0, 1))

    @parameter("float", name="Mouth Happy", min_value=0, max_value=1)
    def mouth_happy(self):
        return self.mouth_demands["Mouth Happy"]

    @mouth_happy.setter
    def set_mouth_happy(self, value):
        self.mouth_demands["Mouth Happy"] = value

    @mouth_happy.on_demand
    def on_mouth_happy_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_happy(clamp(value, 0, 1))

    @parameter("float", name="Mouth Huh", min_value=0, max_value=1)
    def mouth_huh(self):
        return self.mouth_demands["Mouth Huh"]

    @mouth_huh.setter
    def set_mouth_huh(self, value):
        self.mouth_demands["Mouth Huh"] = value

    @mouth_huh.on_demand
    def on_mouth_huh_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_huh(clamp(value, 0, 1))

    @parameter("float", name="Mouth Joy", min_value=0, max_value=1)
    def mouth_joy(self):
        return self.mouth_demands["Mouth Joy"]

    @mouth_joy.setter
    def set_mouth_joy(self, value):
        self.mouth_demands["Mouth Joy"] = value

    @mouth_joy.on_demand
    def on_mouth_joy_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_joy(clamp(value, 0, 1))

    @parameter("float", name="Mouth Sad", min_value=0, max_value=1)
    def mouth_sad(self):
        return self.mouth_demands["Mouth Sad"]

    @mouth_sad.setter
    def set_mouth_sad(self, value):
        self.mouth_demands["Mouth Sad"] = value

    @mouth_sad.on_demand
    def on_mouth_sad_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_sad(clamp(value, 0, 1))

    @parameter("float", name="Mouth Sneer", min_value=0, max_value=1)
    def mouth_sneer(self):
        return self.mouth_demands["Mouth Sneer"]

    @mouth_sneer.setter
    def set_mouth_sneer(self, value):
        self.mouth_demands["Mouth Sneer"] = value

    @mouth_sneer.on_demand
    def on_mouth_sneer_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_sneer(clamp(value, 0, 1))

    @parameter("float", name="Mouth Surprise", min_value=0, max_value=1)
    def mouth_surprise(self):
        return self.mouth_demands["Mouth Surprise"]

    @mouth_surprise.setter
    def set_mouth_surprise(self, value):
        self.mouth_demands["Mouth Surprise"] = value

    @mouth_surprise.on_demand
    def on_mouth_surprise_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_surprise(clamp(value, 0, 1))

    @parameter("float", name="Mouth Worried", min_value=0, max_value=1)
    def mouth_worried(self):
        return self.mouth_demands["Mouth Worried"]

    @mouth_worried.setter
    def set_mouth_worried(self, value):
        self.mouth_demands["Mouth Worried"] = value

    @mouth_worried.on_demand
    def on_mouth_worried_demand(self, value, arbitration_bid_id):
        if not self.on_any_demand_received(DemandGroup.MOUTH, arbitration_bid_id):
            return
        self.set_mouth_worried(clamp(value, 0, 1))

    def apply(self):
        deltas = {}

        def add_deltas_from_pose(pose, gain=1):
            for ctrl, val in pose.items():
                if ctrl not in controls or val is None:
                    continue
                nval = self.neut.get(ctrl, 0)
                if ctrl in deltas:
                    deltas[ctrl] += (val - nval) * gain
                else:
                    deltas[ctrl] = (val - nval) * gain

        def mix_deltas_from_direct_control(ctrl, val):
            # Kinda a QDH for allowing noisy telepresence mocap to blend with
            # flappy mouth.
            # Problem is telepresence mocap is slow at reacting so often are not
            # Opening the mouth when the robot is actually making talking sounds.
            # Flappy mouth doesn't have good mouth shape but is good at reacting to
            # sounds at all times.
            # This QDH chooses which ever one is most open at any time, so that when
            # 50-70% of the time telepresence lipsync actually do capture the mouth and,
            # Opens it widely enough, Telepresence lipsync is used.
            # Otherwise flappy lipsync is used.
            nval = self.neut.get(ctrl, 0)
            if ctrl in deltas:
                if abs(deltas[ctrl]) > abs(val - nval):
                    pass
                else:
                    deltas[ctrl] = val - nval
            else:
                deltas[ctrl] = val - nval

        def normalize_dict(vals: dict, max_val: float) -> float:
            if max_val <= 0.0:
                for key in vals:
                    vals[key] = 0.0
                return 0.0

            sum_val = 0.0
            for value in vals.values():
                sum_val += value

            if sum_val > max_val:
                scalar = max_val / sum_val
                for key in vals:
                    vals[key] *= scalar
                return max_val

            return sum_val

        # gain normalisation and priority stuff
        viseme_demands_normalized = self.viseme_demands.copy()
        mouth_demands_normalized = self.mouth_demands.copy()

        viseme_sum = normalize_dict(viseme_demands_normalized, 1)
        normalize_dict(mouth_demands_normalized, 1 - viseme_sum)

        for key, value in viseme_demands_normalized.items():
            probe(key, value)
            if value > 0:
                add_deltas_from_pose(self.viseme_poses[key], value)

        for key, value in mouth_demands_normalized.items():
            if key == "Mouth Open":
                # 0 (neutral) -> 0.5 (AU4 Jaw Speaking) -> 1 (AU4 Jaw Wide)

                if value <= 0.5:
                    # Mix from 0 to speaking
                    overall_speaking_gain = value * 2
                    overall_wide_gain = 0
                else:
                    # Mix from speaking to wide
                    overall_speaking_gain = remap(value, 0.5, 1, 1, 0)
                    overall_wide_gain = 1 - overall_speaking_gain

                add_deltas_from_pose(self.jaw_speaking_pose, overall_speaking_gain)
                add_deltas_from_pose(self.jaw_wide_pose, overall_wide_gain)
            else:
                if value > 0:
                    add_deltas_from_pose(self.mouth_poses[key], value)

        # Direct controls mixes.
        direct_controls = self.direct_control_demands.copy()
        for key, value in direct_controls.items():
            mix_deltas_from_direct_control((key, None), value)

        with self.bid.use():
            for ctrl, val in self.neut.items():
                if ctrl in controls:
                    probe(ctrl, val)
                    controls[ctrl].demand = val + deltas.get(ctrl, 0)