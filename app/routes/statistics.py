from flask import Blueprint, request, jsonify, render_template, current_app, app
# from app.models import SessionStatistic
from app import db
from datetime import datetime, timedelta
import logging
import os
import uuid
import random

from app.models import SessionStatistic


# Create blueprints
statistics_bp = Blueprint('statistics', __name__)
statistics_api_bp = Blueprint('statistics_api', __name__)


@statistics_api_bp.route('/api/sessions/statistics', methods=['POST'])
def receive_session_statistics():
    """
    Endpoint to receive session statistics from external system.
    """
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    current_user = os.environ.get('CURRENT_USER', 'system')
    client_ip = request.remote_addr

    try:
        data = request.json

        # Validate required fields
        required_fields = ['kiosk_id', 'session_id', 'ended_at', 'duration_seconds',
                           'total_inserted', 'final_balance', 'total_consumed']

        for field in required_fields:
            if field not in data:
                return jsonify({
                    'status': 'error',
                    'message': f'Missing required field: {field}'
                }), 400

        # Parse the datetime
        try:
            if isinstance(data['ended_at'], str):
                # Try to parse ISO format
                ended_at = datetime.fromisoformat(data['ended_at'].replace('Z', '+00:00'))
            else:
                # Assume it's a timestamp
                ended_at = datetime.fromtimestamp(data['ended_at'])
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Invalid date format for ended_at: {e}'
            }), 400

        # Check if session already exists
        existing_session = SessionStatistic.query.filter_by(session_id=data['session_id']).first()
        if existing_session:
            return jsonify({
                'status': 'error',
                'message': f'Session with ID {data["session_id"]} already exists'
            }), 409  # Conflict

        # Create new session statistic record
        session_stat = SessionStatistic(
            kiosk_id=data['kiosk_id'],
            session_id=data['session_id'],
            ended_at=ended_at,
            duration_seconds=float(data['duration_seconds']),
            total_inserted=data['total_inserted'],
            final_balance=data['final_balance'],
            total_consumed=data['total_consumed'],
            payment_details=data.get('payment_details', {})
        )

        db.session.add(session_stat)
        db.session.commit()

        # Log the transaction
        print("\n" + "=" * 80)
        print(f"SESSION STATISTICS RECEIVED - {timestamp} - User: {current_user}")
        print(f"Kiosk ID: {data['kiosk_id']}")
        print(f"Session ID: {data['session_id']}")
        print(f"Ended At: {ended_at}")
        print(f"Duration: {data['duration_seconds']} seconds")
        print(f"Total Inserted: {data['total_inserted']}")
        print(f"Total Consumed: {data['total_consumed']}")
        print(f"Final Balance: {data['final_balance']}")
        print(f"Client IP: {client_ip}")
        print("=" * 80 + "\n")

        return jsonify({
            'status': 'success',
            'message': 'Session statistics received successfully',
            'session_id': data['session_id']
        })

    except Exception as e:
        # Log the error
        logger = logging.getLogger('carwash')
        logger.error(f"Error processing session statistics: {str(e)}")

        # Rollback in case of error
        db.session.rollback()

        return jsonify({
            'status': 'error',
            'message': f'An error occurred: {str(e)}'
        }), 500


@statistics_bp.route('/')
def index():
    """Show statistics dashboard"""
    # Get unique kiosk IDs for filter dropdown
    kiosks = db.session.query(SessionStatistic.kiosk_id).distinct().all()
    kiosk_ids = [k[0] for k in kiosks]

    return render_template('statistics/index.html', kiosk_ids=kiosk_ids)


@statistics_bp.route('/data')
def get_statistics_data():
    """API endpoint to get statistics data with filtering"""
    # Get filter parameters
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    kiosk_id = request.args.get('kiosk_id')
    period = request.args.get('period', 'daily')  # daily, weekly, monthly

    # Build query
    query = SessionStatistic.query

    # Apply filters
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(SessionStatistic.ended_at >= start_date)
        except ValueError:
            pass

    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d')
            # Add one day to include the entire end date
            end_date = end_date.replace(hour=23, minute=59, second=59)
            query = query.filter(SessionStatistic.ended_at <= end_date)
        except ValueError:
            pass

    if kiosk_id:
        query = query.filter(SessionStatistic.kiosk_id == kiosk_id)

    # Get raw data
    sessions = query.order_by(SessionStatistic.ended_at.desc()).all()

    # Process data based on period
    if period == 'daily':
        # Group by day
        result = _group_by_date(sessions, '%Y-%m-%d')
    elif period == 'weekly':
        # Group by ISO week
        result = _group_by_date(sessions, '%Y-%W')
    elif period == 'monthly':
        # Group by month
        result = _group_by_date(sessions, '%Y-%m')
    else:
        # No grouping
        result = {
            'labels': [],
            'total_inserted': [],
            'total_consumed': [],
            'avg_duration': []
        }

    # Get unique kiosk IDs for the filter dropdown
    kiosks = db.session.query(SessionStatistic.kiosk_id).distinct().all()
    kiosk_ids = [k[0] for k in kiosks]

    # Return data for chart
    return jsonify({
        'status': 'success',
        'data': result,
        'kiosks': kiosk_ids,
        'raw_sessions': [_format_session(s) for s in sessions[:100]]  # Limit to 100 sessions for table view
    })


