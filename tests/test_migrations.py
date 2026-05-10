import os
import subprocess
import sys


def test_alembic_upgrade_reaches_head(tmp_path):
    db_path = tmp_path / "migration-smoke.db"
    env = {
        **os.environ,
        "DATABASE_URL": f"sqlite:///{db_path}",
        "FLASK_APP": "app.py",
        "SOCKETIO_ASYNC_MODE": "threading",
    }

    result = subprocess.run(  # nosec B603
        [sys.executable, "-m", "flask", "db", "upgrade"],
        cwd=os.getcwd(),
        env=env,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stderr
    assert db_path.exists()
