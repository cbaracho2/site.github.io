import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from models import db, User

login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'simulador-markov-secret-key-2026'
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'instance', 'simulador.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login_bp.login'
    login_manager.login_message = 'Faca login para acessar o sistema.'
    login_manager.login_message_category = 'warning'

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from login import login_bp
    from adm import adm_bp
    from empreendimentos import emp_bp, api_bp

    app.register_blueprint(login_bp)
    app.register_blueprint(adm_bp, url_prefix='/admin')
    app.register_blueprint(emp_bp, url_prefix='/simulador')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.route('/')
    def index():
        return redirect(url_for('login_bp.login'))

    @app.context_processor
    def utility_processor():
        def format_brl(value):
            if value is None:
                return 'R$ 0,00'
            formatted = f'{value:,.2f}'
            formatted = formatted.replace(',', 'X').replace('.', ',').replace('X', '.')
            return f'R$ {formatted}'

        def format_pct(value):
            if value is None:
                return '0,00%'
            return f'{value:,.2f}%'.replace('.', ',')

        return dict(format_brl=format_brl, format_pct=format_pct)

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
