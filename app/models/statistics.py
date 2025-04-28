from app import db
from datetime import datetime


class SessionStatistic(db.Model):
    __tablename__ = 'session_statistics'

    id = db.Column(db.Integer, primary_key=True)
    kiosk_id = db.Column(db.String(50), nullable=False, index=True)
    session_id = db.Column(db.String(50), nullable=False, unique=True, index=True)
    ended_at = db.Column(db.DateTime, nullable=False, index=True)
    duration_seconds = db.Column(db.Float, nullable=False)
    total_inserted = db.Column(db.Numeric(10, 2), nullable=False)
    final_balance = db.Column(db.Numeric(10, 2), nullable=False)
    total_consumed = db.Column(db.Numeric(10, 2), nullable=False)
    payment_details = db.Column(db.JSON, nullable=True)

    # Timestamps for internal tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SessionStatistic {self.session_id}>'