@statistics_bp.route('/session/<session_id>')
def session_detail(session_id):
    """Show details for a specific session"""
    session = SessionStatistic.query.filter_by(session_id=session_id).first_or_404()

    return render_template('statistics/session_detail.html', session=session)


def _format_session(session):
    """Format a session for JSON response"""
    return {
        'id': session.id,
        'kiosk_id': session.kiosk_id,
        'session_id': session.session_id,
        'ended_at': session.ended_at.strftime('%Y-%m-%d %H:%M:%S'),
        'duration_seconds': round(session.duration_seconds, 2),
        'duration_formatted': _format_duration(session.duration_seconds),
        'total_inserted': float(session.total_inserted),
        'final_balance': float(session.final_balance),
        'total_consumed': float(session.total_consumed),
        'payment_details': session.payment_details
    }


def _format_duration(seconds):
    """Format duration in seconds to human-readable format"""
    minutes, seconds = divmod(int(seconds), 60)
    hours, minutes = divmod(minutes, 60)

    if hours > 0:
        return f"{hours}h {minutes}m {seconds}s"
    elif minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"{seconds}s"


def _group_by_date(sessions, date_format):
    """Group sessions by date format and calculate statistics"""
    grouped_data = {}

    for session in sessions:
        date_key = session.ended_at.strftime(date_format)

        if date_key not in grouped_data:
            grouped_data[date_key] = {
                'count': 0,
                'total_inserted': 0,
                'total_consumed': 0,
                'total_duration': 0
            }

        group = grouped_data[date_key]
        group['count'] += 1
        group['total_inserted'] += float(session.total_inserted)
        group['total_consumed'] += float(session.total_consumed)
        group['total_duration'] += session.duration_seconds

    # Sort dates
    sorted_keys = sorted(grouped_data.keys())

    result = {
        'labels': sorted_keys,
        'total_inserted': [grouped_data[k]['total_inserted'] for k in sorted_keys],
        'total_consumed': [grouped_data[k]['total_consumed'] for k in sorted_keys],
        'avg_duration': [
            grouped_data[k]['total_duration'] / grouped_data[k]['count'] if grouped_data[k]['count'] > 0 else 0 for k in
            sorted_keys],
        'session_count': [grouped_data[k]['count'] for k in sorted_keys]
    }

    return result


def get_statistics_summary():
    """Get summary statistics for display on the homepage"""
    try:
        # Total sessions count
        total_sessions = SessionStatistic.query.count()

        # Total revenue (sum of consumed amounts)
        result = db.session.query(db.func.sum(SessionStatistic.total_consumed)).first()
        total_revenue = float(result[0]) if result[0] else 0

        # Average session duration
        result = db.session.query(db.func.avg(SessionStatistic.duration_seconds)).first()
        avg_duration = float(result[0]) if result[0] else 0

        # Sessions in the last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_sessions = SessionStatistic.query.filter(SessionStatistic.ended_at >= yesterday).count()

        return {
            'total_sessions': total_sessions,
            'total_revenue': total_revenue,
            'avg_duration': avg_duration,
            'recent_sessions': recent_sessions
        }
    except Exception as e:
        print(f"Error getting statistics summary: {str(e)}")
        return {
            'total_sessions': 0,
            'total_revenue': 0,
            'avg_duration': 0,
            'recent_sessions': 0
        }


@statistics_api_bp.route('/api/generate-mock-data', methods=['GET'])
def generate_mock_data():
    """Generate mock statistics data for testing (DEVELOPMENT ONLY)"""
    if app.config['ENV'] != 'development':
        return jsonify({
            'status': 'error',
            'message': 'This endpoint is only available in development mode'
        }), 403

    try:
        count = int(request.args.get('count', 50))
        days_back = int(request.args.get('days', 30))

        base_time = datetime.utcnow() - timedelta(days=days_back)
        kiosk_ids = ['K001', 'K002', 'K003', 'K004']

        for _ in range(count):
            time_offset = timedelta(
                days=random.randint(0, days_back),
                hours=random.randint(0, 23),
                minutes=random.randint(0, 59)
            )
            session_time = base_time + time_offset

            duration = random.uniform(60, 900)
            inserted = round(random.uniform(5, 50), 2)
            final_balance = round(random.uniform(0, inserted * 0.3), 2)
            consumed = round(inserted - final_balance, 2)

            payment_details = []
            if inserted > 0:
                payment_types = ['cash', 'card', 'mobile']
                payment_details.append({
                    'type': random.choice(payment_types),
                    'amount': inserted,
                    'timestamp': session_time.isoformat(),
                    'status': 'success'
                })

            session_stat = SessionStatistic(
                kiosk_id=random.choice(kiosk_ids),
                session_id=f"MOCK-{uuid.uuid4()}",
                ended_at=session_time,
                duration_seconds=duration,
                total_inserted=str(inserted),
                final_balance=str(final_balance),
                total_consumed=str(consumed),
                payment_details=payment_details
            )

            db.session.add(session_stat)

        db.session.commit()

        return jsonify({
            'status': 'success',
            'message': f'Generated {count} mock session records'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
