import sys, os

# Absolute path to this file's directory (foodai/app/)
_app_dir = os.path.dirname(os.path.abspath(__file__))
# Parent = foodai/ — where recipes.parquet, instructions.db, main.py, model.py etc. live
_parent = os.path.abspath(os.path.join(_app_dir, '..'))

# Add both directories to sys.path so all imports resolve
# _app_dir  → makes 'routes', 'services' importable
# _parent   → makes 'main', 'model', 'GenerateRecommendations' importable
for _p in (_app_dir, _parent):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# Change cwd to foodai/ so relative file paths work
os.chdir(_parent)

# ── Startup checks ────────────────────────────────────────────────────────────
for _f in ('recipes.parquet', 'instructions.db'):
    _fp = os.path.join(_parent, _f)
    if os.path.exists(_fp):
        print(f"[startup] {_f} present ({os.path.getsize(_fp)//1024//1024} MB)", flush=True)
    else:
        print(f"[startup] WARNING: {_f} not found — recipe features will not work", flush=True)

from flask import Flask
from flask_cors import CORS
from routes.diet import diet_bp
from routes.custom import custom_bp
from routes.analyzer import analyzer_bp
from routes.pages import pages_bp
from routes.auth import auth_bp

def create_app():
    _app_dir = os.path.join(_parent, 'app')
    app = Flask(__name__,
                static_folder=os.path.join(_app_dir, 'static'),
                template_folder=os.path.join(_app_dir, 'templates'))
    app.secret_key = 'nutrivision-demo-secret-key-2026'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

    CORS(app)

    # Pre-warm the recipe dataset in the master process (gunicorn --preload)
    # Workers fork from master and inherit this via copy-on-write — only ONE copy in RAM
    try:
        from main import get_dataset
        get_dataset()
        print("[startup] Recipe dataset loaded and ready.", flush=True)
    except Exception as _e:
        print(f"[startup] WARNING: Could not pre-load dataset: {_e}", flush=True)

    # Register blueprints
    app.register_blueprint(pages_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(diet_bp, url_prefix='/api/diet')
    app.register_blueprint(custom_bp, url_prefix='/api/custom')
    app.register_blueprint(analyzer_bp, url_prefix='/api/analyzer')

    return app

if __name__ == '__main__':
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', debug=False, port=port, use_reloader=False)
