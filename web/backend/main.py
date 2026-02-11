import os
import importlib
flask = importlib.import_module("flask")
Flask = flask.Flask
from web.backend.api.v1 import bp as api_v1_bp
from core.schedule.scheduler import start as start_scheduler

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api_v1_bp)
    return app

app = create_app()

if __name__ == "__main__":
    try:
        start_scheduler()
    except Exception:
        pass
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
