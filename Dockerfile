FROM node:22-alpine AS frontend-builder

WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend .
RUN npm run build

FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir uv

COPY backend/requirements.txt /app/backend/requirements.txt
WORKDIR /app/backend
RUN uv pip install --system --no-cache -r requirements.txt

COPY backend /app/backend
COPY --from=frontend-builder /app/frontend/out /app/frontend/out

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
