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
docker build -t ip-calculator-v4 .
docker run -d --name ipcalc-app -p 8086:8086 ip-calculator-v4
uv run python scripts/smoke_test.py http://127.0.0.1:8086
```

## Test
```
uv run pytest -q
```
