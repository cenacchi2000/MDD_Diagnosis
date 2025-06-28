"""
 Updates:
     0.0.1: Function created
     0.0.2: Updated to work with motor boards V1.50.0 and above
            Doesn't look for paramemeters in non-existent channel 
     0.0.3: Added ErrorMonitor and board firmware versions
     0.0.4: Use ea.websocket.rocketchat instead of rocketchat_API
     0.0.5: Get robot name from self.robot.serial
     0.0.6: Use f-strings more and tidy up a little - run checks less frequently
     0.0.7: Migrate to Tritium 3 Scripts
     0.0.8: Fix cleanup
     0.0.9: Better tracking of appearing/disappearing boards
     0.0.10: Appearing boards are only info now so they don't create a notification storm
     0.0.11: Suppress Torso brake High level errors when torso brake is activated
     0.0.12: Added error reporting of thermal model limits
     0.0.13: Updated the way we put in rocketchat credentials
     0.0.14: Added messages from the LIDAR inputs
     0.0.15: Drop all currently acquired parameters for a device on disconnect
     0.0.16: Monitor for leak detected events and report to chat

Connecting to RocketChat:
     Please go to this link for full instructions:

     https://george.earts.dev/wiki/index.php/Tritium3_Getting_started_-_setting_up_credentials


     When deploying on a new robot you have to:
     1. Ask Mike to setup a rocketchat account for this robot
     2. Create a file at "~/rocketchat_credentials.json" which looks like this:
            '''
            {
                "url": "wss://chat.engineeredarts.co.uk/websocket",
                "username":  "<SERIAL/username-which-mike-gives-you>",
                "password": "<password-which-mike-gives-you>"
            }
            '''
     3. Go to Rocket Chat and "Create New->Channel"
     4. Name the new channel "robot-testing-<SERIAL>" with the <SERIAL> of this robot e.g. robot-testing-ac-0016
     5. Add the user which Mike created to the new channel
"""

error_monitor_version = "0.0.15"

import time
import datetime
from pprint import pprint
from subprocess import PIPE, run

from tritium.logreader import TritiumJournalReader

RocketChat = system.import_library("../Utils/rocketchat.py").RocketChat


def cmdline(command):
    result = run(command, stdout=PIPE, stderr=PIPE, universal_newlines=True, shell=True)
    return result


