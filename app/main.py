"""FastAPI app: HTTP routes, reminder loop, static UI."""
import asyncio
import logging
import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app import db, service, tracker

ROOT = Path(__file__).resolve().parent.parent
REMINDER_INTERVAL_S = 300
log = logging.getLogger("actiongraph")


def load_env(path: Path = ROOT / ".env") -> None:
    if path.exists():
        for line in path.read_text().splitlines():
            key, sep, val = line.partition("=")
            if sep and not key.strip().startswith("#"):
                os.environ.setdefault(key.strip(), val.strip().strip('"'))


class IngestIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    date: date
    transcript: str = Field(min_length=10, max_length=60_000)
    attendees: list[str] = Field(default_factory=list, max_length=50)


class ApproveIn(BaseModel):
    text: str | None = Field(default=None, max_length=500)
    owner: str | None = Field(default=None, max_length=100)
    deadline: date | None = None
    subject: str | None = Field(default=None, max_length=200)
    value: str | None = Field(default=None, max_length=200)


class PostIn(BaseModel):
    item_ids: list[int] = Field(min_length=1, max_length=100)
    confirm: bool  # explicit human confirmation is required before anything is posted


async def reminder_loop() -> None:
    while True:
        try:
            service.run_reminders(datetime.now())
        except Exception:
            log.exception("reminder loop failed")
        await asyncio.sleep(REMINDER_INTERVAL_S)


@asynccontextmanager
async def lifespan(_: FastAPI):
    load_env()
    db.connect()
    task = asyncio.create_task(reminder_loop())
    yield
    task.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Action Graph AI", lifespan=lifespan)

    @app.exception_handler(service.NotFound)
    async def not_found(_: Request, exc: service.NotFound):
        return JSONResponse({"error": {"code": "NOT_FOUND", "message": str(exc)}}, status_code=404)

    @app.exception_handler(service.InvalidState)
    async def invalid(_: Request, exc: service.InvalidState):
        return JSONResponse({"error": {"code": "INVALID_STATE", "message": str(exc)}}, status_code=409)

    @app.exception_handler(tracker.TrackerError)
    async def tracker_failed(_: Request, exc: tracker.TrackerError):
        return JSONResponse({"error": {"code": "TRACKER_ERROR", "message": str(exc)}}, status_code=502)

    @app.get("/api/health")
    def health():
        return {"status": "ok", "llm": bool(os.getenv("ANTHROPIC_API_KEY")), "repo": tracker.repo()}

    @app.post("/api/meetings", status_code=201)
    def ingest(body: IngestIn):
        return service.ingest(body.title, body.date, body.transcript, [a.strip() for a in body.attendees if a.strip()])

    @app.get("/api/meetings")
    def meetings():
        return db.rows("SELECT id, title, date, extractor FROM meetings ORDER BY date DESC, id DESC")

    @app.get("/api/meetings/{meeting_id}")
    def meeting(meeting_id: int):
        return service.meeting(meeting_id)

    @app.get("/api/items")
    def items(status: str | None = None):
        return service.items(status=status)

    @app.post("/api/items/{item_id}/approve")
    def approve(item_id: int, body: ApproveIn):
        edits = body.model_dump(exclude_none=True)
        if "deadline" in edits:
            edits["deadline"] = edits["deadline"].isoformat()
        return service.approve(item_id, edits)

    @app.post("/api/items/{item_id}/reject")
    def reject(item_id: int):
        return service.reject(item_id)

    @app.post("/api/items/{item_id}/done")
    def done(item_id: int):
        return service.complete(item_id)

    @app.post("/api/post")
    def post(body: PostIn):
        if not body.confirm:
            raise HTTPException(400, "confirm must be true; nothing is posted without explicit confirmation")
        return service.post(body.item_ids)

    @app.post("/api/reminders/run")
    def run_reminders(now: datetime | None = None, window_hours: int = 48):
        return service.run_reminders(now or datetime.now(), window_hours)

    @app.get("/api/reminders")
    def reminders():
        return service.reminders()

    @app.post("/api/reminders/{reminder_id}/post")
    def post_reminder(reminder_id: int):
        return service.post_reminder(reminder_id)

    @app.get("/api/digest")
    def digest(week_start: date | None = None):
        today = date.today()
        return service.digest(week_start or today - timedelta(days=today.weekday()))

    @app.get("/api/graph")
    def graph():
        return service.graph()

    @app.get("/api/stats")
    def stats():
        return service.stats()

    @app.get("/api/eval")
    def eval_results():
        import json

        return [json.loads(f.read_text()) for f in sorted((ROOT / "evals").glob("results_*.json"))]

    @app.get("/api/samples")
    def samples():
        return [{"name": p.stem, "text": p.read_text()} for p in sorted((ROOT / "samples").glob("*.txt"))]

    @app.get("/")
    def index():
        return FileResponse(ROOT / "static" / "index.html")

    app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")
    return app


app = create_app()
