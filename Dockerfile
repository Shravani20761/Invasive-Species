FROM node:22-alpine AS frontend

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend ./
ENV VITE_API_URL=
RUN npm run build

FROM python:3.12-slim

WORKDIR /srv
COPY backend/requirements.txt /srv/backend/requirements.txt
RUN pip install --no-cache-dir -r /srv/backend/requirements.txt
COPY backend /srv/backend
COPY ml /srv/ml
COPY --from=frontend /app/dist /srv/frontend/dist
WORKDIR /srv/backend
ENV PYTHONPATH=/srv/backend
ENV FRONTEND_DIST=/srv/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
