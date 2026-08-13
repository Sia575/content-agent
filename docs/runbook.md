# Operations runbook

- Install the package after dependencies: `pip install -e .`.
- Run once: `python scripts/run_once.py`.
- Run the scheduler: `python -m hotspot_agent.main`.
- Configure `NEWSAPI_KEY` only if a NewsAPI account is available.
- Reports are written below `output/`; failures are logged to standard error and the scheduler continues to its next run.
