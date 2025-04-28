import random
import uuid

from flask import jsonify, request
from app import db
from datetime import datetime, timedelta
import json


# МОДЕЛИ (оставлены без изменений, кроме пары мелких улучшений):

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rfid_card_number = db.Column(db.String(50), unique=True, nullable=False)
    balance = db.Column(db.Float, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'rfid_card_number': self.rfid_card_number,
            'balance': self.balance,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Program(db.Model):
    __tablename__ = 'programs'
    id = db.Column(db.String(50), primary_key=True)  # Changed to String type
    name = db.Column(db.String(100), nullable=False)
    price_per_second = db.Column(db.Numeric(10, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'price_per_second': float(self.price_per_second),
            'is_active': self.is_active
        }

# Update the relationship table as well
device_programs = db.Table('device_programs',
    db.Column('device_id', db.Integer, db.ForeignKey('devices.id'), primary_key=True),
    db.Column('program_id', db.String(50), db.ForeignKey('programs.id'), primary_key=True)  # Changed to String(50)
)

class Device(db.Model):
    __tablename__ = 'devices'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(50), nullable=False)
    port = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    programs = db.relationship('Program', secondary=device_programs,
                                backref=db.backref('devices', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'ip_address': self.ip_address,
            'port': self.port,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'programs': [program.to_dict() for program in self.programs if program.is_active]
        }

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<SessionStatistic {self.session_id}>'

# ГЕНЕРАЦИЯ МОКОВ:
