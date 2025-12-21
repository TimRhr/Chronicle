from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_babel import Babel

db = SQLAlchemy()
login_manager = LoginManager()
babel = Babel()

# Optional: Flask-Caching (requires: pip install Flask-Caching)
try:
    from flask_caching import Cache
    cache = Cache()
except ImportError:
    cache = None

# Optional: Flask-Limiter (requires: pip install Flask-Limiter)
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(key_func=get_remote_address, default_limits=["20000 per day", "5000 per hour"])
except ImportError:
    limiter = None
