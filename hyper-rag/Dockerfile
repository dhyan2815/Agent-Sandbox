# Hyper-RAG in one image: the React app is built in a Node stage and served by FastAPI.
# Made for a Hugging Face Space (Docker SDK, CPU Basic), which runs as user 1000 and
# routes traffic to port 7860. Any Docker host works the same way.
#
#   docker build -t hyper-rag .
#   docker run -p 7860:7860 -e GROQ_API_KEY=... -e HYPER_RAG_PASSWORD=... hyper-rag
#
# Set secrets as environment variables (on a Space: Settings > Variables and secrets),
# never in config.yaml. Without HYPER_RAG_PASSWORD anyone with the URL can use the app.

FROM node:24-slim AS web
WORKDIR /web
COPY web/package.json web/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
RUN useradd --create-home --uid 1000 user
WORKDIR /app
COPY pyproject.toml README.md config.yaml ./
COPY src ./src
RUN pip install --no-cache-dir .
COPY packs ./packs
COPY --from=web /web/dist ./web/dist
# The data folder is the only thing written at run time. A Space's disk is wiped on
# restart; plan v2 phase 2 moves what matters to R2.
RUN mkdir -p data && chown -R user:user /app
USER user
ENV PORT=7860 HOME=/home/user
EXPOSE 7860
# --proxy-headers: the host's proxy says the browser used HTTPS, so the login cookie is
# marked Secure and wrong-password limits apply per visitor, not per proxy.
CMD ["sh", "-c", "exec uvicorn hyper_rag.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
