import os
import random
from asyncio import sleep


class Activity:
    # Seconds from last sequence stopping to next playing
    INTERVAL = 0
    # Seconds till sequence is skipped if no play notification is received
    TIMEOUT = 1
    # Seconds to delay the start of the first played sequence
    START_DELAY = 2

    LOOP = True
    SHUFFLE = False

    SEQS = (
        ### Individual test routines ###
        # "Animations.dir/System.dir/Testing.dir/", # Adding a folder will play all animations in that folder.
        # "Animations.dir/System.dir/Testing.dir/Ameca Test - Neck.project",
        # "Animations.dir/System.dir/Testing.dir/Ameca Test - Hands.project",
        # "Animations.dir/System.dir/Testing.dir/Ameca Test - Face G2.project",
        # "Animations.dir/System.dir/Testing.dir/Ameca Test - Arms and Torso.project",
        ### Full body stock animations ###
        "Animations.dir/System.dir/TelepresenceUI.dir/Impressions.dir/Ameca_G2_Kennedy.project",
        "Animations.dir/System.dir/TelepresenceUI.dir/Impressions.dir/Ameca_G2_OscarWilde.project",
        "Animations.dir/System.dir/TelepresenceUI.dir/Impressions.dir/Ameca_G2_WalkingFalling.project",
        ### Full Body excercise routine, tests all axis to full limits ###
        # "Animations.dir/System.dir/TelepresenceUI.dir/Impressions.dir/Ameca_G2_Excercise_Routine.project",
    )

    async def on_start(self):
        self.make_sequences_iterator()
        if self.START_DELAY:
            self.on_tick.pause()
            await sleep(self.START_DELAY)
            self.on_tick.resume()

    def on_stop(self):
        if self._activity:
            system.unstable.state_engine.stop_activity(
                cause="Auto Playlist Stopped", activity=self._activity
            )
            self._activity = None

    def make_sequences_iterator(self):
        BASE_DIR = "/var/opt/tritium/content/"
        sequences = []
        for s in self.SEQS:
            file_path = os.path.join(BASE_DIR, s)
            if s.endswith(".project"):
                if not os.path.exists(file_path):
                    print("Missing file:", file_path)
                    continue
                sequences.append(file_path)
            else:
                for base, dirs, files in os.walk(file_path):
                    for d in dirs:
                        if d.endswith(".project"):
                            sequences.append(os.path.join(base, d))
                    # Avoid recursing into folders that are intended to look like files in tritium
                    dirs[:] = [d for d in dirs if d.endswith(".dir")]

        if self.SHUFFLE:
            random.shuffle(sequences)

        self.iter_seqs = iter(sequences)

    def get_next(self):
        try:
            seq = next(self.iter_seqs)
        except StopIteration:
            if self.LOOP:
                self.make_sequences_iterator()
                seq = next(self.iter_seqs)
            else:
                self.stop()
                return
        return seq

    def play(self, file_path):
        if not os.path.exists(file_path):
            print("Missing file:", file_path)
            return
        return system.unstable.state_engine.start_activity(
            # causes should be provided for any changes to the state engine's activities
            cause="Auto Playlist",
            # the name of the activity
            activity_class="playing_sequence",
            # properties of the activity e.g. file path
            properties={"file_path": file_path},
        )

    _activity = None

    @system.tick(fps=5)
    async def on_tick(self):
        if self._activity:
            if not self._activity.stopped:
                return
            probe("playing", None)
            self._activity = None

        await sleep(self.INTERVAL)
        next_seq = self.get_next()
        if next_seq is not None:
            probe("playing", next_seq)
            self._activity = self.play(next_seq)