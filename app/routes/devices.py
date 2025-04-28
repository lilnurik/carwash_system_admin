from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
import requests
import json  # Import the json module for pretty printing
import logging  # Import the logging module
from datetime import datetime  # Import datetime for timestamp
from app.models import Device, Program
from app import db

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('carwash')

# API Blueprint
device_api_bp = Blueprint('device_api', __name__)

# Web Blueprint
device_bp = Blueprint('devices', __name__)


# Helper function to log request data
def log_request_data(url, data, username="system"):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "=" * 80)
    print(f"REQUEST LOG - {timestamp} - User: {username}")
    print(f"Endpoint: {url}")
    print("Payload:")
    print(json.dumps(data, indent=2))
    print("=" * 80 + "\n")

    # Also log to the application logger
    logger.info(f"Request to {url} by {username} at {timestamp}")


# Helper function to log response data
def log_response_data(response, username="system"):
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    print("\n" + "+" * 80)
    print(f"RESPONSE LOG - {timestamp} - User: {username}")
    print(f"Status Code: {response.status_code}")
    print(f"URL: {response.url}")
    print("Headers:")
    for key, value in response.headers.items():
        print(f"  {key}: {value}")
    print("Response Body:")
    try:
        # Try to parse response as JSON
        response_json = response.json()
        print(json.dumps(response_json, indent=2))
    except:
        # If not JSON, print as text
        print(response.text)
    print("+" * 80 + "\n")

    # Also log to the application logger
    logger.info(f"Response from {response.url} - Status: {response.status_code}")


# API Routes
@device_api_bp.route('/', methods=['GET'])
def get_devices():
    devices = Device.query.all()
    return jsonify([device.to_dict() for device in devices])


@device_api_bp.route('/<int:id>', methods=['GET'])
def get_device(id):
    device = Device.query.get_or_404(id)
    return jsonify(device.to_dict())


@device_api_bp.route('/', methods=['POST'])
def create_device():
    data = request.json

    if not data or not data.get('name') or not data.get('ip_address') or not data.get('port'):
        return jsonify({'error': 'Missing required fields'}), 400

    device = Device(
        name=data['name'],
        ip_address=data['ip_address'],
        port=data['port'],
        is_active=data.get('is_active', True)
    )

    db.session.add(device)
    db.session.commit()

    # Add selected programs if provided
    if 'program_ids' in data and isinstance(data['program_ids'], list):
        for program_id in data['program_ids']:
            program = Program.query.get(program_id)
            if program:
                device.programs.append(program)

        db.session.commit()

    # Send request to device with programs
    try:
        endpoint = data.get('endpoint', 'central/register')
        url = f"http://{device.ip_address}:{device.port}/{endpoint}"

        # Prepare program data for sending - ONLY include programs
        program_data = {
            'programs': [program.to_dict() for program in device.programs]
        }

        # Log the request data
        username = request.headers.get('X-Username', 'api_user')
        log_request_data(url, program_data, username)

        response = requests.post(url, json=program_data, timeout=5)

        # Log the response
        log_response_data(response, username)
    except Exception as e:
        # Log the error
        print(f"Error communicating with device: {str(e)}")

    return jsonify(device.to_dict()), 201


@device_api_bp.route('/<int:id>', methods=['PUT'])
def update_device(id):
    device = Device.query.get_or_404(id)
    data = request.json

    if 'name' in data:
        device.name = data['name']
    if 'ip_address' in data:
        device.ip_address = data['ip_address']
    if 'port' in data:
        device.port = data['port']
    if 'is_active' in data:
        device.is_active = data['is_active']

    # Update programs if provided
    if 'program_ids' in data and isinstance(data['program_ids'], list):
        # Clear existing programs
        device.programs = []

        # Add selected programs
        for program_id in data['program_ids']:
            program = Program.query.get(program_id)
            if program:
                device.programs.append(program)

    db.session.commit()

    # If endpoint provided, send update request
    if 'endpoint' in data:
        try:
            endpoint = data.get('endpoint')
            url = f"http://{device.ip_address}:{device.port}/{endpoint}"

            # Prepare program data for sending - ONLY include programs
            program_data = {
                'programs': [program.to_dict() for program in device.programs]
            }

            # Log the request data
            username = request.headers.get('X-Username', 'api_user')
            log_request_data(url, program_data, username)

            response = requests.post(url, json=program_data, timeout=5)

            # Log the response
            log_response_data(response, username)
        except Exception as e:
            print(f"Error communicating with device: {str(e)}")

    return jsonify(device.to_dict())


