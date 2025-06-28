from tritium.client.client import Client


class ObjectDetectionClient(Client):
    """
    Client for the Object Detection node.
    """

    def __init__(self, owner, name="Object Detection", api_address=None, **settings):
        super().__init__(owner=owner, name=name, api_address=api_address, **settings)

    def start_object_detection(self):
        self.call_api("start_object_detection", callback=None)

    def stop_object_detection(self):
        self.call_api("stop_object_detection", callback=None)
