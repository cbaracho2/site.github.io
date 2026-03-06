import csv
import io
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Empresa, User, Empreendimento, Bloco, Unidade, PlanoPadrao, RegrasEmpreendimento
from login import role_required

adm_bp = Blueprint('adm_bp', __name__)


def _check_empresa_access(empresa_id):
    """Lider can only access their own company's data."""
    if current_user.is_admin:
        return True
    return current_user.empresa_id == empresa_id


def _check_empreendimento_access(emp):
    """Check if current user can manage this empreendimento."""
    if not emp:
        return False
    return _check_empresa_access(emp.empresa_id)


@adm_bp.route('/')
@role_required('lider', 'adm')
def dashboard():
    if current_user.is_admin:
        empresas = Empresa.query.filter_by(ativo=True).all()
        empreendimentos = Empreendimento.query.filter_by(ativo=True).all()
        usuarios = User.query.all()
    else:
        empresas = [current_user.empresa]
        empreendimentos = Empreendimento.query.filter_by(
            ativo=True, empresa_id=current_user.empresa_id
        ).all()
        usuarios = User.query.filter_by(empresa_id=current_user.empresa_id).all()
    return render_template('adm.html',
                           empresas=empresas,
                           empreendimentos=empreendimentos,
                           usuarios=usuarios)


# -- EMPRESAS --

