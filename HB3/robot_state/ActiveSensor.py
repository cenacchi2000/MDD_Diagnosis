"""
This is a global resource that holds information related to the active sensor.
"""

from dataclasses import dataclass

sr = system.import_library("../lib/shared_resources.py")


@sr.global_resource
@dataclass
class ActiveSensor:
    name: str = None
    neutral: str = None
