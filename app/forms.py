from flask_wtf import FlaskForm
from wtforms import StringField, FloatField, BooleanField
from wtforms.validators import DataRequired, Length, ValidationError
from app.models import Program


class ProgramForm(FlaskForm):
    id = StringField('Program ID', validators=[
        DataRequired(),
        Length(max=50, message='ID cannot be longer than 50 characters')
    ])
    name = StringField('Program Name', validators=[DataRequired()])
    price_per_second = FloatField('Price per Second', validators=[DataRequired()])
    is_active = BooleanField('Active', default=True)

    def validate_id(self, field):
        # Check if this ID exists but only for a different program (for new records)
        program = Program.query.filter_by(id=field.data).first()
        if program and getattr(self, '_obj', None) != program:
            raise ValidationError('A program with this ID already exists.')