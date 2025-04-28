from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from app.models import Program
from app import db
from app.forms import ProgramForm

# API Blueprint
program_api_bp = Blueprint('program_api', __name__)

# Web Blueprint
program_bp = Blueprint('programs', __name__)


# API Routes
@program_api_bp.route('/', methods=['GET'])
def get_programs():
    programs = Program.query.all()
    return jsonify([program.to_dict() for program in programs])


@program_api_bp.route('/<program_id>', methods=['GET'])
def get_program(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    return jsonify(program.to_dict())


@program_api_bp.route('/', methods=['POST'])
def create_program():
    data = request.json

    if not data or not data.get('name') or 'price_per_second' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # Generate a program ID if not provided
    program_id = data.get('id')
    if not program_id:
        # Create a slug from the name or use a default prefix with a random suffix
        from slugify import slugify
        import uuid
        program_id = slugify(data['name'], separator='_').upper() or f"PROGRAM_{uuid.uuid4().hex[:8].upper()}"

    program = Program(
        id=program_id,  # Use the string ID
        name=data['name'],
        price_per_second=float(data['price_per_second']),
        is_active=data.get('is_active', True)
    )

    db.session.add(program)
    db.session.commit()

    return jsonify(program.to_dict()), 201


@program_api_bp.route('/<program_id>', methods=['PUT'])
def update_program(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    data = request.json

    if 'name' in data:
        program.name = data['name']
    if 'price_per_second' in data:
        program.price_per_second = float(data['price_per_second'])
    if 'is_active' in data:
        program.is_active = data['is_active']

    db.session.commit()

    return jsonify(program.to_dict())


@program_api_bp.route('/<program_id>', methods=['DELETE'])
def delete_program(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    db.session.delete(program)
    db.session.commit()

    return jsonify({'message': 'Program deleted successfully'})


@program_api_bp.route('/<program_id>/deactivate', methods=['PUT'])
def deactivate_program(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    program.is_active = False
    db.session.commit()

    return jsonify(program.to_dict())


# Web Routes
@program_bp.route('/')
def index():
    # Get search and filter parameters
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    price = request.args.get('price', '')

    # Build query
    query = Program.query

    # Apply filters
    if search:
        query = query.filter(Program.name.ilike(f'%{search}%'))

    if status == 'active':
        query = query.filter_by(is_active=True)
    elif status == 'inactive':
        query = query.filter_by(is_active=False)

    # Apply sorting
    if price == 'low':
        query = query.order_by(Program.price_per_second.asc())
    elif price == 'high':
        query = query.order_by(Program.price_per_second.desc())
    else:
        query = query.order_by(Program.id.asc())  # Default sorting

    # Execute query
    programs = query.all()

    return render_template('programs/index.html', programs=programs)


@program_bp.route('/create', methods=['GET', 'POST'])
def create():
    form = ProgramForm()
    if form.validate_on_submit():
        program = Program(
            id=form.id.data,
            name=form.name.data,
            price_per_second=form.price_per_second.data,
            is_active=form.is_active.data
        )
        db.session.add(program)
        try:
            db.session.commit()
            flash('Program created successfully', 'success')
            return redirect(url_for('programs.index'))
        except Exception as e:
            db.session.rollback()
            flash(f'Error creating program: {str(e)}', 'danger')

    return render_template('programs/create.html', form=form)


@program_bp.route('/<program_id>/edit', methods=['GET', 'POST'])
def edit(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)

    if request.method == 'POST':
        program.name = request.form.get('name')
        program.price_per_second = float(request.form.get('price_per_second'))
        program.is_active = 'is_active' in request.form

        db.session.commit()
        flash('Program updated successfully', 'success')
        return redirect(url_for('programs.index'))

    return render_template('programs/edit.html', program=program)


@program_bp.route('/<program_id>/toggle-status', methods=['POST'])
def toggle_status(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    program.is_active = not program.is_active
    db.session.commit()

    status = 'activated' if program.is_active else 'deactivated'
    flash(f'Program {status} successfully', 'success')
    return redirect(url_for('programs.index'))


@program_bp.route('/<program_id>/delete', methods=['POST'])
def delete(program_id):  # Changed from int:id
    program = Program.query.get_or_404(program_id)
    db.session.delete(program)
    db.session.commit()

    flash('Program deleted successfully', 'success')
    return redirect(url_for('programs.index'))