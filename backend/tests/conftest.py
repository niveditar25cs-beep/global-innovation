import sys
from pathlib import Path
import pytest
import pytest_asyncio

# Ensure backend root is on sys.path for test discovery
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.data_access.database import async_engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_engine_after_test():
    yield
    await async_engine.dispose()
