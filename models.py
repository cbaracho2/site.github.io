from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import random
import string

db = SQLAlchemy()


def gerar_codigo():
    ts = datetime.utcnow().strftime('%y%m%d%H%M')
    rand = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f'SIM-{ts}-{rand}'


class Empresa(db.Model):
    __tablename__ = 'empresas'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), unique=True)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    usuarios = db.relationship('User', back_populates='empresa', lazy='dynamic')
    empreendimentos = db.relationship('Empreendimento', back_populates='empresa', lazy='dynamic')

    def __repr__(self):
        return f'<Empresa {self.nome}>'


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='corretor')
    ativo = db.Column(db.Boolean, default=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship('Empresa', back_populates='usuarios')
    simulacoes = db.relationship('Simulacao', foreign_keys='Simulacao.corretor_id',
                                 back_populates='corretor', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'adm'

    @property
    def is_lider(self):
        return self.role in ('lider', 'adm')

    @property
    def is_corretor(self):
        return True

    def __repr__(self):
        return f'<User {self.email} [{self.role}]>'


class Empreendimento(db.Model):
    __tablename__ = 'empreendimentos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300))
    empresa_id = db.Column(db.Integer, db.ForeignKey('empresas.id'), nullable=False)
    taxa_desconto_mensal = db.Column(db.Float, nullable=False, default=0.01)
    ativo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    empresa = db.relationship('Empresa', back_populates='empreendimentos')
    blocos = db.relationship('Bloco', back_populates='empreendimento', cascade='all, delete-orphan')
    plano_padrao = db.relationship('PlanoPadrao', back_populates='empreendimento',
                                   uselist=False, cascade='all, delete-orphan')
    regras = db.relationship('RegrasEmpreendimento', back_populates='empreendimento',
                              uselist=False, cascade='all, delete-orphan')
    simulacoes = db.relationship('Simulacao', back_populates='empreendimento', lazy='dynamic')

    def __repr__(self):
        return f'<Empreendimento {self.nome}>'


class Bloco(db.Model):
    __tablename__ = 'blocos'
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    empreendimento_id = db.Column(db.Integer, db.ForeignKey('empreendimentos.id'), nullable=False)

    empreendimento = db.relationship('Empreendimento', back_populates='blocos')
    unidades = db.relationship('Unidade', back_populates='bloco', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Bloco {self.nome}>'


class Unidade(db.Model):
    __tablename__ = 'unidades'
    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), nullable=False)
    bloco_id = db.Column(db.Integer, db.ForeignKey('blocos.id'), nullable=False)
    descricao = db.Column(db.String(200))
    area_coberta = db.Column(db.Float, nullable=False, default=0.0)
    area_descoberta = db.Column(db.Float, nullable=False, default=0.0)
    preco_m2 = db.Column(db.Float, nullable=False, default=0.0)
    coef_area_descoberta = db.Column(db.Float, nullable=False, default=0.5)
    status = db.Column(db.String(20), default='disponivel')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bloco = db.relationship('Bloco', back_populates='unidades')

    @property
    def valor_total(self):
        return (self.area_coberta * self.preco_m2 +
                self.area_descoberta * self.preco_m2 * self.coef_area_descoberta)

    @property
    def area_total(self):
        return self.area_coberta + self.area_descoberta

    @property
    def identificador(self):
        return f'{self.bloco.nome} - {self.numero}'

    def __repr__(self):
        return f'<Unidade {self.numero}>'


class PlanoPadrao(db.Model):
    __tablename__ = 'planos_padrao'
    id = db.Column(db.Integer, primary_key=True)
    empreendimento_id = db.Column(db.Integer, db.ForeignKey('empreendimentos.id'),
                                   unique=True, nullable=False)
    sinal_qtd = db.Column(db.Integer, default=1)
    sinal_pct = db.Column(db.Float, default=10.0)
    mensal_qtd = db.Column(db.Integer, default=24)
    mensal_pct = db.Column(db.Float, default=10.0)
    intermediaria_qtd = db.Column(db.Integer, default=2)
    intermediaria_pct = db.Column(db.Float, default=10.0)
    intermediaria_periodicidade = db.Column(db.String(1), default='S')
    chave_pct = db.Column(db.Float, default=10.0)
    financiamento_pct = db.Column(db.Float, default=60.0)

    empreendimento = db.relationship('Empreendimento', back_populates='plano_padrao')

    def __repr__(self):
        return f'<PlanoPadrao emp={self.empreendimento_id}>'


class RegrasEmpreendimento(db.Model):
    __tablename__ = 'regras_empreendimento'
    id = db.Column(db.Integer, primary_key=True)
    empreendimento_id = db.Column(db.Integer, db.ForeignKey('empreendimentos.id'),
                                   unique=True, nullable=False)
    # Sinal
    pct_min_sinal = db.Column(db.Float, default=5.0)
    # Mensais
    pct_min_mensal = db.Column(db.Float, default=5.0)
    qtd_max_mensal = db.Column(db.Integer, default=48)
    # Financiamento
    pct_min_financiamento = db.Column(db.Float, default=0.0)
    pct_max_financiamento = db.Column(db.Float, default=80.0)
    # Chave
    valor_max_chave = db.Column(db.Float, default=0.0)  # 0 = sem limite
    # Intermediarias por periodicidade
    qtd_max_bimestrais = db.Column(db.Integer, default=0)
    qtd_max_trimestrais = db.Column(db.Integer, default=0)
    qtd_max_semestrais = db.Column(db.Integer, default=0)
    qtd_max_anuais = db.Column(db.Integer, default=0)

    empreendimento = db.relationship('Empreendimento', back_populates='regras')

    def __repr__(self):
        return f'<RegrasEmpreendimento emp={self.empreendimento_id}>'


class Simulacao(db.Model):
    __tablename__ = 'simulacoes'
    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False, index=True, default=gerar_codigo)
    corretor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    empreendimento_id = db.Column(db.Integer, db.ForeignKey('empreendimentos.id'), nullable=False)
    unidade_id = db.Column(db.Integer, db.ForeignKey('unidades.id'), nullable=False)
    cliente_nome = db.Column(db.String(200))
    cliente_telefone = db.Column(db.String(20))
    # Sinal
    sinal_qtd = db.Column(db.Integer, default=0)
    sinal_valor = db.Column(db.Float, default=0.0)
    sinal_data_inicio = db.Column(db.Date)
    # Mensal
    mensal_qtd = db.Column(db.Integer, default=0)
    mensal_valor = db.Column(db.Float, default=0.0)
    mensal_data_inicio = db.Column(db.Date)
    # Intermediaria
    intermediaria_qtd = db.Column(db.Integer, default=0)
    intermediaria_valor = db.Column(db.Float, default=0.0)
    intermediaria_data_inicio = db.Column(db.Date)
    intermediaria_periodicidade = db.Column(db.String(1), default='S')
    # Chave (single)
    chave_valor = db.Column(db.Float, default=0.0)
    chave_data = db.Column(db.Date)
    # Financiamento (single)
    financiamento_valor = db.Column(db.Float, default=0.0)
    financiamento_data = db.Column(db.Date)
    # Calculated
    valor_nominal_proposta = db.Column(db.Float, default=0.0)
    vp_proposta = db.Column(db.Float, default=0.0)
    valor_nominal_tabela = db.Column(db.Float, default=0.0)
    vp_tabela = db.Column(db.Float, default=0.0)
    dif_pct_proposta = db.Column(db.Float, default=0.0)
    dif_pct_tabela = db.Column(db.Float, default=0.0)
    detalhes_json = db.Column(db.JSON)
    # Approval
    status = db.Column(db.String(20), default='pendente')
    aprovador_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    data_aprovacao = db.Column(db.DateTime)
    motivo_rejeicao = db.Column(db.String(500))
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    corretor = db.relationship('User', foreign_keys=[corretor_id], back_populates='simulacoes')
    aprovador = db.relationship('User', foreign_keys=[aprovador_id])
    empreendimento = db.relationship('Empreendimento', back_populates='simulacoes')
    unidade = db.relationship('Unidade')

    def __repr__(self):
        return f'<Simulacao {self.codigo}>'