@adm_bp.route('/empresas', methods=['POST'])
@role_required('adm')
def criar_empresa():
    nome = request.form.get('nome', '').strip()
    cnpj = request.form.get('cnpj', '').strip()
    if not nome:
        flash('Nome da empresa obrigatorio.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))
    empresa = Empresa(nome=nome, cnpj=cnpj or None)
    db.session.add(empresa)
    db.session.commit()
    flash(f'Empresa "{nome}" cadastrada.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/empresas/<int:id>/editar', methods=['POST'])
@role_required('lider', 'adm')
def editar_empresa(id):
    empresa = db.session.get(Empresa, id)
    if not empresa:
        flash('Empresa nao encontrada.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    if not _check_empresa_access(empresa.id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    empresa.nome = request.form.get('nome', empresa.nome).strip()
    empresa.cnpj = request.form.get('cnpj', empresa.cnpj).strip()
    db.session.commit()
    flash('Empresa atualizada.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/empresas/<int:id>/excluir', methods=['POST'])
@role_required('adm')
def excluir_empresa(id):
    empresa = db.session.get(Empresa, id)
    if empresa:
        empresa.ativo = False
        db.session.commit()
        flash('Empresa desativada.', 'info')
    return redirect(url_for('adm_bp.dashboard'))


# -- EMPREENDIMENTOS --

@adm_bp.route('/empreendimentos', methods=['POST'])
@role_required('lider', 'adm')
def criar_empreendimento():
    nome = request.form.get('nome', '').strip()
    endereco = request.form.get('endereco', '').strip()
    taxa = request.form.get('taxa_desconto_mensal', 0.01, type=float)
    if current_user.is_admin:
        empresa_id = request.form.get('empresa_id', type=int)
    else:
        empresa_id = current_user.empresa_id
    if not nome or not empresa_id:
        flash('Nome e empresa obrigatorios.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))
    if not _check_empresa_access(empresa_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    emp = Empreendimento(nome=nome, endereco=endereco, empresa_id=empresa_id,
                         taxa_desconto_mensal=taxa)
    db.session.add(emp)
    db.session.flush()
    plano = PlanoPadrao(empreendimento_id=emp.id)
    db.session.add(plano)
    regras = RegrasEmpreendimento(empreendimento_id=emp.id)
    db.session.add(regras)
    db.session.commit()
    flash(f'Empreendimento "{nome}" cadastrado.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/empreendimentos/<int:id>/editar', methods=['POST'])
@role_required('lider', 'adm')
def editar_empreendimento(id):
    emp = db.session.get(Empreendimento, id)
    if not emp:
        flash('Empreendimento nao encontrado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    if not _check_empreendimento_access(emp):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    emp.nome = request.form.get('nome', emp.nome).strip()
    emp.endereco = request.form.get('endereco', emp.endereco).strip()
    if current_user.is_admin:
        emp.empresa_id = request.form.get('empresa_id', emp.empresa_id, type=int)
    emp.taxa_desconto_mensal = request.form.get('taxa_desconto_mensal',
                                                 emp.taxa_desconto_mensal, type=float)
    db.session.commit()
    flash('Empreendimento atualizado.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/empreendimentos/<int:id>/excluir', methods=['POST'])
@role_required('lider', 'adm')
def excluir_empreendimento(id):
    emp = db.session.get(Empreendimento, id)
    if emp:
        if not _check_empreendimento_access(emp):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))
        emp.ativo = False
        db.session.commit()
        flash('Empreendimento desativado.', 'info')
    return redirect(url_for('adm_bp.dashboard'))


# -- BLOCOS --

@adm_bp.route('/empreendimentos/<int:emp_id>/blocos', methods=['POST'])
@role_required('lider', 'adm')
def criar_bloco(emp_id):
    emp = db.session.get(Empreendimento, emp_id)
    if not emp or not _check_empreendimento_access(emp):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    nome = request.form.get('nome', '').strip()
    if not nome:
        flash('Nome do bloco obrigatorio.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))
    bloco = Bloco(nome=nome, empreendimento_id=emp_id)
    db.session.add(bloco)
    db.session.commit()
    flash(f'Bloco "{nome}" criado.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/blocos/<int:id>/excluir', methods=['POST'])
@role_required('lider', 'adm')
def excluir_bloco(id):
    bloco = db.session.get(Bloco, id)
    if bloco:
        if not _check_empreendimento_access(bloco.empreendimento):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))
        db.session.delete(bloco)
        db.session.commit()
        flash('Bloco excluido.', 'info')
    return redirect(url_for('adm_bp.dashboard'))


# -- UNIDADES --

@adm_bp.route('/blocos/<int:bloco_id>/unidades', methods=['POST'])
@role_required('lider', 'adm')
def criar_unidade(bloco_id):
    bloco = db.session.get(Bloco, bloco_id)
    if not bloco or not _check_empreendimento_access(bloco.empreendimento):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    numero = request.form.get('numero', '').strip()
    if not numero:
        flash('Numero da unidade obrigatorio.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))
    unidade = Unidade(
        numero=numero,
        bloco_id=bloco_id,
        descricao=request.form.get('descricao', '').strip(),
        area_coberta=request.form.get('area_coberta', 0, type=float),
        area_descoberta=request.form.get('area_descoberta', 0, type=float),
        preco_m2=request.form.get('preco_m2', 0, type=float),
        coef_area_descoberta=request.form.get('coef_area_descoberta', 0.5, type=float),
        status='disponivel'
    )
    db.session.add(unidade)
    db.session.commit()
    flash(f'Unidade {numero} criada.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/blocos/<int:bloco_id>/unidades/lote', methods=['POST'])
@role_required('lider', 'adm')
def criar_unidades_lote(bloco_id):
    bloco = db.session.get(Bloco, bloco_id)
    if not bloco or not _check_empreendimento_access(bloco.empreendimento):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))

    numeros = request.form.get('numeros', '').strip()
    descricao = request.form.get('descricao', '').strip()
    area_coberta = request.form.get('area_coberta', 0, type=float)
    area_descoberta = request.form.get('area_descoberta', 0, type=float)
    preco_m2 = request.form.get('preco_m2', 0, type=float)
    coef_area_descoberta = request.form.get('coef_area_descoberta', 0.5, type=float)

    if not numeros:
        flash('Informe os numeros das unidades.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))

    # Parse: comma-separated or range (e.g. "101,102,103" or "101-110")
    unidades_criadas = 0
    for part in numeros.split(','):
        part = part.strip()
        if '-' in part:
            try:
                inicio, fim = part.split('-', 1)
                inicio = int(inicio.strip())
                fim = int(fim.strip())
                for n in range(inicio, fim + 1):
                    u = Unidade(
                        numero=str(n), bloco_id=bloco_id, descricao=descricao,
                        area_coberta=area_coberta, area_descoberta=area_descoberta,
                        preco_m2=preco_m2, coef_area_descoberta=coef_area_descoberta,
                        status='disponivel'
                    )
                    db.session.add(u)
                    unidades_criadas += 1
            except ValueError:
                flash(f'Formato invalido: "{part}". Use numeros como 101-110.', 'warning')
                continue
        elif part:
            u = Unidade(
                numero=part, bloco_id=bloco_id, descricao=descricao,
                area_coberta=area_coberta, area_descoberta=area_descoberta,
                preco_m2=preco_m2, coef_area_descoberta=coef_area_descoberta,
                status='disponivel'
            )
            db.session.add(u)
            unidades_criadas += 1

    db.session.commit()
    flash(f'{unidades_criadas} unidade(s) criada(s) em lote.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/blocos/<int:bloco_id>/unidades/csv', methods=['POST'])
@role_required('lider', 'adm')
def importar_unidades_csv(bloco_id):
    bloco = db.session.get(Bloco, bloco_id)
    if not bloco or not _check_empreendimento_access(bloco.empreendimento):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))

    arquivo = request.files.get('arquivo_csv')
    if not arquivo or not arquivo.filename:
        flash('Selecione um arquivo CSV.', 'warning')
        return redirect(url_for('adm_bp.dashboard'))

    if not arquivo.filename.lower().endswith('.csv'):
        flash('O arquivo deve ser .csv', 'warning')
        return redirect(url_for('adm_bp.dashboard'))

    try:
        conteudo = arquivo.read().decode('utf-8-sig')
    except UnicodeDecodeError:
        try:
            arquivo.seek(0)
            conteudo = arquivo.read().decode('latin-1')
        except Exception:
            flash('Erro ao ler o arquivo. Verifique a codificacao.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))

    # Detect delimiter (comma or semicolon)
    primeira_linha = conteudo.split('\n')[0] if conteudo else ''
    delimitador = ';' if primeira_linha.count(';') > primeira_linha.count(',') else ','

    leitor = csv.DictReader(io.StringIO(conteudo), delimiter=delimitador)

    # Normalize header names (lowercase, strip, remove accents)
    CAMPO_MAP = {
        'numero': 'numero', 'num': 'numero', 'unidade': 'numero', 'unit': 'numero',
        'descricao': 'descricao', 'desc': 'descricao', 'description': 'descricao',
        'area_coberta': 'area_coberta', 'areacoberta': 'area_coberta',
        'area coberta': 'area_coberta', 'coberta': 'area_coberta',
        'area_descoberta': 'area_descoberta', 'areadescoberta': 'area_descoberta',
        'area descoberta': 'area_descoberta', 'descoberta': 'area_descoberta',
        'preco_m2': 'preco_m2', 'precom2': 'preco_m2', 'preco m2': 'preco_m2',
        'preco': 'preco_m2', 'price': 'preco_m2', 'r$/m2': 'preco_m2',
        'coef_area_descoberta': 'coef_area_descoberta', 'coef': 'coef_area_descoberta',
        'coeficiente': 'coef_area_descoberta',
        'status': 'status',
    }

    unidades_criadas = 0
    erros = []
    for i, row in enumerate(leitor, start=2):
        # Map CSV column names to model fields
        dados = {}
        for col_csv, valor in row.items():
            if col_csv is None:
                continue
            chave = col_csv.strip().lower().replace('ã', 'a').replace('é', 'e').replace('ç', 'c')
            campo = CAMPO_MAP.get(chave)
            if campo:
                dados[campo] = valor.strip() if valor else ''

        numero = dados.get('numero', '').strip()
        if not numero:
            erros.append(f'Linha {i}: numero da unidade vazio, ignorada.')
            continue

        # Parse numeric fields with comma support (Brazilian format)
        def parse_float(val, default=0.0):
            if not val:
                return default
            val = val.replace('.', '').replace(',', '.') if ',' in val else val
            try:
                return float(val)
            except (ValueError, TypeError):
                return default

        area_coberta = parse_float(dados.get('area_coberta', ''))
        area_descoberta = parse_float(dados.get('area_descoberta', ''))
        preco_m2 = parse_float(dados.get('preco_m2', ''))
        coef = parse_float(dados.get('coef_area_descoberta', ''), 0.5)
        descricao = dados.get('descricao', '')
        status = dados.get('status', 'disponivel') or 'disponivel'

        if status not in ('disponivel', 'reservada', 'vendida'):
            status = 'disponivel'

        u = Unidade(
            numero=numero,
            bloco_id=bloco_id,
            descricao=descricao,
            area_coberta=area_coberta,
            area_descoberta=area_descoberta,
            preco_m2=preco_m2,
            coef_area_descoberta=coef,
            status=status
        )
        db.session.add(u)
        unidades_criadas += 1

    if unidades_criadas > 0:
        db.session.commit()

    msg = f'{unidades_criadas} unidade(s) importada(s) via CSV.'
    if erros:
        msg += ' Avisos: ' + '; '.join(erros[:5])
        if len(erros) > 5:
            msg += f' ... e mais {len(erros) - 5} aviso(s).'
    flash(msg, 'success' if unidades_criadas > 0 else 'warning')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/unidades/<int:id>/editar', methods=['POST'])
@role_required('lider', 'adm')
def editar_unidade(id):
    u = db.session.get(Unidade, id)
    if not u:
        flash('Unidade nao encontrada.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    if not _check_empreendimento_access(u.bloco.empreendimento):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    u.numero = request.form.get('numero', u.numero).strip()
    u.descricao = request.form.get('descricao', u.descricao).strip()
    u.area_coberta = request.form.get('area_coberta', u.area_coberta, type=float)
    u.area_descoberta = request.form.get('area_descoberta', u.area_descoberta, type=float)
    u.preco_m2 = request.form.get('preco_m2', u.preco_m2, type=float)
    u.coef_area_descoberta = request.form.get('coef_area_descoberta',
                                               u.coef_area_descoberta, type=float)
    u.status = request.form.get('status', u.status)
    db.session.commit()
    flash('Unidade atualizada.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/unidades/<int:id>/excluir', methods=['POST'])
@role_required('lider', 'adm')
def excluir_unidade(id):
    u = db.session.get(Unidade, id)
    if u:
        if not _check_empreendimento_access(u.bloco.empreendimento):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))
        db.session.delete(u)
        db.session.commit()
        flash('Unidade excluida.', 'info')
    return redirect(url_for('adm_bp.dashboard'))


