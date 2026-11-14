# IP Calculator v4

Kalkulator subnet IPv4 (gaya ipcalc) dengan mode Subnet dan VLSM.

## Menjalankan lokal
```
uv sync --dev
uv run fastapi dev main.py
```
Buka http://127.0.0.1:8000

## CLI
```
uv run python main.py 192.168.0.1/24
```

## Docker
```
docker compose up -d --build
uv run python scripts/smoke_test.py http://127.0.0.1:8086
```

Mode pengembangan (hot-reload): folder project di-mount ke container, jadi
perubahan `main.py` atau `index.html` langsung terlihat setelah refresh
browser tanpa perlu `docker compose up --build` ulang. Rebuild hanya perlu
bila `Dockerfile`, `pyproject.toml`, atau `uv.lock` berubah:
```
docker compose up -d --build
```

Mode image statis (tanpa mount):
```
docker build -t ip-calculator-v4 .
docker run -d --name ipcalc-app -p 8086:8086 ip-calculator-v4
uv run python scripts/smoke_test.py http://127.0.0.1:8086
```
```

## Test
```
uv run pytest -q
```
