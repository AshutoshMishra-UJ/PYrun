import sys
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
import subprocess
import tempfile
import os
import pathlib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="PyRun API", version="1.0.0")

BASE_DIR = pathlib.Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")


class CodeRequest(BaseModel):
    code: str


class HealthResponse(BaseModel):
    status: str
    python_version: str


class RunResponse(BaseModel):
    status: str
    stdout: str
    stderr: str


PYTHON_BIN = os.environ.get("PYTHON_BIN", sys.executable)


@app.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthResponse(
        status="healthy",
        python_version=sys.version.split()[0]
    )


@app.post("/run", response_model=RunResponse)
async def run_code(request: CodeRequest):
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(request.code)
        tmp_path = f.name

    logger.info(f"Executing code in {tmp_path}")

    try:
        result = subprocess.run(
            [PYTHON_BIN, tmp_path],
            capture_output=True,
            text=True,
            timeout=2
        )
        return RunResponse(
            status="success",
            stdout=result.stdout,
            stderr=result.stderr,
        )
    except subprocess.TimeoutExpired:
        return RunResponse(
            status="timeout",
            stdout="",
            stderr="Execution timed out after 2 seconds.",
        )
    except Exception as e:
        logger.error(f"Execution error: {e}")
        return RunResponse(
            status="error",
            stdout="",
            stderr=str(e),
        )
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
