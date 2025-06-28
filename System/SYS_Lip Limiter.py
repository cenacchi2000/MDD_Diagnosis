from ea.util.number import clamp, remap, remap_keyframes

ctrls = {
    c: system.control(c, n, p)
    for c, n, p in [
        ("Jaw Pitch", None, ["demand"]),
        ("Lip Top Raise Middle", None, ["demand"]),
        ("Lip Top Raise Middle Limits", None, []),
        ("Lip Top Curl Limits", None, []),
        ("Lip Bottom Curl Limits", None, []),
        ("Lip Bottom Depress Middle", None, ["demand"]),
        ("Lip Bottom Depress Middle Limits", None, []),
    ]
}


class Activity:
    """
    See more here:
    https://george.earts.dev/wiki/index.php/Mesmer_Module_-_Lip_2_-_Conditional_Ranges
    """

    # Interpolation between two points
    # (Lower point, limit_min) - (Upper point, limit_max)

    # A limit point using the following
    # (actual position/demand from the limiting joint, set limit value to the limited joint)

    # Lip Top Raise Middle limiting Lip Top Curl.Lower Limit  and Upper Limit
    ENABLE_LIMITMAP_TOP_CURL_LOWER_LIMIT = True
    LIMITMAP_TOP_CURL_LOWER_LIMIT = [(0.0, 0.0), (1.0, 0.75)]
    # LIMITMAP_TOP_CURL_LOWER_LIMIT = [(0.0, 0.0),(0.2, 0.6), (0.5,0.7), (1.0,1.0)]

    ENABLE_LIMITMAP_TOP_CURL_UPPER_LIMIT = True
    LIMITMAP_TOP_CURL_UPPER_LIMIT = [(0.0, 0.7), (0.2, 1)]
    # LIMITMAP_TOP_CURL_UPPER_LIMIT = [(0.0, 1.0), (0.2, 1)]

    # Lip Bottom Depress Middle limiting Lip Bottom Curl.Lower Limit and Upper Limit
    ENABLE_BOTTOM_CURL_LOWER_LIMIT = True
    LIMITMAP_BOTTOM_CURL_LOWER_LIMIT = [(0.0, 0.1), (1.0, 0.85)]

    # ENABLE_BOTTOM_CURL_UPPER_LIMIT = True
    LIMITMAP_BOTTOM_CURL_UPPER_LIMIT = [(0.0, 0.9), (0.1, 1)]

    # Are these necessary?
    # Jaw Pitch limiting Lip Bottom Depress Middle.Lower Limit
    ENABLE_BOTTOM_DEPRESS_MID_LOWER_LIMIT = True
    LIMITMAP_BOTTOM_DEPRESS_MID_LOWER_LIMIT = [(0.7, 0), (1, 0.40)]
    assert (
        len(LIMITMAP_BOTTOM_DEPRESS_MID_LOWER_LIMIT) == 2
    ), "This is used for get_scale and cannot have a length longer than 2"

    # (Jaw Pitch + Lip Bottom Depress Middle) limiting Lip Top Raise Middle.Lower Limit
    ENABLE_TOP_RAISE_MID_LOWER_LIMIT = True
    LIMITMAP_TOP_RAISE_MID_LOWER_LIMIT = [(0.4, 0.0), (0.7, 0.5)]

    def get_limit(self, xp, limits):
        return remap_keyframes(xp, limits)

    def on_start(self):
        self.map = dict()

    def on_stop(self):
        if self.map:
            print(self.map)

    def record_state(self, pos_mid, pos_out):
        mid = "{:.1f}".format(pos_mid)
        self.map[mid] = pos_out
        pass

    def get_scale(self, map):
        return (map[1][0] - map[0][0]) / (map[1][1] - map[0][1])

    @system.tick(fps=60)
    def on_tick(self):
        pos_jaw_pitch = ctrls["Jaw Pitch"].demand
        pos_bottom_depress_middle = ctrls["Lip Bottom Depress Middle"].demand
        pos_top_raise_middle = ctrls["Lip Top Raise Middle"].demand

        try:
            #####  1. Lip Lower Middle Up-Down movement limit #####
            if getattr(self, "ENABLE_BOTTOM_DEPRESS_MID_LOWER_LIMIT", False):
                bottom_depress_mid_lower_limit = self.get_limit(
                    pos_jaw_pitch, self.LIMITMAP_BOTTOM_DEPRESS_MID_LOWER_LIMIT
                )
            else:
                bottom_depress_mid_lower_limit = 0

            # This is needed as the .demand read back doesn't accomodate our limits
            pos_bottom_depress_middle = clamp(
                pos_bottom_depress_middle, bottom_depress_mid_lower_limit, 1
            )
            ctrls["Lip Bottom Depress Middle Limits"].norm_lower_limit = (
                bottom_depress_mid_lower_limit
            )

            ##### 2. Lip Upper Middle Up-Down movement limiting #####

            # Calculate an absolute position by combining the Jaw Pitch and the Lip Lower Middle
            abs_pos_bottom_depress_middle = (
                pos_jaw_pitch
                - pos_bottom_depress_middle
                * self.get_scale(self.LIMITMAP_BOTTOM_DEPRESS_MID_LOWER_LIMIT)
            )
            probe("abs_pos_bottom_depress_middle", abs_pos_bottom_depress_middle)

            # Use that combinned position to limit the Upper Middle
            if getattr(self, "ENABLE_TOP_RAISE_MID_LOWER_LIMIT", False):
                top_raise_mid_lower_limit = self.get_limit(
                    abs_pos_bottom_depress_middle,
                    self.LIMITMAP_TOP_RAISE_MID_LOWER_LIMIT,
                )
            else:
                top_raise_mid_lower_limit = 0

            # This is needed as the .demand read back value doesn't accomodate our limits
            pos_top_raise_middle = clamp(
                pos_top_raise_middle, top_raise_mid_lower_limit, 1
            )
            ctrls["Lip Top Raise Middle Limits"].norm_lower_limit = (
                top_raise_mid_lower_limit
            )

            ###### 3. Lip Lower Middle In-Out movement limiting #####
            if getattr(self, "ENABLE_BOTTOM_CURL_LOWER_LIMIT", False):
                bottom_curl_lower_limit = self.get_limit(
                    pos_bottom_depress_middle, self.LIMITMAP_BOTTOM_CURL_LOWER_LIMIT
                )
            else:
                bottom_curl_lower_limit = 0

            if getattr(self, "ENABLE_BOTTOM_CURL_UPPER_LIMIT", False):
                bottom_curl_upper_limit = self.get_limit(
                    pos_bottom_depress_middle, self.LIMITMAP_BOTTOM_CURL_UPPER_LIMIT
                )
            else:
                bottom_curl_upper_limit = 1

            ctrls["Lip Bottom Curl Limits"].norm_lower_limit = bottom_curl_lower_limit
            ctrls["Lip Bottom Curl Limits"].norm_upper_limit = bottom_curl_upper_limit

            ###### 4. Lip Upper Middle In-Out movement limiting #####
            if getattr(self, "ENABLE_LIMITMAP_TOP_CURL_LOWER_LIMIT", False):
                top_curl_lower_limit = self.get_limit(
                    pos_top_raise_middle, self.LIMITMAP_TOP_CURL_LOWER_LIMIT
                )
            else:
                top_curl_lower_limit = 0

            if getattr(self, "ENABLE_LIMITMAP_TOP_CURL_UPPER_LIMIT", False):
                top_curl_upper_limit = self.get_limit(
                    pos_top_raise_middle, self.LIMITMAP_TOP_CURL_UPPER_LIMIT
                )
            else:
                top_curl_upper_limit = 1

            ctrls["Lip Top Curl Limits"].norm_lower_limit = top_curl_lower_limit
            ctrls["Lip Top Curl Limits"].norm_upper_limit = top_curl_upper_limit

            probe("Error", None)

        except TypeError as e:
            probe("Error", e)