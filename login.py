from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, Empresa

login_bp = Blueprint('login_bp', __name__)


def role_required(*roles):
    """Decorator to restrict access by role."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if current_user.role not in roles:
                flash('Acesso negado.', 'danger')
                return redirect(url_for('emp_bp.simulador'))
            return f(*args, **kwargs)
        return decorated
    return decorator


@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        if current_user.is_lider:
            return redirect(url_for('adm_bp.dashboard'))
        return redirect(url_for('emp_bp.simulador'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            if not user.ativo:
                flash('Conta desativada. Contate o administrador.', 'danger')
                return render_template('login.html')
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            if user.is_lider:
                return redirect(url_for('adm_bp.dashboard'))
            return redirect(url_for('emp_bp.simulador'))
        else:
            flash('Email ou senha incorretos.', 'danger')

    return render_template('login.html')


@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logout realizado com sucesso.', 'info')
    return redirect(url_for('login_bp.login'))


@login_bp.route('/cadastro', methods=['GET', 'POST'])
@login_required
def cadastro():
    if not current_user.is_lider:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('emp_bp.simulador'))

    empresas = Empresa.query.filter_by(ativo=True).all()

    if request.method == 'POST':
        nome = request.form.get('nome', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        role = request.form.get('role', 'corretor')
        empresa_id = request.form.get('empresa_id', type=int)

        # Lider can only create corretores in their own empresa
        if current_user.role == 'lider':
            role = 'corretor'
            empresa_id = current_user.empresa_id

        if not all([nome, email, password, empresa_id]):
            flash('Preencha todos os campos.', 'warning')
            return render_template('cadastro.html', empresas=empresas)

        if User.query.filter_by(email=email).first():
            flash('Email ja cadastrado.', 'danger')
            return render_template('cadastro.html', empresas=empresas)

        user = User(nome=nome, email=email, role=role, empresa_id=empresa_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        flash(f'Usuario {nome} cadastrado com sucesso!', 'success')
        return redirect(url_for('adm_bp.usuarios') if current_user.is_admin
                        else url_for('emp_bp.simulador'))

    return render_template('cadastro.html', empresas=empresas)


@login_bp.route('/recuperar', methods=['GET', 'POST'])
def recuperar():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if user:
            # Simple reset: generate temp password (in production, use email token)
            flash('Contate o administrador para redefinir sua senha.', 'info')
        else:
            flash('Email nao encontrado.', 'warning')

        return redirect(url_for('login_bp.login'))

    return render_template('recuperar.html')
