"""Application entry point."""
from app_factory import create_app

app = create_app(True,True)


if __name__ == "__main__":
    app.run(host='0.0.0.0',port=5002)