import os

from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app.models import User
from app import db
import logging
from datetime import datetime
import json
from app.socket_io import broadcast_balance_update


# API Blueprint
user_api_bp = Blueprint('user_api', __name__)

# Web Blueprint
user_bp = Blueprint('users', __name__)


# API Routes
@user_api_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@user_api_bp.route('/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_dict())


@user_api_bp.route('/', methods=['POST'])
def create_user():
    data = request.json

    if not data or not data.get('name') or not data.get('rfid_card_number'):
        return jsonify({'error': 'Missing required fields'}), 400

    user = User(
        name=data['name'],
        rfid_card_number=data['rfid_card_number'],
        balance=data.get('balance', 0),
        is_active=data.get('is_active', True)
    )

    db.session.add(user)
    db.session.commit()

    return jsonify(user.to_dict()), 201


@user_api_bp.route('/<int:id>', methods=['PUT'])
def update_user(id):
    user = User.query.get_or_404(id)
    data = request.json

    if 'name' in data:
        user.name = data['name']
    if 'rfid_card_number' in data:
        user.rfid_card_number = data['rfid_card_number']
    if 'balance' in data:
        user.balance = data['balance']
    if 'is_active' in data:
        user.is_active = data['is_active']

    db.session.commit()

    return jsonify(user.to_dict())


@user_api_bp.route('/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()

    return jsonify({'message': 'User deleted successfully'})


@user_api_bp.route('/<int:id>/topup', methods=['POST'])
def topup_balance(id):
    user = User.query.get_or_404(id)
    data = request.json

    if not data or 'amount' not in data:
        return jsonify({'error': 'Amount is required'}), 400

    amount = float(data['amount'])
    if amount <= 0:
        return jsonify({'error': 'Amount must be positive'}), 400

    user.balance += amount
    db.session.commit()

    return jsonify(user.to_dict())


@user_api_bp.route('/<int:id>/deactivate', methods=['PUT'])
def deactivate_user(id):
    user = User.query.get_or_404(id)
    user.is_active = False
    db.session.commit()

    return jsonify(user.to_dict())


# Web Routes
@user_bp.route('/')
def index():
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    balance = request.args.get('balance', '')

    # Build query
    query = User.query

    # Apply filters
    if search:
        query = query.filter(User.name.ilike(f'%{search}%') |
                             User.rfid_card_number.ilike(f'%{search}%'))

    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    if balance == 'positive':
        query = query.filter(User.balance > 0)
    elif balance == 'zero':
        query = query.filter(User.balance == 0)

    # Execute query
    users = query.all()

    return render_template('users/index.html', users=users)


@user_bp.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        name = request.form.get('name')
        rfid_card_number = request.form.get('rfid_card_number')
        balance = float(request.form.get('balance', 0))

        user = User(name=name, rfid_card_number=rfid_card_number, balance=balance)
        db.session.add(user)
        db.session.commit()

        flash('User created successfully', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/create.html')


@user_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
def edit(id):
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        user.name = request.form.get('name')
        user.rfid_card_number = request.form.get('rfid_card_number')
        user.balance = float(request.form.get('balance'))
        user.is_active = 'is_active' in request.form

        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('users.index'))

    return render_template('users/edit.html', user=user)


@user_bp.route('/<int:id>/topup', methods=['GET', 'POST'])
def topup(id):
    user = User.query.get_or_404(id)

    if request.method == 'POST':
        amount = float(request.form.get('amount', 0))
        if amount > 0:
            user.balance += amount
            db.session.commit()
            flash(f'Balance topped up successfully by {amount}', 'success')
            return redirect(url_for('users.index'))
        else:
            flash('Amount must be positive', 'danger')

    return render_template('users/topup.html', user=user)


@user_bp.route('/<int:id>/toggle-status', methods=['POST'])
def toggle_status(id):
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()

    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {status} successfully', 'success')
    return redirect(url_for('users.index'))


@user_bp.route('/<int:id>/delete', methods=['POST'])
def delete(id):
    user = User.query.get_or_404(id)
    db.session.delete(user)
    db.session.commit()

    flash('User deleted successfully', 'success')
    return redirect(url_for('users.index'))


# Add this new endpoint to the existing file, with the other API routes
@user_api_bp.route('/by-rfid/<rfid_card_number>', methods=['GET'])
def get_user_by_rfid(rfid_card_number):
    """
    Get user information by RFID card number.

    This endpoint allows external systems to verify user credentials
    and check their balance by providing the RFID card number.
    """
    # Find user with the given RFID card number
    user = User.query.filter_by(rfid_card_number=rfid_card_number).first()

    # If no user is found, return 404
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found',
            'rfid_card_number': rfid_card_number
        }), 404

    # If user is not active, return 403
    if not user.is_active:
        return jsonify({
            'status': 'error',
            'message': 'User is inactive',
            'rfid_card_number': rfid_card_number
        }), 403

    # Log the access
    logger = logging.getLogger('carwash')
    client_ip = request.remote_addr
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"RFID Lookup - Card: {rfid_card_number} - User: {user.name} - IP: {client_ip} - Time: {timestamp}")

    # Return user data
    return jsonify({
        'status': 'success',
        'user': {
            'id': user.id,
            'name': user.name,
            'rfid_card_number': user.rfid_card_number,
            'balance': user.balance,
            'is_active': user.is_active
        }
    })


