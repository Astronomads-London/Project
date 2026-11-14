import os
from dotenv import load_dotenv
load_dotenv()
from app import create_app
app = create_app()

secret = os.environ.get("FLASK_SECRET")
if not secret:
    raise ValueError("FLASK_SECRET environment variable is not set")

app.secret_key = secret.encode()

if __name__ == "__main__":
    app.run(debug=True)