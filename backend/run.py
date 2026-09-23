import sys
from pathlib import Path
import uvicorn

# Ensure the backend directory is in the Python module search path
backend_dir = Path(__file__).resolve().parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.config import settings

if __name__ == "__main__":
    print(f"Starting {settings.APP_NAME} server on {settings.HOST}:{settings.PORT}...")
    print(f"API Docs available at: http://localhost:{settings.PORT}/docs")
    print(f"API Prefix: {settings.API_PREFIX}")
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=(settings.APP_ENV == "development"),
        log_level="info"
    )