# Add an endpoint for deducting user balance
@user_api_bp.route('/deduct-balance', methods=['POST'])
def deduct_user_balance():
    """
    Deduct balance from a user's account.

    Required JSON payload:
    {
        "rfid_card_number": "12345",
        "amount": 10.5,
        "device_id": 1,
        "program_id": 2,
        "seconds_used": 30
    }
    """
    data = request.json

    # Validate required fields
    if not data or 'rfid_card_number' not in data or 'amount' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields'
        }), 400

    # Get values from request
    rfid_card_number = data['rfid_card_number']
    amount = float(data['amount'])
    device_id = data.get('device_id')
    program_id = data.get('program_id')
    seconds_used = data.get('seconds_used', 0)

    # Find user by RFID card number
    user = User.query.filter_by(rfid_card_number=rfid_card_number).first()

    # If no user found, return error
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found',
            'rfid_card_number': rfid_card_number
        }), 404

    # If user is not active, return error
    if not user.is_active:
        return jsonify({
            'status': 'error',
            'message': 'User is inactive',
            'rfid_card_number': rfid_card_number
        }), 403

    # Check if user has enough balance
    if user.balance < amount:
        return jsonify({
            'status': 'error',
            'message': 'Insufficient balance',
            'balance': user.balance,
            'required': amount
        }), 402  # 402 Payment Required

    # Deduct the balance
    user.balance -= amount
    db.session.commit()

    # Log the transaction
    logger = logging.getLogger('carwash')
    client_ip = request.remote_addr
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    transaction_details = {
        'user_id': user.id,
        'user_name': user.name,
        'rfid_card_number': rfid_card_number,
        'amount': amount,
        'new_balance': user.balance,
        'device_id': device_id,
        'program_id': program_id,
        'seconds_used': seconds_used,
        'client_ip': client_ip,
        'timestamp': timestamp
    }

    logger.info(f"Balance Deduction: {json.dumps(transaction_details)}")

    # Return success and updated user data
    return jsonify({
        'status': 'success',
        'message': 'Balance deducted successfully',
        'transaction': {
            'amount': amount,
            'device_id': device_id,
            'program_id': program_id,
            'seconds_used': seconds_used,
            'timestamp': timestamp
        },
        'user': {
            'id': user.id,
            'name': user.name,
            'rfid_card_number': user.rfid_card_number,
            'previous_balance': user.balance + amount,
            'new_balance': user.balance
        }
    })


@user_api_bp.route('/update-balance', methods=['POST'])
def update_user_balance():
    """
    Update a user's balance to a new value provided by the external system.

    Simplified JSON payload:
    {
        "rfid_card_number": "12345",
        "new_balance": 89.5
    }
    """
    # Get current timestamp for logging
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    client_ip = request.remote_addr
    current_user = os.environ.get('CURRENT_USER', 'system')

    # Get data from request
    data = request.json

    # Validate required fields
    if not data or 'rfid_card_number' not in data or 'new_balance' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required fields',
            'timestamp': timestamp
        }), 400

    # Get values from request - only the two essential fields
    rfid_card_number = data['rfid_card_number']
    new_balance = float(data['new_balance'])

    # Find user by RFID card number
    user = User.query.filter_by(rfid_card_number=rfid_card_number).first()

    # If no user found, return error
    if not user:
        return jsonify({
            'status': 'error',
            'message': 'User not found',
            'rfid_card_number': rfid_card_number,
            'timestamp': timestamp
        }), 404

    # If user is not active, return error
    if not user.is_active:
        return jsonify({
            'status': 'error',
            'message': 'User is inactive',
            'rfid_card_number': rfid_card_number,
            'timestamp': timestamp
        }), 403

    # Store previous balance for reporting
    previous_balance = user.balance

    # Make sure the new balance is not negative
    if new_balance < 0:
        return jsonify({
            'status': 'error',
            'message': 'New balance cannot be negative',
            'requested_balance': new_balance,
            'current_balance': user.balance,
            'timestamp': timestamp
        }), 400

    # Update user's balance
    user.balance = new_balance
    db.session.commit()

    # If broadcast_balance_update function exists, call it here
    try:
        # Only call this if the function is defined
        if 'broadcast_balance_update' in globals():
            broadcast_balance_update(user.id, rfid_card_number, new_balance)
    except Exception as e:
        # Log the error but don't fail the request
        print(f"Error broadcasting balance update: {str(e)}")

    # Log the transaction with minimal information
    logger = logging.getLogger('carwash')
    logger.info(f"Balance Update: Card {rfid_card_number}, Previous: {previous_balance}, New: {new_balance}")

    # Print transaction details to console in a simple format
    print("\n" + "=" * 80)
    print(f"BALANCE UPDATE - {timestamp} - User: {current_user}")
    print(f"RFID Card: {rfid_card_number} ({user.name})")
    print(f"Previous Balance: {previous_balance}")
    print(f"New Balance: {new_balance}")
    print(f"Client IP: {client_ip}")
    print("=" * 80 + "\n")

    # Return success and minimal user data
    return jsonify({
        'status': 'success',
        'message': 'Balance updated successfully',
        'user': {
            'rfid_card_number': user.rfid_card_number,
            'previous_balance': previous_balance,
            'new_balance': new_balance
        }
    })




