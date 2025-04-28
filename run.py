from app import create_app
import os
from datetime import datetime

app = create_app()

if __name__ == '__main__':
    # Get host and port from environment variables or use defaults
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5001))
    current_user = os.environ.get('CURRENT_USER', 'lilnurik')

    # Print access information
    print("*" * 80)
    print(f"Carwash Management API is running!")
    print(f"Current user: {current_user}")
    print(f"Current time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print(f"Internal URL: http://127.0.0.1:{port}/")
    print(f"Network URL:  http://<your-ip-address>:{port}/")
    print("*" * 80)

    # Use standard Flask run method - no socketio
    app.run(host=host, port=port, debug=True)