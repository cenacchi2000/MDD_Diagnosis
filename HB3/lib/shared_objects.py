import weakref


class SharedObjectSet:
    def __init__(self, topic):
        self.objects = weakref.WeakSet()
        self._evt_name = f"shared-objects-{topic}"
        system.messaging.post(self._evt_name, {"set": self.objects})

    def on_message(self, evt_name, data):
        if evt_name == self._evt_name:
            o = data.get("object")
            if o is None:
                return
            self.objects.add(o)


class SharedObjectRef:
    def __init__(self, topic):
        self.object = lambda: None
        self._evt_name = f"shared-objects-{topic}"
        system.messaging.post(self._evt_name, {"ref": self})

    def on_message(self, evt_name, data):
        if evt_name == self._evt_name:
            o = data.get("object")
            if o is None:
                return
            self.object = weakref.ref(o)


class SharedObject:
    def __init__(self, topic):
        self._evt_name = f"shared-objects-{topic}"
        system.messaging.post(self._evt_name, {"object": self})

    def on_message(self, evt_name, data):
        if evt_name == self._evt_name:
            s = data.get("set")
            if s is not None:
                s.add(self)
            s = data.get("ref")
            if s is not None:
                s.object = weakref.ref(self)