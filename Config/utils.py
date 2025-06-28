def module_to_dict(module):
    return {
        key: value
        for key, value in module.__dict__.items()
        if (not key.startswith("__")) and (not key.endswith("__"))
    }


def get_layered_config(default_module, robot_module):
    config = module_to_dict(default_module)
    if robot_module is not None:
        config.update(module_to_dict(robot_module))
    return config


def clean_phrase(phrase: str) -> str:
    """Cast a phrase to lower case and remove punctuation."""
    return phrase.strip().lower().translate(str.maketrans("", "", ",.!;"))
