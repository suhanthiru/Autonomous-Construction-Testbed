from excavation_sim.core import JointCommand


class HoldPolicy:
    def reset(self, seed):
        pass

    def act(self, observation):
        return JointCommand((0.0, 0.0, 0.0, 0.0))
