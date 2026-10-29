"""Contract checks for the Airflow-to-Spark writer-token handoff."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_broker_requests_send_the_supplied_credential_as_bearer_auth():
    """Broker calls must authenticate with the control token or run capability."""
    source = (ROOT / "dags" / "dag_factory.py").read_text(encoding="utf-8")

    assert '"Authorization": f"Bearer {credential}"' in source
    assert '"Authorization": f"******"' not in source
