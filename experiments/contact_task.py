"""External contact task using raw evaluator force; does not edit world dynamics."""

from excavation_sim.tasks import ExcavationTask, ExcavationTaskConfig


class ContactTask(ExcavationTask):
    def __init__(self):
        super().__init__(ExcavationTaskConfig(kind="probe", contact_force_n=10, time_limit_s=3))