# -- PLANO PADRAO --

@adm_bp.route('/empreendimentos/<int:emp_id>/plano-padrao', methods=['POST'])
@role_required('lider', 'adm')
def editar_plano_padrao(emp_id):
    emp = db.session.get(Empreendimento, emp_id)
    if not emp or not _check_empreendimento_access(emp):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))

    plano = PlanoPadrao.query.filter_by(empreendimento_id=emp_id).first()
    if not plano:
        plano = PlanoPadrao(empreendimento_id=emp_id)
        db.session.add(plano)

    plano.sinal_qtd = request.form.get('sinal_qtd', 1, type=int)
    plano.sinal_pct = request.form.get('sinal_pct', 10, type=float)
    plano.mensal_qtd = request.form.get('mensal_qtd', 24, type=int)
    plano.mensal_pct = request.form.get('mensal_pct', 10, type=float)
    plano.intermediaria_qtd = request.form.get('intermediaria_qtd', 2, type=int)
    plano.intermediaria_pct = request.form.get('intermediaria_pct', 10, type=float)
    plano.intermediaria_periodicidade = request.form.get('intermediaria_periodicidade', 'S')
    plano.chave_pct = request.form.get('chave_pct', 10, type=float)
    plano.financiamento_pct = request.form.get('financiamento_pct', 60, type=float)

    db.session.commit()
    flash('Plano padrao atualizado.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


# -- REGRAS EMPREENDIMENTO --

@adm_bp.route('/empreendimentos/<int:emp_id>/regras', methods=['POST'])
@role_required('lider', 'adm')
def editar_regras(emp_id):
    emp = db.session.get(Empreendimento, emp_id)
    if not emp or not _check_empreendimento_access(emp):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))

    regras = RegrasEmpreendimento.query.filter_by(empreendimento_id=emp_id).first()
    if not regras:
        regras = RegrasEmpreendimento(empreendimento_id=emp_id)
        db.session.add(regras)

    regras.pct_min_sinal = request.form.get('pct_min_sinal', 5, type=float)
    regras.pct_min_mensal = request.form.get('pct_min_mensal', 5, type=float)
    regras.qtd_max_mensal = request.form.get('qtd_max_mensal', 48, type=int)
    regras.pct_min_financiamento = request.form.get('pct_min_financiamento', 0, type=float)
    regras.pct_max_financiamento = request.form.get('pct_max_financiamento', 80, type=float)
    regras.valor_max_chave = request.form.get('valor_max_chave', 0, type=float)
    regras.qtd_max_bimestrais = request.form.get('qtd_max_bimestrais', 0, type=int)
    regras.qtd_max_trimestrais = request.form.get('qtd_max_trimestrais', 0, type=int)
    regras.qtd_max_semestrais = request.form.get('qtd_max_semestrais', 0, type=int)
    regras.qtd_max_anuais = request.form.get('qtd_max_anuais', 0, type=int)

    db.session.commit()
    flash('Regras do empreendimento atualizadas.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


# -- API: REGRAS --

@adm_bp.route('/api/empreendimentos/<int:emp_id>/regras')
@role_required('lider', 'adm')
def api_regras(emp_id):
    regras = RegrasEmpreendimento.query.filter_by(empreendimento_id=emp_id).first()
    if not regras:
        return jsonify({
            'pct_min_sinal': 5, 'pct_min_mensal': 5, 'qtd_max_mensal': 48,
            'pct_min_financiamento': 0, 'pct_max_financiamento': 80,
            'valor_max_chave': 0,
            'qtd_max_bimestrais': 0, 'qtd_max_trimestrais': 0,
            'qtd_max_semestrais': 0, 'qtd_max_anuais': 0,
        })
    return jsonify({
        'pct_min_sinal': regras.pct_min_sinal,
        'pct_min_mensal': regras.pct_min_mensal,
        'qtd_max_mensal': regras.qtd_max_mensal,
        'pct_min_financiamento': regras.pct_min_financiamento,
        'pct_max_financiamento': regras.pct_max_financiamento,
        'valor_max_chave': regras.valor_max_chave,
        'qtd_max_bimestrais': regras.qtd_max_bimestrais,
        'qtd_max_trimestrais': regras.qtd_max_trimestrais,
        'qtd_max_semestrais': regras.qtd_max_semestrais,
        'qtd_max_anuais': regras.qtd_max_anuais,
    })


# -- USUARIOS --

@adm_bp.route('/usuarios')
@role_required('lider', 'adm')
def usuarios():
    if current_user.is_admin:
        users = User.query.all()
        empresas = Empresa.query.filter_by(ativo=True).all()
        empreendimentos = Empreendimento.query.filter_by(ativo=True).all()
    else:
        users = User.query.filter_by(empresa_id=current_user.empresa_id).all()
        empresas = [current_user.empresa]
        empreendimentos = Empreendimento.query.filter_by(
            ativo=True, empresa_id=current_user.empresa_id
        ).all()
    return render_template('adm.html', usuarios=users,
                           empresas=empresas,
                           empreendimentos=empreendimentos)


@adm_bp.route('/usuarios/<int:id>/editar', methods=['POST'])
@role_required('lider', 'adm')
def editar_usuario(id):
    user = db.session.get(User, id)
    if not user or user.id == current_user.id:
        flash('Operacao invalida.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    if not _check_empresa_access(user.empresa_id):
        flash('Acesso negado.', 'danger')
        return redirect(url_for('adm_bp.dashboard'))
    user.nome = request.form.get('nome', user.nome).strip()
    user.email = request.form.get('email', user.email).strip().lower()
    if current_user.is_admin:
        user.role = request.form.get('role', user.role)
        new_empresa = request.form.get('empresa_id', type=int)
        if new_empresa:
            user.empresa_id = new_empresa
    db.session.commit()
    flash(f'Usuario {user.nome} atualizado.', 'success')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/usuarios/<int:id>/toggle', methods=['POST'])
@role_required('lider', 'adm')
def toggle_usuario(id):
    user = db.session.get(User, id)
    if user and user.id != current_user.id:
        if not _check_empresa_access(user.empresa_id):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))
        user.ativo = not user.ativo
        db.session.commit()
        status = 'ativado' if user.ativo else 'desativado'
        flash(f'Usuario {user.nome} {status}.', 'info')
    return redirect(url_for('adm_bp.dashboard'))


@adm_bp.route('/usuarios/<int:id>/reset-senha', methods=['POST'])
@role_required('lider', 'adm')
def reset_senha(id):
    user = db.session.get(User, id)
    if user:
        if not _check_empresa_access(user.empresa_id):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('adm_bp.dashboard'))
        nova_senha = request.form.get('nova_senha', '123456')
        user.set_password(nova_senha)
        db.session.commit()
        flash(f'Senha de {user.nome} redefinida.', 'success')
    return redirect(url_for('adm_bp.dashboard'))
