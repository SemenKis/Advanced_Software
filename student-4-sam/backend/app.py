from flask import Flask
from flask_cors import CORS

from database import init_database
from transportation import transportation
from htmx_routes import htmx_transportation


def create_app(seed=True):
    app = Flask(__name__)

    CORS(
        app,
        origins=[
            "http://localhost:3004"
        ]
    )

    app.register_blueprint(
        transportation
    )

    app.register_blueprint(
        htmx_transportation
    )

    init_database(
        seed=seed
    )

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "service": "transportation-backend"
        }

    return app


app = create_app()


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5004,
        debug=False
    )