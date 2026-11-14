FROM node:24-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim-bookworm
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    LIFELINETWIN_DATABASE=/var/lib/lifelinetwin/lifelinetwin.sqlite3

COPY requirements-phase2-lock.txt requirements-phase4a.txt requirements-phase4b.txt ./
RUN pip install --no-cache-dir -r requirements-phase2-lock.txt -r requirements-phase4a.txt -r requirements-phase4b.txt

ARG INSTALL_FORECASTING=0
COPY requirements-migration.txt ./
RUN if [ "$INSTALL_FORECASTING" = "1" ]; then \
      apt-get update && apt-get install -y --no-install-recommends git && \
      pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements-migration.txt && \
      rm -rf /var/lib/apt/lists/*; \
    fi

COPY lifelinetwin_backend/ ./lifelinetwin_backend/
COPY lifelinetwin_geo/ ./lifelinetwin_geo/
COPY data/alabama/ ./data/alabama/
COPY data/houston/ ./data/houston/
COPY data/heidelberg/ ./data/heidelberg/
COPY --from=frontend /build/dist ./frontend/dist
RUN python -c "from lifelinetwin_backend.continuity import dataset; dataset('houston'); dataset('alabama')" \
    && python -c "from lifelinetwin_backend.config import Settings; from lifelinetwin_backend.schemas import GeographicRequest; from lifelinetwin_backend.services import Tools; Tools(Settings()).geographic(GeographicRequest())"
CMD ["sh", "-c", "exec python -m uvicorn lifelinetwin_backend.web:app --host 0.0.0.0 --port ${PORT:-8000}"]
