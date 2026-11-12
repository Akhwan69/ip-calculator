FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock .python-version ./
RUN pip install --no-cache-dir "fastapi[standard]" uvicorn

COPY main.py index.html ./

ENV PORT=8086
EXPOSE 8086
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
