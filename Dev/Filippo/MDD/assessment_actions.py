from typing import List

ACTION_UTIL = system.import_library("../../../HB3/chat/actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action

mdd_main = system.import_library("./main.py")


@ActionRegistry.register_builder
class RunMDDAssessment(ActionBuilder):
    """Action to run the full MDD assessment workflow."""

    def factory(self) -> List[Action]:
        async def run_full_assessment() -> str:
            await mdd_main.main()
            return "mdd_assessment_finished"

        return [run_full_assessment]
