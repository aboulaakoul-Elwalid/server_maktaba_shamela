# filepath: /home/yourusername/mysite/wsgi.py
from main import app

if __name__ == "__main__":
    import os
    from waitress import serve
    serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))