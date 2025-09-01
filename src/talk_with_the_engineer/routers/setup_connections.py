from pydantic_ai import RunContext
from talk_with_the_engineer.models.base import Deps


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


def get_runtime_ctx() -> RunContext:
    """
    Returns a RunContext[Deps] with a shared dependencies.
    for now unused.
    Leave in for compatibility later.
    """
    # combine all three into a Deps object
    deps = Deps()
    return CtxWithDeps(deps)
