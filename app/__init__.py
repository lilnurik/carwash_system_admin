from flask import Flask, render_template
import os
import logging
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect  # Import only CSRFProtect class

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()  # Create an instance of CSRFProtect


def create_app():
    app = Flask(__name__)

    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-12345')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql://carwash_admin:admin123@localhost/carwash_admin')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)  # Now this will work correctly

    # Debug route
    @app.route('/debug')
    def debug():
        import sys
        import flask

        debug_info = [
            f"<h1>Debug Information</h1>",
            f"<p>Python version: {sys.version}</p>",
            f"<p>Flask version: {flask.__version__}</p>",
            f"<p>Current user: {os.environ.get('CURRENT_USER', 'not set')}</p>",
            f"<p>Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}</p>",
            f"<p>App name: {app.name}</p>",
            f"<p>Registered blueprints: {list(app.blueprints.keys())}</p>",
        ]

        return "".join(debug_info)

    # Context processor for templates
    @app.context_processor
    def inject_globals():
        return dict(
            datetime=datetime,
            os=os
        )

    # Register blueprints
    from app.routes.devices import device_bp, device_api_bp
    from app.routes.programs import program_bp, program_api_bp
    from app.routes.users import user_bp, user_api_bp
    from app.routes.statistics import statistics_bp, statistics_api_bp

    app.register_blueprint(device_bp, url_prefix='/devices')
    app.register_blueprint(device_api_bp, url_prefix='/api/devices')
    app.register_blueprint(program_bp, url_prefix='/programs')
    app.register_blueprint(program_api_bp, url_prefix='/api/programs')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(user_api_bp, url_prefix='/api/users')
    app.register_blueprint(statistics_bp, url_prefix='/statistics')
    app.register_blueprint(statistics_api_bp)

    # Home route
    @app.route('/')
    def home():
        try:
            # Import here to avoid circular imports
            from app.routes.statistics import get_statistics_summary
            stats = get_statistics_summary()
            return render_template('index.html', stats=stats)
        except Exception as e:
            return f"""
            <h1>Error rendering template</h1>
            <p>{str(e)}</p>
            <p>Try accessing <a href="/debug">/debug</a> for more information.</p>
            """

    return app