from flask import Blueprint, render_template
import datetime
import os

test_bp = Blueprint('test', __name__)

@test_bp.route('/test')
def test_page():
    return render_template('test.html', datetime=datetime, os=os)