"""Explicit, source-checked correction for the pinned Newton residual scratch array.

Newton 1.6.0 evaluates the stress residual at inactive nodes whose temporary
stress deltas are not written by the colored solve. Initialize those entries.
This process-wide hook is installed once before building any testbed soil solver.
It changes no material parameters and does not establish solver convergence.
"""

import hashlib
import importlib.metadata
import inspect
from functools import wraps
from threading import Lock

WORKAROUND_ID = "newton-1.6.0-initialize-stress-delta-v1"
_EXPECTED_INIT_SHA256 = "2a1c0588edf1a88731457534d6a9177bd71ff097177a29f46bace8e0e9d577e3"
_LOCK = Lock()


def install_stress_delta_initialization() -> str:
    from newton._src.solvers.implicit_mpm.solve_rheology import _RheologySolver

    with _LOCK:
        current = _RheologySolver.__init__
        if getattr(current, "_excavation_workaround", None) == WORKAROUND_ID:
            return WORKAROUND_ID
        if importlib.metadata.version("newton") != "1.6.0":
            raise RuntimeError("Newton residual workaround requires review for this version")
        source = inspect.getsource(current).replace("\r\n", "\n").encode()
        if hashlib.sha256(source).hexdigest() != _EXPECTED_INIT_SHA256:
            raise RuntimeError("Newton residual constructor differs from the reviewed source")

        @wraps(current)
        def initialized(self, *args, **kwargs):
            current(self, *args, **kwargs)
            self.delta_stress.zero_()

        initialized._excavation_workaround = WORKAROUND_ID
        _RheologySolver.__init__ = initialized
    return WORKAROUND_ID
