import os
import shutil

import sentry_sdk
from flask import Flask
from flask_migrate import Migrate
from flask_socketio import SocketIO
from models import db
from sentry_sdk.integrations.flask import FlaskIntegration

migrate = Migrate()
socketio = None

if "SENTRY_DSN" in os.environ:
    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[FlaskIntegration()],
        traces_sample_rate=1.0,
    )

try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
except ModuleNotFoundError:
    Limiter = None

    def get_remote_address():  # noqa: D401
        return "127.0.0.1"


class NoopLimiter:
    """Fallback limiter used when Flask-Limiter is unavailable."""

    def limit(self, *_args, **_kwargs):
        def decorator(func):
            return func

        return decorator


def create_app():
    global socketio
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "default-dev-key")
    data_dir = os.path.join(app.root_path, "data")
    os.makedirs(data_dir, exist_ok=True)
    db_path = os.path.join(data_dir, "videos.db")
    legacy_db_path = os.path.join(app.root_path, "videos.db")
    if not os.path.exists(db_path) and os.path.exists(legacy_db_path):
        shutil.copy2(legacy_db_path, db_path)
    database_url = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url or f"sqlite:///{db_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db.init_app(app)
    migrate.init_app(app, db)

    if Limiter is not None:
        limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[])
    else:
        limiter = NoopLimiter()

    from routes import register_routes

    register_routes(app, limiter)
    socketio = SocketIO(
        app,
        message_queue=os.environ.get("REDIS_URL"),
        cors_allowed_origins="*",
    )

    return app


app = create_app()

if __name__ == "__main__":
    socketio.run(app, debug=True)
