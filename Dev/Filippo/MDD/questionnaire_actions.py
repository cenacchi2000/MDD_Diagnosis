from typing import List

ACTION_UTIL = system.import_library("../../../HB3/chat/actions/action_util.py")
ActionRegistry = ACTION_UTIL.ActionRegistry
ActionBuilder = ACTION_UTIL.ActionBuilder
Action = ACTION_UTIL.Action

bdi = system.import_library("./BeckDepression.py")
dass = system.import_library("./dass21_assessment.py")
eq5d = system.import_library("./eq5d5l_assessment.py")
pcs = system.import_library("./pain_catastrophizing.py")
psqi = system.import_library("./pittsburgh_sleep.py")
csi = system.import_library("./central_sensitization.py")
odi = system.import_library("./oswestry_disability_index.py")
bpi = system.import_library("./bpi_inventory.py")


@ActionRegistry.register_builder
class RunQuestionnaires(ActionBuilder):
    """Provide actions to run each MDD questionnaire."""

    def factory(self) -> List[Action]:
        async def run_beck_depression():
            """Run the Beck Depression Inventory."""
            await bdi.run_beck_depression_inventory()
            return "beck_depression_finished"

        async def run_dass21():
            """Run the DASS-21 assessment."""
            await dass.run_dass21()
            return "dass21_finished"

        async def run_eq5d5l():
            """Run the EQ5D5L assessment."""
            await eq5d.run_eq5d5l_questionnaire()
            return "eq5d5l_finished"

        async def run_pcs():
            """Run the Pain Catastrophizing Scale."""
            await pcs.run_pcs()
            return "pcs_finished"

        async def run_psqi():
            """Run the Pittsburgh Sleep Quality Index."""
            await psqi.run_psqi()
            return "psqi_finished"

        async def run_csi_inventory():
            """Run the CSI inventory and worksheet."""
            await csi.run_csi_inventory()
            await csi.run_csi_worksheet()
            return "csi_finished"

        async def run_odi():
            """Run the Oswestry Disability Index."""
            await odi.run_odi()
            return "odi_finished"

        async def run_bpi():
            """Run the Brief Pain Inventory."""
            await bpi.run_bpi()
            return "bpi_finished"

        return [
            run_bpi,
            run_csi_inventory,
            run_dass21,
            run_eq5d5l,
            run_odi,
            run_pcs,
            run_psqi,
            run_beck_depression,
        ]
