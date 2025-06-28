perception_state = system.import_library("../perception_state.py").perception_state


async def get_good_frame():
    if (image_b64 := perception_state.last_good_image_b64) is not None:
        return image_b64
    else:
        raise Exception("Error finding image.")