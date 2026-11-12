"""Serve the production frontend and API from the same origin."""

from pathlib import Path

from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.staticfiles import StaticFiles

from .main import app as api


class FrontendFiles(StaticFiles):
    async def get_response(self, path, scope):
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            accepts_html = any(
                key == b"accept" and b"text/html" in value
                for key, value in scope["headers"]
            )
            if exc.status_code != 404 or not accepts_html or Path(path).suffix:
                raise
            return await super().get_response("index.html", scope)


app = Starlette(lifespan=api.router.lifespan_context)
app.mount("/api", api)
app.mount("/", FrontendFiles(directory=Path(__file__).resolve().parents[1] / "frontend" / "dist", html=True))
