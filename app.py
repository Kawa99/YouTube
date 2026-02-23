import os

from flask import Flask

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
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "default-dev-key")

    if Limiter is not None:
        limiter = Limiter(app=app, key_func=get_remote_address, default_limits=[])
    else:
        limiter = NoopLimiter()

    from routes import register_routes

    register_routes(app, limiter)
    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
