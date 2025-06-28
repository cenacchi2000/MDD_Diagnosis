from copy import copy
from time import time as time_unix
from collections import defaultdict

from ea.animation import INTERP_BEZIER, INTERP_LINEAR
from ea.animation.structural import Clip

CONTROL_NAMES = [
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

BASE_POSE = {viseme: 0 for viseme in CONTROL_NAMES}
TTS_VISEME_OFFSET = -0.1

VISEMES = defaultdict(lambda: ["Viseme A", 0.8, 0.7])
VISEMES.update(
    {
        "a": ["Viseme A", 0.8, 0.7],
        # long open-back unrounded vowel | f[a]ther & diphthong | m[ou]th & diphthong | pr[i]ce & near open-front unrounded vowel | tr[a]p
        "e": ["Viseme E", 0.8, 0.8],
        # diphthong | f[a]ce
        "E": ["Viseme E", 0.9, 0.7],
        # Open-mid-back unrounded vowel | str[u]t & diphthong | squ[are] & open mid-front unrounded vowel | dr[e]ss & long open mid-central unrounded vowel | n[ur]se
        "i": ["Viseme I", 0.8, 0.8],
        # diphthong | n[ear] & near-close near-front unrounded vowel | k[i]t & long close front unrounded vowel | fl[ee]ce & palatal approximant | [y]es
        "f": ["Viseme F", 0.7, 0.8],
        # voiced labiodental fricative | [v]est & voiceless labiodental fricative | [f]ive
        "k": ["Viseme KK", 0.9, 0.6],
        # velar nasal | thi[ng] & voiceless velar plosive | [c]at & voiceless glottal fricative | [h]ouse  voiced velar plosive | [g]ame
        "p": ["Viseme M", 1, 1.1],
        # voiceless bilabial plosive | [p]in & syllabic bilabial nasal | anth[em] & bilabial nasal | [m]ouse & voiced bilabial plosive | [b]ed
        "O": ["Viseme O", 1, 0.5],
        "@": ["Viseme O", 1, 0.5],
        # diphthong | g[oa]t & mid central vowel | [a]ren[a]
        "o": ["Viseme O", 1, 0.5],
        # open back rounded vowel | l[o]t & Diphthong | ch[oi]ce & long open-mid back rounded vowel | th[ou]ght
        "r": ["Viseme RR", 0.9, 0.4],
        # alveolar approximant | red
        "s": ["Viseme SS", 1, 0.7],
        # voiced alveolar fricative | [z]ero & voiceless alveolar fricative | [s]eem
        "S": ["Viseme SS", 1, 0.5],
        # voiced postalveolar fricative | vi[s]ion & voiceless postalveolar affricate | [ch]art & voiceless postalveolar fricative | [sh]ip & voiced postalveolar affricate | [j]ump
        "t": ["Viseme I", 0.3, 0.5],
        # voiceless alveolar plosive | [t]ask & syllabic alveolar nasal | butto[n] & alveolar nasal | [n]ap & syllabic alveolar lateral approximant | batt[le] & alveolar lateral approximant | & [l]ay & voiced alveolar plosive | [d]ig
        "T": ["Viseme F", 0.6, 0.5],
        # voiceless dental fricative | [th]in & voiced dental fricative | [th]en
        "u": ["Viseme U", 1, 0.5],
        # diphthong | c[u]re & near-close near-back rounded vowel | f[oo]t & long close-back rounded vowel | g[oo]se & labial-velar approximant | [w]est
        "sil": ["BASE_POSE", 0.5, 0.5],
        # silence, using BASE_POSE here instead of Viseme Closed means we can let expressions show though
    }
)


# returns a dict with viseme_name having value gain, and the rest have value 0
def pose_from_viseme(viseme_name, gain=1):
    if viseme_name == "BASE_POSE":
        return BASE_POSE
    viseme_pose = BASE_POSE.copy()
    # viseme_pose = {viseme_name: gain}
    viseme_pose[viseme_name] = gain
    return viseme_pose


class VisemeQueue:
    MAX_INTERP_TIME = 0.3
    MAX_RAMP_TIME = 0.2  # s

    def __init__(self, visemes=None):
        """
        initial_pose: dict-like ctrl, value pose for interpolation
        viseme_dict: dict that defines the controls for each viseme and the weights

        the weight affects how much we should sway the interpolation to spend more time on that viseme pose
        """
        self.clip = Clip({}, [])

        # dict that contains time and viseme, same format as entries in add_visemes functin arguments
        self.last_viseme = None
        self.stop_time = None
        if visemes:
            self.add_visemes(visemes)

    def convert_viseme(self, name):
        return VISEMES[name][0]

    def is_playable(self):
        if self.stop_time:
            return time_unix() < self.stop_time
        return False

    def add_visemes(self, visemes):
        if not visemes:
            # Empty list of new visemes, no need to do anything
            return

        time_adjusted_visemes = []

        for viseme in visemes:
            adjusted_viseme = copy(viseme)
            adjusted_viseme["time"] += TTS_VISEME_OFFSET
            if (
                self.last_viseme is None
                or adjusted_viseme["time"] > self.last_viseme["time"]
            ):
                time_adjusted_visemes.append(adjusted_viseme)
            else:
                log.info(
                    f"Skipping viseme {adjusted_viseme} which has a timestamp before last viseme {self.last_viseme}"
                )
        if not time_adjusted_visemes:
            # Empty list of new visemes, no need to do anything
            return

        # Make sure visemes are sorted
        time_adjusted_visemes.sort(key=lambda x: x["time"])
        visemes_to_add = []
        for viseme, next_viseme in zip(
            time_adjusted_visemes, time_adjusted_visemes[1:]
        ):
            visemes_to_add.append(viseme)

            # People rarely move their mouth slowly whilst talking (except for expression)
            # Sometimes TTS will leave a big gap between sentances - we want to detect these
            # gaps and not have a slow interpolation during the gap - instead we hang at the
            # previous keyframe.
            if next_viseme["time"] - viseme["time"] > self.MAX_INTERP_TIME:
                extra_viseme = copy(next_viseme)
                extra_viseme["time"] = next_viseme["time"] - self.MAX_INTERP_TIME
                visemes_to_add.append(extra_viseme)
        visemes_to_add.append(time_adjusted_visemes[-1])

        if not self.last_viseme:
            # Queue is empty. Add a gentle rampup at the start to prevent a jump
            first_viseme = visemes_to_add[0]
            first_pose = pose_from_viseme(self.convert_viseme(first_viseme["viseme"]))

            # if somehow audio is delayed, only start the ramping up in advance at most
            start_point_time = first_viseme["time"] - self.MAX_RAMP_TIME
            if self.last_viseme is None or start_point_time > self.last_viseme["time"]:
                for name, base_val in BASE_POSE.items():
                    first_val = first_pose[name]

                    self.clip.curves[name].add(
                        start_point_time,
                        base_val,
                        INTERP_BEZIER,
                        (
                            (first_viseme["time"], base_val),
                            (start_point_time, first_val),
                        ),
                    )

        else:
            # Queue is not empty. We need to remove last 2 points
            # (which is last viseme and extra base pose, which are added at the end of this function)

            # Removing the last point is needed as it is a base pose added to prevent potential jumps at the end if visemes do not end in sil
            # Removing the second to last point is needed as we need to change the bezier handles for it in the curves

            for curve in self.clip.curves.values():
                del curve.nodes[-2:]

            # add the old point into the visemes list to regenerate handles
            visemes_to_add = [self.last_viseme] + visemes_to_add

        handle_array = self.generate_handles(visemes_to_add)

        # Note that interp handles are for AFTER the point they relate to for some reason?
        # This is why the code might look v confusing
        # When you set interp, you are saying how you will interp FROM this point, NOT TO
        for viseme, next_viseme, handles in zip(
            visemes_to_add, visemes_to_add[1:], handle_array
        ):
            pose = pose_from_viseme(self.convert_viseme(viseme["viseme"]))

            next_pose = pose_from_viseme(self.convert_viseme(next_viseme["viseme"]))

            for name, val in pose.items():
                next_val = next_pose[name]

                self.clip.curves[name].add(
                    viseme["time"],
                    val,
                    INTERP_BEZIER,
                    ((handles[0], val), (handles[1], next_val)),
                )

        # handle the end of the viseme sequence, to prevent a jump
        # by adding another keyframe with all values set to 0, 100 ms after the last viseme
        # usually last viseme is sil so this doesn't really matter much, but its still helpful
        self.last_viseme = visemes_to_add[-1]

        final_pose = pose_from_viseme(self.convert_viseme(self.last_viseme["viseme"]))
        self.stop_time = self.last_viseme["time"] + self.MAX_RAMP_TIME

        for name, val in final_pose.items():
            base_val = BASE_POSE[name]

            self.clip.curves[name].add(
                self.last_viseme["time"],
                val,
                INTERP_BEZIER,
                (
                    (self.stop_time, val),
                    (self.last_viseme["time"], base_val),
                ),
            )

            self.clip.curves[name].add(
                self.stop_time,
                0,
                INTERP_LINEAR,
            )

    def generate_handles(self, visemes):
        handle_array = []

        for viseme0, viseme1 in zip(visemes, visemes[1:]):
            viseme0_w = VISEMES[viseme0["viseme"]][2]
            viseme1_w = VISEMES[viseme1["viseme"]][2]

            viseme0_t = viseme0["time"]
            viseme1_t = viseme1["time"]

            handle0_t = viseme0_t + viseme0_w * (viseme1_t - viseme0_t)
            handle1_t = viseme1_t + viseme1_w * (viseme0_t - viseme1_t)

            handle_array.append((handle0_t, handle1_t))

        return handle_array

    def sample(self):
        """Return the current samples for each actuator and the levels of each viseme as a dictionary."""
        samples = self.clip.sample_curves(time_unix())

        return samples

    def __repr__(self):
        # Clip.__repr__ not deployed yet
        cr = f"Clip({dict(self.clip.curves.items())!r}, {self.clip.events!r})"
        return f"VisemeQueue<{cr}>"