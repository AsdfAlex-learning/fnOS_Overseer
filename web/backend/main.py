import os
import importlib
from pathlib import Path

flask = importlib.import_module("flask")
Flask = flask.Flask
from web.backend.api.v1 import bp as api_v1_bp
from core.schedule.scheduler import start as start_scheduler

# Get the project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

def create_app():
    app = Flask(
        __name__,
        static_folder=str(PROJECT_ROOT / "web" / "static"),
        static_url_path="/static"
    )
    app.register_blueprint(api_v1_bp)

    # Add route to serve index.html at root
    @app.route("/")
    def index():
        return app.send_static_file("index.html")

    return app

app = create_app()

if __name__ == "__main__":
    try:
        start_scheduler()
    except Exception:
        pass
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port)
