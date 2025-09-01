import os
from pydantic_ai import RunContext
from AI_agents_template.models.base import Deps
from AI_agents_template.utils.utils import connect_to_database
import duckdb


class CtxWithDeps:
    def __init__(self, deps):
        self.deps = deps


# Shared/cached context globals
_db_connection = None
_cache_database_db = None


def get_runtime_ctx() -> RunContext:
    """
    Returns a RunContext[Deps] with a shared database connection and schema.
    Uses DB_PATH env var or defaults to './database.db'.
    """
    global _db_connection, _schema, _cache_database_db

    ## here you can make database connections for example
    db_path = os.environ.get("DB_PATH", "./database.db3")
    if _db_connection is None:
        _db_connection = connect_to_database(db_path)

    # handle webservice URL
    disable_cache_db = os.environ.get("DISABLE_CACHE", False)

    if _cache_database_db is None and not disable_cache_db:
        _cache_database_db = duckdb.connect(database=":memory:", read_only=False)
        _cache_database_db.execute("INSTALL spatial;")
        _cache_database_db.execute("LOAD spatial;")

    # combine all three into a Deps object
    deps = Deps(db_path=db_path, db_connection=_db_connection)
    # for now this is limited to the session
    deps.cache_database_db = _cache_database_db
    return CtxWithDeps(deps)
