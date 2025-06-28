def tritium_version():
    """
    Return Tritium version, for example, "3.1".
    """
    try:
        for component in system.components.components:
            if component["type"] == "system":
                return component["properties"]["version"]
    except Exception:
        return "3.0"
