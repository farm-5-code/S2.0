# Sports Prediction System v2.0.0

Production-oriented MVP for sports match analysis.

## Run

```bash
cp .env.example .env
pip install -r requirements-dev.txt
python run.py
```

## Test

```bash
pytest -q
python scripts/smoke_test.py
```

## Main endpoints
- `/health/live`
- `/health/ready`
- `/api/test`
- `/api/analyze`
- `/api/history`
- `/api/stats`
- `/api/engine-status`
- `/metrics`
