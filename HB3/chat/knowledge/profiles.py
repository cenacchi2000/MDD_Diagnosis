"""
Log all the events which occurs in the short term.
"""

import json
from pathlib import Path

INTERACTION_HISTORY = system.import_library("./interaction_history.py")
ENVIRONMENT_KNOWLEDGE = system.import_library("./environment_knowledge.py")
STATE = system.import_library("./environment_knowledge.py")

MAX_MEMORY_LEN = 10

functions_path = Path(__file__).parent / "profiles_function_description.json"

with open(functions_path) as fd:
    FUNCTIONS = json.load(fd)
llm_interface = system.import_library("../../lib/llm/llm_interface.py")


SYSTEM_PROMPT_TEMPLATE = """Update the known information about the participant refered to as "{PERSON}" in the given conversation.

Note that Person x (e.g. Person 1, Person 2) are just internal identifiers. These are NOT the real names of the people, and you MUST NOT attempt to save these as names.

You will be given the previously known information about the participant as JSON.

Respond using the provided function to return a new, updated JSON object which encompasses the previously known knowledge as well as information learnt during the conversation.

Try to keep entries in the json information short, so if you can combine list elements / words into one, do this. (e.g. if there were entries in "likes" for "boats" and "sailboats", you could combine these into "boats").

If someone asks Ameca to forget some information about them, leave it out from the output json.
If they have information that contrasts with previously known information, make sure to update that entry in the output.

If you learn no knew information, just return the previously known information with any possible simplifications applied.
"""

USER_PROMPT_TEMPLATE = """PREVIOUSLY KNOWN INFORMATION about "{PERSON}"
{PREVIOUSLY_KNOWN_INFORMATION}

CONVERSATION:
{CONVERSATION}
"""


async def update_from_conversation(person_object):
    try:
        person_name = f"Person {person_object.id}"
        interaction_history = INTERACTION_HISTORY.InteractionHistory()
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(PERSON=person_name)
        if (
            conversation := interaction_history.get_person_conversation(person_name)
        ) is not None:
            user_prompt = USER_PROMPT_TEMPLATE.format(
                PERSON=person_name,
                CONVERSATION=conversation,
                PREVIOUSLY_KNOWN_INFORMATION=ENVIRONMENT_KNOWLEDGE.get_profiles(
                    person_object.id
                ),
            )
        else:
            return None
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        response = await llm_interface.run_chat(
            model="gpt-4-0613", messages=messages, functions=FUNCTIONS
        )

        async def handle_function(fun_call):
            if fun_call["name"] == "return_info" and fun_call["arguments"]:
                info = fun_call["arguments"]

                log.info("SAVING INFO: ", info)
                await person_object.save_info(info)
                return
            if fun_call["name"] == "forget_person":
                log.info("Forgetting person: ", person_object.id)
                await person_object.save_info(None)
                return

        if response["tool_calls"]:
            for fun_call in response["tool_calls"]:
                await handle_function(fun_call)
        elif response["function_call"]:
            handle_function(response["function_call"])
        else:
            log.warning("No information saved! Response was:", response["value"])

    except Exception as e:
        print(f"ERROR getting new profile for Person {person_object.id}!")
        print(e)