class Activity:
    """
    Monitor motor boards for errors and log aditional information
    """

    _requested_params = []

    status_error_code = {
        1: "Limit Error",
        2: "Sensor Error",
        3: "Current Error",
        4: "Voltage Error",
        5: "Communication Error",
        6: "Temperature Error",
        7: "Motor Driver Error",
        8: "High Level Error",
    }
    last_valve = None
    channel_id = None
    rocket_sub = None
    rocket = None

    ###################################################### CONFIG PARAMS ######################################################
    channel_name_template = "robot-testing-{}"  # Chat channel name where log messages will be sente, {} where robot's serial is replaced

    enable_debug_print = True
    proxy_device_host_name = "proxy_device_host_usb"
    log_on_chat = True  # Send messages to "robot-testing" rocket chat channel
    log_errors = (
        True  # Send errors found on external logs (control and proxy device host)
    )
    log_warnings = False  # Send warnings found on external logs periodically (seconds) (control and proxy device host)
    report_period = 901  # in minutes
    command_check_period = 0.2  # in sec check for new commands every second
    channel_check_period = 0.5  # (in secs) period between expensive channel checks
    # Boards with only 2 channels
    CHANNELS = {
        "Arm Humerus Left Motor Board": ["Channel 1", "Channel 2"],
        "Arm Humerus Right Motor Board": ["Channel 1", "Channel 2"],
        "Air Pump Motor Board": ["Channel 1", "Channel 2"],
    }

    # Otherwise use all channels
    DEFAULT_CHANNELS = ["Channel 1", "Channel 2", "Channel 3", "Channel 4"]

    ###################################################### HELPER FUNCTIONS ######################################################
    def check_for_commands(self):
        try:
            for msg in self.get_chat_messages():
                if msg == "!help":
                    help_msg = """*ErrorMonitor help section:*
                    - *!update* Display latest error messages since last report
                    - *!report* Display full report with warnings since last power cycle
                    - *!status* Display all channel latest satus
                    - *!status_enabled* Display all channels if the enabled or not
                    - *!status_thermal_model_temp* Display the thermal model temperature
                    - *!current* Display all channel motor current
                    - *!version* Display the ErrorMonitor version
                    - *!firmware* Display the firmware version of the boards"""

                    if self.log_on_chat:
                        self.send_chat_message(help_msg)

                if msg == "!update":
                    self.report()
                if msg == "!report":
                    # Reset logs to show everything
                    self.log_control["cursor"] = None
                    self.log_proxy_dev["cursor"] = None
                    self.log_warnings = True
                    self.report()
                    self.log_warnings = False
                if msg == "!status":
                    self.cmd_get_device_info("status", threshold=0)
                if msg == "!status_thermal_model_temp":
                    self.cmd_get_device_info("thermal_model_temp", threshold=60)
                if msg == "!status_enabled":
                    self.cmd_get_device_info("enable")
                if msg == "!current":
                    self.cmd_get_device_info("current")
                if msg == "!version":
                    msg = "ErrorMonitor V"
                    emoji = ":robot:"
                    msg += f"{error_monitor_version} {emoji}\n"
                    self.send_chat_message(msg)

                if msg == "!firmware":
                    host = system.unstable.owner.device_manager
                    print(host.device_hosts)
                    print(host._device_hosts_by_identifier)
                    msg = "Firmware versions:\n"
                    for h in host.device_hosts:
                        print(h.name, h.identifier)
                        if h.name.startswith("Proxy"):
                            for d in host.get_device_host(h.identifier).devices:
                                msg += f"{d.logical_name} ({d.serial}) *{d.device_class.version}*\n"
                    self.send_chat_message(msg)

        except Exception as e:
            if self.enable_debug_print:
                print("Too many rocketchat API request, slow down:", e)
            pass
        pass

    def cmd_get_device_info(self, key_name, filter="None", threshold=None):
        msg = "Device Statuses:\n"
        counter = 0
        # Check all channels for stuff to report
        for board, ch, channel in self.loop_channels():
            # Get parameter from board
            # status = self.get_param("{}.{}.Status.Error".format(board, ch))
            # encoder_warning = self.get_param("{}.{}.Sensors.Encoder SSI.Error bit".format(board, ch))
            value = channel[key_name]
            warning_emoji = ""
            try:
                pass
                if threshold is not None:
                    try:
                        if threshold < float(value):
                            warning_emoji = ":exclamation:"
                    except Exception as e:
                        print(e)
                        pass

            except e:
                print(e)
            pretty_value = f"{value:5.3f}".rstrip("0").rstrip(".")
            msg += (
                f"{warning_emoji} {self.board_names[board]} {ch} \t*{pretty_value}*\n"
            )

        self.send_chat_message(msg)

    def get_journal_log(self, logger):
        log_list = []

        if logger["cursor"] is None:
            logs = logger["handler"].tail()
        else:
            logs = logger["handler"].head(from_cursor=logger["cursor"])

        first = True
        for item in logs:
            if first:
                first = False
                continue
            logger["cursor"] = item["cursor"]
            if (item["level"] == "WARNING" and self.log_warnings) or (
                item["level"] == "ERROR" and self.log_errors
            ):
                log_list.append(item)

        return log_list

    def NUC_boot_mode(self):
        result = cmdline('/opt/ea/sbin/boot_mode | grep "current"')
        if "dev" in result.stdout:
            return "dev"
        else:
            return "customer"

    def log_error(self, msg):
        self.last_error_time = time.time()
        log.error(msg)
        msg = "{} ErrorMonitor: {}".format(time.ctime(), msg)
        msg = "@here\n" + msg
        if self.log_on_chat:
            self.send_chat_message(msg)

    def log_info(self, msg):
        log.info(msg)
        msg = "{} ErrorMonitor: {}".format(time.ctime(), msg)
        if self.log_on_chat:
            self.send_chat_message(msg)

    def report(self):
        chat_msg = ""

        # COLLECTED HERE
        if self.enable_debug_print:
            print("ErrorMonitor:")
        if self.log_on_chat:
            chat_msg += "*ErrorMonitor:*\n"

        # Empty buffer and print
        if len(self.warning_buffer):
            for msg in self.warning_buffer:
                if self.enable_debug_print:
                    print(msg)
                if self.log_on_chat:
                    chat_msg += msg + "\n"
        else:
            if self.enable_debug_print:
                print("-    Nothing to report!")
            if self.log_on_chat:
                chat_msg += "-    Nothing to report!\n"

        self.warning_buffer = []

        # CONTROL LOGS
        if self.enable_debug_print:
            print("\nTritium Scripts:")
        if self.log_on_chat:
            chat_msg += "*Tritium Scripts:*\n"

        logs = self.get_journal_log(self.log_control)
        if len(logs):
            for item in logs:
                if self.enable_debug_print:
                    print("-    [{}] {}".format(item["timestamp"], item["message"]))
                if self.log_on_chat:
                    chat_msg += "-    *[{}]* [{}] {}\n".format(
                        item["level"], item["timestamp"], item["message"]
                    )
        else:
            if self.enable_debug_print:
                print("-    Nothing to report!")
            if self.log_on_chat:
                chat_msg += "-    Nothing to report!\n"

        # PROXY DEVICE HOST LOGS
        if self.enable_debug_print:
            print("\nTritium node Proxy Device Host:")
        if self.log_on_chat:
            chat_msg += "*Tritium node Proxy Device Host:*\n"

        logs = self.get_journal_log(self.log_proxy_dev)
        if len(logs):
            for item in logs:
                if self.enable_debug_print:
                    print("-    [{}] {}".format(item["timestamp"], item["message"]))
                if self.log_on_chat:
                    chat_msg += "-    *[{}]* [{}] {}\n".format(
                        item["level"], item["timestamp"], item["message"]
                    )
        else:
            if self.enable_debug_print:
                print("-   Nothing to report!")
            if self.log_on_chat:
                chat_msg += "-    Nothing to report!"

        # Test Configuration
        if self.enable_debug_print:
            print("\nTesting parameters:")
        if self.log_on_chat:
            chat_msg += "\n*Testing parameters:*\n"

        if self.log_on_chat:
            if self.NUC_boot_mode() == "customer":
                chat_msg += " -    Robot is in customer mode\n"
            else:
                chat_msg += " -    Robot is in dev mode\n"

            chat_msg += " -    You can expect reports at every {}s".format(
                round(self.report_period)
            )
        # Send message to chat
        if self.log_on_chat:
            if self.log_on_chat:
                self.send_chat_message(chat_msg)

    def device_online(self, device):
        """
        Check if a board is present and online
        """

        host = system.unstable.owner.device_manager.get_device_host(
            self.proxy_device_host_name
        )
        for dev in host.devices:
            if dev.identifier == device and dev.online:
                return True
        return False

    def set_param(self, param, demand):
        self.params_by_name[param].demand = demand

    def get_param(self, param):
        return self.params_by_name[param].value

    def request_param(self, param):
        p = self.params_by_name[param]
        system.unstable.owner.device_manager.acquire_parameters([p])
        self._requested_params.append(p)

    def drop_params_from_device(self, device_identifier):
        to_drop = []
        for p in self._requested_params:
            if p.device.identifier == device_identifier:
                to_drop.append(p)
        system.unstable.owner.device_manager.release_parameters(to_drop)
        self._requested_params = [
            p for p in self._requested_params if p not in set(to_drop)
        ]

    def drop_params(self):
        system.unstable.owner.device_manager.release_parameters(self._requested_params)
        self._requested_params.clear()

    def update_boards(self, first_run=False):
        host = host = system.unstable.owner.device_manager.get_device_host(
            self.proxy_device_host_name
        )
        for dev in host.devices:
            if (("Motor" in dev.logical_name) and dev.online) and (
                dev.identifier not in self.boards
            ):
                if not first_run:
                    self.log_info(
                        "Board '{} ({})' connected +++".format(
                            dev.logical_name, dev.identifier
                        )
                    )
                channel_names = self.CHANNELS.get(
                    dev.logical_name, self.DEFAULT_CHANNELS
                )
                self.boards[dev.identifier] = {cn: {} for cn in channel_names}
                self.board_names[dev.identifier] = dev.logical_name
                if self.enable_debug_print:
                    print("Registering {}".format(dev.identifier))

                params_by_name = {}
                for p in dev.parameters:
                    fqpn = "{}.{}".format(dev.identifier, p.name_in_device_class)
                    params_by_name[fqpn] = p

                self.params_by_name.update(params_by_name)

                board = dev.identifier
                for ch in self.boards[dev.identifier]:
                    self.request_param(f"{board}.{ch}.Config.Enable")
                    self.request_param(f"{board}.{ch}.Status.Error")
                    self.request_param(f"{board}.{ch}.Status.Error Argument")
                    self.request_param(f"{board}.{ch}.Status.Error Argument 2")
                    self.request_param(f"{board}.{ch}.Fatigue.Fatigued")
                    self.request_param(
                        f"{board}.{ch}.Thermal Model.Thermal Model Limit"
                    )
                    self.request_param(f"{board}.{ch}.Thermal Model.Temperature")
                    self.request_param(f"{board}.{ch}.Sensors.Current")
                    self.request_param(f"{board}.{ch}.Sensors.Encoder SSI.Error bit")

                    self.boards[board][ch].update(
                        {
                            "status": 0,
                            "last_status": 0,
                            "fatigued": 0,
                            "last_fatigued": 0,
                            "thermal": 0,
                            "last_thermal": 0,
                        }
                    )
            elif (("Power Input" in dev.logical_name) and dev.online) and (
                dev.identifier not in self.boards
            ):
                if not first_run:
                    self.log_info(
                        "Board '{} ({})' connected +++".format(
                            dev.logical_name, dev.identifier
                        )
                    )
                self.boards[dev.identifier] = {}
                self.board_names[dev.identifier] = dev.logical_name

                params_by_name = {}
                for p in dev.parameters:
                    fqpn = "{}.{}".format(dev.identifier, p.name_in_device_class)
                    params_by_name[fqpn] = p

                self.params_by_name.update(params_by_name)

                board = dev.identifier
                self.request_param(f"{board}.General.LIDAR.Software Alarms Enable")
                self.request_param(f"{board}.General.LIDAR.Left Clear")
                self.request_param(f"{board}.General.LIDAR.Right Clear")

                self.boards[board]["Lidar Left"] = True
                self.boards[board]["Lidar Right"] = True

        for board in list(self.boards.keys()):
            if not self.device_online(board):
                self.log_error(
                    "Board '{} ({})' disconnected ---".format(
                        self.board_names[board], board
                    )
                )
                self.drop_params_from_device(board)

                for fqpn in list(self.params_by_name.keys()):
                    if fqpn.startswith(board):
                        self.params_by_name.pop(fqpn)

                self.board_names.pop(board)
                self.boards.pop(board)

    def loop_channels(self):  # Loop trough all channels in all boards
        for board in self.boards:
            for ch in [x for x in self.boards[board] if x.startswith("Channel")]:
                yield (board, ch, self.boards[board][ch])

    def log_buffer_warning(self, msg):
        self.warning_buffer.append(
            "-    *[WARNING]* [{}] {}".format(
                datetime.datetime.now().strftime("%Y-%b-%d %H:%M:%S"), msg
            )
        )

    def send_chat_message(self, msg):
        if not self.rocket:
            return
        # ea.websocket.rocketchat
        self.rocket.send(self.channel_name, msg)

    def get_chat_messages(self):
        # ea.websocket.rocketchat
        if self.rocket_sub:
            return [contents for username, contents in self.rocket_sub.get_pending()]
        return []

    def connect_chat(self):
        # Set rocket chat account
        # print("CONNECT CHAT")
        try:
            self.rocket = RocketChat()
            self.rocket_sub = self.rocket.subscribe(self.channel_name)
            print("CONNECTED CHAT")
        except Exception:
            self.rocket = None

    ###################################################### ACTUAL CODE ######################################################

    async def on_start(self):
        # Make channel name from template
        sernum = await system.unstable.stash.get("/profile/system/serial")
        self.channel_name = self.channel_name_template.format(sernum)
        print(self.channel_name)

        # Empty buffer for periodic log
        self.warning_buffer = []
        #         self.last_report_time = time.time()        # To send first report only after timout
        self.last_report_time = 0  # To send firs report on initialization
        self.last_command_check_time = 0  # when was last checked for new commands

        # last error time
        self.last_error_time = time.time()  # to see whe to restart the robot
        self.last_channel_check = time.time()

        # Set rocket chat account
        self.connect_chat()

        # Post on chat
        msg = "ErrorMonitor V"
        msg += f"{error_monitor_version} Online\n"
        self.send_chat_message(msg)

        # Get all connected motor boards identifiers
        self.boards = {}
        self.board_names = {}
        self.params_by_name = {}

        # Update boards but don't spam chat with ones that are new because they all are
        self.update_boards(first_run=True)

        # log handlers

        self.log_control = {
            "handler": TritiumJournalReader(
                log_identifier=None, service_name="tritium-node-scripts-py3.service"
            ),
            "cursor": None,
        }
        self.log_proxy_dev = {
            "handler": TritiumJournalReader(
                log_identifier=None,
                service_name="tritium-node-proxy-device-host-usb.service",
            ),
            "cursor": None,
        }

    def on_stop(self):
        self.drop_params()
        # Post on chat
        msg = "ErrorMonitor V"
        msg += "{} Offline\n".format(error_monitor_version)
        self.send_chat_message(msg)
        if self.rocket:
            self.rocket.client.close()

    @system.on_event("leak_detected_event")
    def on_leak_detected(self, msg):
        self.log_error(msg)

    @system.tick(fps=10)
    def on_tick(self):
        now = time.time()

        # Check if all boards are still connected
        # for board in self.boards:
        #      if(self.device_online(board) is False):
        #          self.log_error("Board '{}' disconnected".format(board))
        #          self.manager.start_control_function('SYS_ErrorMonitorStartup')
        #          self.stop()
        self.update_boards()

        if now - self.last_channel_check > self.channel_check_period:
            # Check all channels for stuff to report
            for board, ch, channel in self.loop_channels():
                # Get parameter from board
                channel["enable"] = self.get_param(f"{board}.{ch}.Config.Enable")
                channel["status"] = self.get_param(f"{board}.{ch}.Status.Error")
                channel["arg 1"] = self.get_param(f"{board}.{ch}.Status.Error Argument")
                channel["arg 2"] = self.get_param(
                    f"{board}.{ch}.Status.Error Argument 2"
                )
                channel["fatigued"] = self.get_param(f"{board}.{ch}.Fatigue.Fatigued")
                channel["thermal"] = self.get_param(
                    f"{board}.{ch}.Thermal Model.Thermal Model Limit"
                )
                channel["current"] = self.get_param(f"{board}.{ch}.Sensors.Current")
                # channel["encoder_biss_error_bit"] = channel["enable"] and self.get_param(f"{board}.{ch}.Sensors.Encoder SSI.Error bit")
                channel["thermal_model_temp"] = self.get_param(
                    f"{board}.{ch}.Thermal Model.Temperature"
                )

                # ======================================= Error Status =======================================
                # Check if status changed to an error state

                # Status changed
                if channel["status"] != channel["last_status"]:
                    # Error has gone scenario
                    if channel["status"] == 0:
                        if (
                            self.board_names[board] == "Torso Motor Board"
                            and channel["last_status"] == 8
                            and channel["last arg 1"] == 43
                        ):
                            # suppress Channel 2 so we dont log it in the channel twice
                            if ch == "Channel 1":
                                self.log_info("Torso brake deactivated")

                    # Error has just happened scenario
                    # status is not ok and  status is valid
                    if channel["status"] != 0 and channel["status"] is not None:
                        # Ignore Torso Motor Board.Channel 1.status = 8 - High Level Error with args
                        # This message comes up when the brake is activated.
                        if (
                            self.board_names[board] == "Torso Motor Board"
                            and channel["status"] == 8
                            and channel["arg 1"] == 43
                        ):
                            # suppress Channel 2 so we dont log it in the channel twice
                            if ch == "Channel 1":
                                self.log_info("Torso brake activated")
                        else:
                            self.log_error(
                                "`{}.{}.status` = {} - {} with args [{}, {}]".format(
                                    self.board_names[board],
                                    ch,
                                    channel["status"],
                                    self.status_error_code[channel["status"]],
                                    channel["arg 1"],
                                    channel["arg 2"],
                                )
                            )

                # update last
                channel["last_status"] = channel["status"]
                channel["last arg 1"] = channel["arg 1"]

                # ========================================== Fatigue =========================================
                #            if (channel["fatigued"] != channel["last_fatigued"]
                #                and channel["fatigued"] != 0
                #                and channel["fatigued"] is not None
                #               ):
                #                self.log_buffer_warning("{}.{} fatigued".format(board, ch))
                #                if(self.enable_debug_print): print("{}.{} fatigued".format(board, ch))
                #            # update last
                #            channel["last_fatigued"] = channel["fatigued"]

                # ========================================== Thermal =========================================
                if (
                    channel["thermal"] != channel["last_thermal"]
                    and channel["thermal"] != 0
                    and channel["thermal"] is not None
                ):
                    self.log_buffer_warning(f"{board}.{ch} thermal limit reached")
                    if self.enable_debug_print:
                        print(f"{self.board_names[board]}.{ch} thermal")
                    self.log_error(
                        "`{}.{}.Thermal Model.Thermal Model Limit = {}, {:3.1f} degrees".format(
                            self.board_names[board],
                            ch,
                            channel["thermal"],
                            channel["thermal_model_temp"],
                        )
                    )
                # update last
                channel["last_thermal"] = channel["thermal"]

                # ================================ Check if motor is running? ================================
                # how to test it without reling on statuses?

            if "Mesmer Power Input" in self.board_names.values():
                board = list(self.board_names.keys())[
                    list(self.board_names.values()).index("Mesmer Power Input")
                ]
                alarm_enable = self.get_param(
                    f"{board}.General.LIDAR.Software Alarms Enable"
                )
                if alarm_enable:
                    lidar_left = self.get_param(f"{board}.General.LIDAR.Left Clear")
                    lidar_right = self.get_param(f"{board}.General.LIDAR.Right Clear")
                    if lidar_left == False and self.boards[board]["Lidar Left"] == True:
                        self.log_info("Left LIDAR obstructed")
                    elif (
                        lidar_left == True and self.boards[board]["Lidar Left"] == False
                    ):
                        self.log_info("Left LIDAR cleared")
                    if (
                        lidar_right == False
                        and self.boards[board]["Lidar Right"] == True
                    ):
                        self.log_info("Right LIDAR obstructed")
                    elif (
                        lidar_right == True
                        and self.boards[board]["Lidar Right"] == False
                    ):
                        self.log_info("Right LIDAR cleared")
                    self.boards[board]["Lidar Left"] = lidar_left
                    self.boards[board]["Lidar Right"] = lidar_right

        if now - self.last_command_check_time > self.command_check_period:
            self.last_command_check_time = now
            self.check_for_commands()
        # ======================================== check logs ========================================
        # Periodic report
        # if now - self.last_report_time > self.report_period:
        #    self.report()
        #    self.last_report_time = now

        # Make sure rocket chat is connected
        if self.rocket is None:
            self.connect_chat()