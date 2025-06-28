"""
There are several ways to perform logging from a script
"""

print("You can use the standard print function (outputs similarly to log.info)")


class Activity:
    def on_start(self):
        log.warning("all log.* calls accept a context argument", context="on_start")

        try:
            5 / 0
        except Exception:
            log.exception(
                "trying to do the impossible",
                # with_stack_trace=False will prevent logging the entire stacktrace
                with_stack_trace=True,  # True is the default
                # warning=True will log at "warning level" instead of "error"
                warning=False,  # False is the default
            )
