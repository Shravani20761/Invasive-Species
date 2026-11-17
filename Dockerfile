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
ENV HF_HOME=/opt/hf
ENV HF_HUB_CACHE=/opt/hf/hub
ENV INFERENCE_MODE=bioclip
RUN pip install --no-cache-dir -r /srv/backend/requirements.txt \
    && pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir open_clip_torch \
    && python -c "import open_clip; open_clip.create_model_from_pretrained('hf-hub:imageomics/bioclip'); open_clip.get_tokenizer('hf-hub:imageomics/bioclip')"
COPY backend /srv/backend
COPY ml /srv/ml
COPY --from=frontend /app/dist /srv/frontend/dist
WORKDIR /srv/backend
ENV PYTHONPATH=/srv/backend
ENV FRONTEND_DIST=/srv/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
