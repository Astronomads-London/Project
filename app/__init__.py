import os
from pathlib import Path

from flask import Flask
from dotenv import load_dotenv

from app.routes.main import main_bp
from app.routes.api import api_bp
from app.routes.learn import learn_bp
from app.routes.policies import policies_bp

def create_app():
    load_dotenv(Path(__file__).resolve().parents[1] / ".env")
    app = Flask(__name__)
    app.config["INVITE_CODE"] = os.environ.get("INVITE_CODE")
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(learn_bp, url_prefix="/learn")
    app.register_blueprint(policies_bp, url_prefix="/policies")
    return app