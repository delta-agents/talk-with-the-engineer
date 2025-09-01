import os
from pydantic_ai import RunContext
from skip_the_engineer.models.base import Deps
from skip_the_engineer.utils.utils import connect_to_database
import duckdb


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