@device_api_bp.route('/<int:id>', methods=['DELETE'])
def delete_device(id):
    device = Device.query.get_or_404(id)
    db.session.delete(device)
    db.session.commit()

    return jsonify({'message': 'Device deleted successfully'})


@device_api_bp.route('/<int:id>/deactivate', methods=['PUT'])
def deactivate_device(id):
    device = Device.query.get_or_404(id)
    device.is_active = False
    db.session.commit()

    return jsonify(device.to_dict())


# Web Routes
@device_bp.route('/')
def index():
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    program_id = request.args.get('program', '')

    # Build query
    query = Device.query

    # Apply filters
    if search:
        query = query.filter(Device.name.ilike(f'%{search}%') |
                             Device.ip_address.ilike(f'%{search}%'))

    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    if program_id:
        query = query.join(Device.programs).filter(Program.id == program_id)

    # Execute query
    devices = query.all()

    # Get all programs for filter dropdown
    all_programs = Program.query.all()

    return render_template('devices/index.html', devices=devices, all_programs=all_programs)


@device_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        ip_address = request.form.get('ip_address')
        port = request.form.get('port')
        endpoint = request.form.get('endpoint', 'central/register')

        device = Device(name=name, ip_address=ip_address, port=port)
        db.session.add(device)
        db.session.commit()

        # Handle selected programs
        selected_program_ids = request.form.getlist('program_ids')
        for program_id in selected_program_ids:
            program = Program.query.get(program_id)
            if program:
                device.programs.append(program)

        db.session.commit()

        # Send request to device with programs
        try:
            url = f"http://{device.ip_address}:{device.port}/{endpoint}"

            # Prepare program data for sending - ONLY include programs
            program_data = {
                'programs': [program.to_dict() for program in device.programs]
            }

            # Log the request data with the current user's information
            username = request.cookies.get('username', 'web_user')
            log_request_data(url, program_data, username)

            response = requests.post(url, json=program_data, timeout=5)

            # Log the response
            log_response_data(response, username)

            flash(f"Device registration sent. Response: {response.status_code}", 'info')
        except Exception as e:
            flash(f"Warning: Could not communicate with device: {str(e)}", 'warning')

        flash('Device created successfully', 'success')
        return redirect(url_for('devices.index'))

    # Get all available programs for selection
    programs = Program.query.filter_by(is_active=True).all()
    return render_template('devices/create.html', programs=programs)


@device_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    device = Device.query.get_or_404(id)

    if request.method == 'POST':
        device.name = request.form.get('name')
        device.ip_address = request.form.get('ip_address')
        device.port = request.form.get('port')
        device.is_active = 'is_active' in request.form
        endpoint = request.form.get('endpoint', 'central/register')  # Changed default to register

        # Update selected programs
        device.programs = []  # Clear existing associations
        selected_program_ids = request.form.getlist('program_ids')
        for program_id in selected_program_ids:
            program = Program.query.get(program_id)
            if program:
                device.programs.append(program)

        db.session.commit()

        # Send update to device if endpoint provided
        if endpoint:
            try:
                url = f"http://{device.ip_address}:{device.port}/{endpoint}"

                # Prepare program data for sending - ONLY include programs, not device info
                program_data = {
                    'programs': [program.to_dict() for program in device.programs]
                }

                # Log the request data
                username = request.cookies.get('username', 'web_user')
                log_request_data(url, program_data, username)

                # Use POST as requested
                response = requests.post(url, json=program_data, timeout=5)

                # Log the response
                log_response_data(response, username)

                flash(f"Device update sent. Response: {response.status_code}", 'info')
            except Exception as e:
                flash(f"Warning: Could not communicate with device: {str(e)}", 'warning')

        flash('Device updated successfully', 'success')
        return redirect(url_for('devices.index'))

    # Get all available programs for selection
    all_programs = Program.query.filter_by(is_active=True).all()
    return render_template('devices/edit.html', device=device, all_programs=all_programs)


@device_bp.route('/<int:id>/toggle-status', methods=['POST'])
def toggle_status(id):
    device = Device.query.get_or_404(id)
    device.is_active = not device.is_active
    db.session.commit()

    status = 'activated' if device.is_active else 'deactivated'
    flash(f'Device {status} successfully', 'success')
    return redirect(url_for('devices.index'))


@device_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    device = Device.query.get_or_404(id)
    db.session.delete(device)
    db.session.commit()

    flash('Device deleted successfully', 'success')
    return redirect(url_for('devices.index'))