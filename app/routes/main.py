from flask import Blueprint, render_template, redirect, url_for

# Create the main blueprint
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    from app.routes.statistics import get_statistics_summary

    # Get statistics summary
    stats = get_statistics_summary()

    return render_template('index.html', stats=stats)


@main_bp.route('/dashboard')
def dashboard():
    """Dashboard page."""
    return render_template('dashboard.html')


@main_bp.route('/socket-test')
def socket_test():
    """Test page for WebSocket functionality."""
    return render_template('socket_test.html')


# Add a simple status endpoint that shows current time and user
@main_bp.route('/status')
def status():
    """Simple status endpoint that shows the application is running."""
    from datetime import datetime
    import os

    current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    current_user = os.environ.get('CURRENT_USER', 'lilnurik')

    return render_template('status.html',
                           current_time=current_time,
                           current_user=current_user)