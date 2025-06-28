"""
Using Stash

>>> stash.get("path/to/data")
>>> view = stash.get_view("path/to/data", my_on_ready_func, my_on_change_func)
>>> view.close()

N.B. Making changes to Stash shouldn't be done from scripts if avoidable

>>> stash.set(path, ["some", {"data": "and that"}])
>>> stash.set(path, ["some", "data"])
>>> stash.set(path, "data")
"""


class Activity:
    async def on_start(self):
        # system.stash can be used to read from the JSON data tree (the 'stash') used by
        # the robot to store non-realtime data e.g. node configs, connected devices
        restart_required = await system.unstable.stash.get(
            "/runtime/status/restart_required"
        )
        print("restart_required", restart_required)

        # It is also possible to subscribe to sections of the data tree using
        # >>> view = stash.get_view(path, my_on_ready_func, my_on_change_func)

        # you must manually close opened views with
        # >>> view.close()
