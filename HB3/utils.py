def _resolve_path(path, my_path):
    if not path.startswith("/"):
        parts = [*my_path.split("/")[:-1]]
        for p in path.split("/"):
            if p == ".":
                continue
            elif p == "..":
                parts.pop()
            else:
                parts.append(p)
        resolved = "/".join(parts)
    else:
        resolved = path[1:]
    return resolved


def start_other_script(system, relative_path):
    # TODO: don't rely on this private attribute
    other_path = system._path
    script_path = _resolve_path(relative_path, other_path)
    return system.unstable.state_engine.start_activity(
        cause=f"started by script: {other_path!r}",
        activity_class="script",
        properties={
            "script": script_path,
            # TODO: Don't hardcode this!
            "script_file_path": f"/var/opt/tritium/scripts/{script_path}",
        },
    )


def stop_other_script(system, relative_path_or_local_activity):
    if not isinstance(relative_path_or_local_activity, str):
        system.unstable.state_engine.stop_activity(
            f"stopped by script: {system._path!r}", relative_path_or_local_activity
        )
        return

    # TODO: don't rely on this private attribute
    other_path = system._path
    script_path = _resolve_path(relative_path_or_local_activity, other_path)
    for activity in system.unstable.state_engine._state.activities:
        if activity.get_property("script") == script_path:
            # TODO: don't rely on this private attribute
            system.unstable.state_engine.stop_activity(
                f"stopped by script: {system._path!r}", activity
            )


def is_other_script_running(system, relative_path):
    other_path = system._path
    script_path = _resolve_path(relative_path, other_path)
    for activity in system.unstable.state_engine._state.activities:
        if activity.get_property("script") == script_path:
            return True
    return False


class ParameterHandler:
    _requested_params = []

    def __init__(self, system):
        self.device_manager = system.unstable.owner.device_manager
        self.refresh_params()

    def refresh_params(self):
        devices = self.device_manager.devices
        params_by_name = {}

        for d in devices:
            for p in d.parameters:
                # print(vars(p))
                fqpn = "{}.{}".format(d.logical_name, p.name)
                # print(fqpn)
                params_by_name[fqpn] = p
        self.params_by_name = params_by_name

    def deinit(self):
        for p in self._requested_params:
            self.drop_param(p)

    def set_param(self, param, demand):
        try:
            self.params_by_name[param].demand = demand
        except Exception:
            # print("Cannot set parameter", e)
            pass

    def get_param(self, param):
        return self.params_by_name[param].value

    def request_param(self, param):
        p = self.params_by_name[param]
        self.device_manager.acquire_parameters([p])
        self._requested_params.append(param)

    def drop_param(self, param):
        p = self.params_by_name[param]
        self.device_manager.release_parameters([p])
        self._requested_params.remove(param)

    def requested_params(self):
        return self._requested_params