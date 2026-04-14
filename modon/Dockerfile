# Stage 1: build React frontend
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY modon_react/package*.json ./
RUN npm ci
COPY modon_react/ .
ARG VITE_API_URL=/api
ENV VITE_API_URL=$VITE_API_URL
ARG VITE_GOOGLE_MAPS_API_KEY
ENV VITE_GOOGLE_MAPS_API_KEY=$VITE_GOOGLE_MAPS_API_KEY
RUN npm run build

# Stage 2: Python backend + serve static
FROM python:3.13-slim
WORKDIR /app

COPY modon/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY modon/api/ ./api/
COPY modon/src/ ./src/
COPY modon/data/*.csv ./data/

COPY --from=frontend /frontend/dist ./static/

ENV DATA_DIR=data
ENV STATIC_DIR=static
ENV CORS_ORIGINS=*

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
