import json

from ea.websocket.rocketchat import RocketChat as RocketChatBase


def RocketChat():
    try:
        with open("/home/tritium/rocketchat_credentials.json") as fd:
            credentials = json.load(fd)
            return RocketChatBase(
                credentials.get("url", "wss://chat.engineeredarts.co.uk/websocket"),
                credentials["username"],
                credentials["password"],
            )
    except FileNotFoundError:
        raise Exception("Rocketchat API key not properly set")
