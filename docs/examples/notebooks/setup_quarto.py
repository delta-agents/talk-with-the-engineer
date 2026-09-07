import os
from pathlib import Path
from dotenv import load_dotenv
from talk_with_the_engineer.interface.mcp.connections import get_runtime_ctx
import logging

logger = logging.getLogger("AI_agent")
logger.setLevel(logging.WARNING)
httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


def setup_dot_env(download_schemas: bool = False):
    logger.info("Setting up .env file")
    work_dir = Path(__file__).parent.parent.parent.parent
    env_path = work_dir / "env"
    env_template = env_path / ".env.example"
    env_copy = env_path / ".env"
    if not env_copy.exists():
        env_copy.write_text(env_template.read_text())
    load_dotenv(dotenv_path=env_copy)

    os.chdir(work_dir)
    ctx = get_runtime_ctx()
    return ctx
