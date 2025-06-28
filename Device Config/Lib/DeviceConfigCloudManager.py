import os
import re
import json
import shutil
import subprocess

import pygit2
from tritium import config


class DeviceConfigCloudManager:
    CONFIG_DIR = "/var/opt/tritium/profile/nodes/proxy_device_host_usb/device_states/"

    # location of the config repo folder. if it does not exist yet, it will clone it
    CONFIG_REPO_DIR = "/home/tritium/repos/device_configs"
    CUSTOMIZATION_DIR = "/home/tritium/repos/device_configs/t3_customizations/"
    CUSTOMIZATION_SUFFIX = "_customizations.json"

    # git details for pushing
    GIT_CREDENTIALS_FILE = "/home/tritium/public_repos_credentials.txt"
    GIT_USERNAME = "robot_access"
    GIT_TOKEN = "D4FGpAaqoQcXMN"
    GIT_EMAIL = "robot_access@ea"
    GIT_BRANCH = "master"

    CONFIG_REPO_URL = "https://repos.engineeredarts.co.uk/configuration/device_configs"

    DEVICE_STATES_FILE = "device_states.json"
    DEVICE_CUSTOMIZATION_FILE = "device_customization.json"

    def __init__(self):
        self.load_credentials_from_filesystem()
        self.clone_repository_if_does_not_exist(
            self.CONFIG_REPO_URL, self.CONFIG_REPO_DIR
        )
        self.repo = pygit2.Repository(self.CONFIG_REPO_DIR)

    def load_credentials_from_filesystem(self):
        try:
            with open(self.GIT_CREDENTIALS_FILE) as my_file:
                content = json.loads(my_file.read())
                self.GIT_USERNAME = content["username"]
                self.GIT_TOKEN = content["password"]
                self.GIT_EMAIL = content["email"]
            return True
        except Exception as e:
            pass

        return False

    def clone_repository_if_does_not_exist(self, repo_url, local_path):
        callbacks = pygit2.RemoteCallbacks(
            pygit2.UserPass(self.GIT_USERNAME, self.GIT_TOKEN)
        )
        # Check if repository already exists
        if os.path.exists(local_path):
            return
        else:
            print(f"Config repository does not exist. Cloning now...")
            pygit2.clone_repository(repo_url, local_path, callbacks=callbacks)

    def pull_repo(self):
        callbacks = pygit2.RemoteCallbacks(
            pygit2.UserPass(self.GIT_USERNAME, self.GIT_TOKEN)
        )
        self.repo.remotes["origin"].fetch(callbacks=callbacks)
        remote_master_id = self.repo.lookup_reference(
            f"refs/remotes/origin/{self.GIT_BRANCH}"
        ).target

        master_ref = self.repo.lookup_reference(f"refs/heads/{self.GIT_BRANCH}")
        master_ref.set_target(remote_master_id)
        # Terrible hack to fix set_target() screwing with the index
        self.repo.reset(master_ref.target, pygit2.GIT_RESET_HARD)

    def push_repo(self):
        callbacks = pygit2.RemoteCallbacks(
            pygit2.UserPass(self.GIT_USERNAME, self.GIT_TOKEN)
        )
        self.repo.remotes["origin"].push(
            [f"refs/heads/{self.GIT_BRANCH}"], callbacks=callbacks
        )

    def get_customizations(self):
        customizations = []
        for path in os.listdir(self.CUSTOMIZATION_DIR):
            name = path.replace(self.CUSTOMIZATION_SUFFIX, "")
            customizations.append(name)
        return customizations

    """
        Add config to the cloud: 
        The serial either could be a 
        * tritium_key (name + ID)
        * serial_id   (ID only)
        ex.: serial="USB BDC 1234567890AB" is OK
             serial="1234567890AB" is OK
    """

    async def add_config(self, serial, config, overwrite=False):
        # Check if arguments are

        # Get only the last 12 digit id from the serial if full serial is given
        serial_id = self.get_serial_id(serial)
        if serial_id is None:
            log.warning(
                f"Add config - Serial is not valid: {serial, config} - skipping."
            )
            return False

        # Check if we have customiztion data
        if not "device_customization" in config:
            log.warning(
                f"Add config - Customization is missing in config argument for {serial} - skipping."
            )
            return False

        # Check if we have device states
        if not "device_states" in config:
            log.warning(
                f"Add config - Device states missing in config argument for {serial} - skipping."
            )
            return False

        # check if folder for serial id number exists
        full_path = os.path.join(self.CONFIG_REPO_DIR, serial_id)

        if os.path.exists(full_path):
            if overwrite:
                log.info(
                    f"Add config - Config already exists in the cloud for {serial} - overwriting."
                )
                shutil.rmtree(full_path)
            else:
                # log.warning(f"Add config - Config already exists in the cloud for {serial} - skipping.")
                return False

        os.makedirs(full_path)

        # Writing the device states
        device_state_dest_path = os.path.join(
            self.CONFIG_REPO_DIR, serial_id, self.DEVICE_STATES_FILE
        )
        with open(device_state_dest_path, "x") as f:
            json.dump(config["device_states"], f, indent=4)

        # Writing the device customization
        customisation_dest_path = os.path.join(
            self.CONFIG_REPO_DIR, serial_id, self.DEVICE_CUSTOMIZATION_FILE
        )
        with open(customisation_dest_path, "x") as f:
            json.dump(config["device_customization"], f, indent=4)

        # commit and push changes
        index = self.repo.index

        # Add files to the index
        index.add(os.path.join(serial_id, self.DEVICE_STATES_FILE))
        index.add(os.path.join(serial_id, self.DEVICE_CUSTOMIZATION_FILE))
        self.repo.index.write()
        tree = self.repo.index.write_tree()
        parent = [self.repo.head.target]
        author = committer = pygit2.Signature(self.GIT_USERNAME, self.GIT_EMAIL)
        sernum = await system.unstable.stash.get("/profile/system/serial")
        commit_message = f"Added config for {serial} from {sernum}"
        oid = self.repo.create_commit(
            "HEAD", author, committer, commit_message, tree, parent
        )
        return True

    """
        Get config from the cloud: 
        The serial either could be a 
        * tritium_key (name + ID)
        * serial_id   (ID only)
        ex.: serial="USB BDC 1234567890AB" is OK
             serial="1234567890AB" is OK
    """

    def get_config(self, serial):
        serial_id = self.get_serial_id(serial)
        if serial_id is None:
            log.warning(f"Get config - Serial is not valid: {serial}")
            return None

        if serial_id in self.get_stored_serials():
            device_customization_path = os.path.join(
                self.CONFIG_REPO_DIR, serial_id, self.DEVICE_CUSTOMIZATION_FILE
            )
            device_states_path = os.path.join(
                self.CONFIG_REPO_DIR, serial_id, self.DEVICE_STATES_FILE
            )

            with open(device_customization_path) as f:
                device_customization = json.load(f)

            with open(device_states_path) as f:
                device_states = json.load(f)

            return {
                "device_states": device_states,
                "device_customization": device_customization,
            }

        return None

    """
        Get a default control definitios from the cloud.
        Robot is a robot type to look for defaults from e.g. "Ameca"
    """

    def get_default_controls(self, robot):
        defaults_dir = f"{robot} templates"
        controls_path = os.path.join(
            self.CONFIG_REPO_DIR, defaults_dir, "controls.json"
        )

        with open(controls_path) as f:
            controls = json.load(f)
            return controls

        return None

    """
        Get a default config from the cloud.
        Robot is a robot type to look for defaults from e.g. "Ameca"
        Board is the location in the robot the board to find a config for is
        e.g. "Clavicle and Shoulder Right Motor Board"
    """

    def get_default_config(self, robot, board):
        defaults_dir = f"{robot} templates"
        if not os.path.isdir(os.path.join(self.CONFIG_REPO_DIR, defaults_dir, board)):
            return None

        device_customization_path = os.path.join(
            self.CONFIG_REPO_DIR, defaults_dir, board, self.DEVICE_CUSTOMIZATION_FILE
        )
        device_states_path = os.path.join(
            self.CONFIG_REPO_DIR, defaults_dir, board, self.DEVICE_STATES_FILE
        )

        with open(device_customization_path) as f:
            device_customization = json.load(f)

        with open(device_states_path) as f:
            device_states = json.load(f)

        return {
            "device_states": device_states,
            "device_customization": device_customization,
        }

    """
        example.: returns  1234567890AB from "USB BDC 1234567890AB"
    """

    def get_serial_id(self, serial):
        if serial is None:
            return None
        pattern = r".*([A-F0-9]{12})$"
        match = re.match(pattern, str(serial))
        if match:
            return str(match.group(1))
        return None

    """
        example.: 
        USB BDC 1234567890AB - True
        1234567890AB - True
        Mesmer Power Distro 1234567890AB - True
        Mesmer Power Distro - False
        Left Arm Motor Board - False
    """

    def contains_valid_serial_id(self, name):
        if self.get_serial_id(name) is not None:
            return True
        return False

    """
        1234567890AB - True
        USB BDC 1234567890AB - False
        Mesmer Power Distro 1234567890AB - False
        Mesmer Power Distro - False
        Left Arm Motor Board - False
    """

    def is_valid_serial_id(self, serial):
        # Regular expression pattern that checks for 12 alphanumeric characters
        pattern = r"^[A-F0-9]{12}$"

        return bool(re.match(pattern, serial))

    def get_stored_serials(self):
        path = self.CONFIG_REPO_DIR
        # Check if the path exists
        if not os.path.exists(path):
            return []

        serials = []
        for folder in os.listdir(path):
            if os.path.isdir(os.path.join(path, folder)) and self.is_valid_serial_id(
                folder
            ):
                serials.append(folder)

        return serials
