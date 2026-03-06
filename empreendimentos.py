from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import db, Empreendimento, Bloco, Unidade, PlanoPadrao, Simulacao, RegrasEmpreendimento
from login import role_required
from engine import (construir_fluxo_pagamentos, calcular_vp,
                    construir_plano_padrao_pagamentos, comparar_proposta_vs_tabela)

emp_bp = Blueprint('emp_bp', __name__)
api_bp = Blueprint('api_bp', __name__)


# ═══════════════════════════════════════════
#  SIMULATOR PAGES
# ═══════════════════════════════════════════

@emp_bp.route('/')
@login_required
def simulador():
    if current_user.is_admin:
        empreendimentos = Empreendimento.query.filter_by(ativo=True).all()
    else:
        empreendimentos = Empreendimento.query.filter_by(
            ativo=True, empresa_id=current_user.empresa_id
        ).all()
    return render_template('empreendimentos.html', empreendimentos=empreendimentos)


@emp_bp.route('/salvar', methods=['POST'])
@login_required
def salvar_simulacao():
    data = request.form
    unidade_id = data.get('unidade_id', type=int)
    empreendimento_id = data.get('empreendimento_id', type=int)

    if not unidade_id or not empreendimento_id:
        flash('Selecione uma unidade.', 'warning')
        return redirect(url_for('emp_bp.simulador'))

    unidade = db.session.get(Unidade, unidade_id)
    emp = db.session.get(Empreendimento, empreendimento_id)
    if not unidade or not emp:
        flash('Unidade ou empreendimento invalido.', 'danger')
        return redirect(url_for('emp_bp.simulador'))

    # Build proposta dict
    proposta = {
        'sinal_qtd': data.get('sinal_qtd', 0, type=int),
        'sinal_valor': data.get('sinal_valor', 0, type=float),
        'sinal_data_inicio': data.get('sinal_data_inicio') or None,
        'mensal_qtd': data.get('mensal_qtd', 0, type=int),
        'mensal_valor': data.get('mensal_valor', 0, type=float),
        'mensal_data_inicio': data.get('mensal_data_inicio') or None,
        'intermediaria_qtd': data.get('intermediaria_qtd', 0, type=int),
        'intermediaria_valor': data.get('intermediaria_valor', 0, type=float),
        'intermediaria_data_inicio': data.get('intermediaria_data_inicio') or None,
        'intermediaria_periodicidade': data.get('intermediaria_periodicidade', 'S'),
        'chave_valor': data.get('chave_valor', 0, type=float),
        'chave_data': data.get('chave_data') or None,
        'financiamento_valor': data.get('financiamento_valor', 0, type=float),
        'financiamento_data': data.get('financiamento_data') or None,
    }

    # Calculate VP comparison
    plano_padrao = PlanoPadrao.query.filter_by(empreendimento_id=empreendimento_id).first()
    if not plano_padrao:
        flash('Plano padrao nao configurado para este empreendimento.', 'danger')
        return redirect(url_for('emp_bp.simulador'))

    resultado = comparar_proposta_vs_tabela(
        proposta, plano_padrao, unidade.valor_total,
        emp.taxa_desconto_mensal, date.today()
    )

    # Parse dates for DB storage
    def parse_date(d):
        if not d:
            return None
        if isinstance(d, str):
            return date.fromisoformat(d)
        return d

    sim = Simulacao(
        corretor_id=current_user.id,
        empreendimento_id=empreendimento_id,
        unidade_id=unidade_id,
        cliente_nome=data.get('cliente_nome', '').strip(),
        cliente_telefone=data.get('cliente_telefone', '').strip(),
        sinal_qtd=proposta['sinal_qtd'],
        sinal_valor=proposta['sinal_valor'],
        sinal_data_inicio=parse_date(proposta['sinal_data_inicio']),
        mensal_qtd=proposta['mensal_qtd'],
        mensal_valor=proposta['mensal_valor'],
        mensal_data_inicio=parse_date(proposta['mensal_data_inicio']),
        intermediaria_qtd=proposta['intermediaria_qtd'],
        intermediaria_valor=proposta['intermediaria_valor'],
        intermediaria_data_inicio=parse_date(proposta['intermediaria_data_inicio']),
        intermediaria_periodicidade=proposta['intermediaria_periodicidade'],
        chave_valor=proposta['chave_valor'],
        chave_data=parse_date(proposta['chave_data']),
        financiamento_valor=proposta['financiamento_valor'],
        financiamento_data=parse_date(proposta['financiamento_data']),
        valor_nominal_proposta=resultado['proposta']['nominal_total'],
        vp_proposta=resultado['proposta']['vp_total'],
        valor_nominal_tabela=resultado['tabela']['nominal_total'],
        vp_tabela=resultado['tabela']['vp_total'],
        dif_pct_proposta=resultado['proposta']['dif_pct'],
        dif_pct_tabela=resultado['tabela']['dif_pct'],
        detalhes_json=resultado,
        status='pendente'
    )

    db.session.add(sim)
    db.session.commit()

    flash('Simulacao salva com sucesso! Codigo: ' + sim.codigo, 'success')
    return redirect(url_for('emp_bp.report', id=sim.id))


@emp_bp.route('/report/<int:id>')
@login_required
def report(id):
    sim = db.session.get(Simulacao, id)
    if not sim:
        flash('Simulacao nao encontrada.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))
    # Corretor can only see own simulations
    if not current_user.is_lider and sim.corretor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))
    return render_template('report.html', sim=sim)


@emp_bp.route('/minhas')
@login_required
def minhas_simulacoes():
    if current_user.is_admin:
        sims = Simulacao.query.order_by(Simulacao.created_at.desc()).all()
    elif current_user.is_lider:
        sims = Simulacao.query.join(Empreendimento).filter(
            Empreendimento.empresa_id == current_user.empresa_id
        ).order_by(Simulacao.created_at.desc()).all()
    else:
        sims = Simulacao.query.filter_by(
            corretor_id=current_user.id
        ).order_by(Simulacao.created_at.desc()).all()
    return render_template('consultar.html', simulacoes=sims)


@emp_bp.route('/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def editar_simulacao(id):
    sim = db.session.get(Simulacao, id)
    if not sim:
        flash('Simulacao nao encontrada.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))
    if not current_user.is_admin and sim.corretor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))

    if request.method == 'POST':
        data = request.form

        sim.cliente_nome = data.get('cliente_nome', '').strip()
        sim.cliente_telefone = data.get('cliente_telefone', '').strip()
        sim.sinal_qtd = data.get('sinal_qtd', 0, type=int)
        sim.sinal_valor = data.get('sinal_valor', 0, type=float)
        sim.sinal_data_inicio = date.fromisoformat(data['sinal_data_inicio']) if data.get('sinal_data_inicio') else None
        sim.mensal_qtd = data.get('mensal_qtd', 0, type=int)
        sim.mensal_valor = data.get('mensal_valor', 0, type=float)
        sim.mensal_data_inicio = date.fromisoformat(data['mensal_data_inicio']) if data.get('mensal_data_inicio') else None
        sim.intermediaria_qtd = data.get('intermediaria_qtd', 0, type=int)
        sim.intermediaria_valor = data.get('intermediaria_valor', 0, type=float)
        sim.intermediaria_data_inicio = date.fromisoformat(data['intermediaria_data_inicio']) if data.get('intermediaria_data_inicio') else None
        sim.intermediaria_periodicidade = data.get('intermediaria_periodicidade', 'S')
        sim.chave_valor = data.get('chave_valor', 0, type=float)
        sim.chave_data = date.fromisoformat(data['chave_data']) if data.get('chave_data') else None
        sim.financiamento_valor = data.get('financiamento_valor', 0, type=float)
        sim.financiamento_data = date.fromisoformat(data['financiamento_data']) if data.get('financiamento_data') else None

        # Recalculate VP
        proposta = {
            'sinal_qtd': sim.sinal_qtd, 'sinal_valor': sim.sinal_valor,
            'sinal_data_inicio': sim.sinal_data_inicio,
            'mensal_qtd': sim.mensal_qtd, 'mensal_valor': sim.mensal_valor,
            'mensal_data_inicio': sim.mensal_data_inicio,
            'intermediaria_qtd': sim.intermediaria_qtd, 'intermediaria_valor': sim.intermediaria_valor,
            'intermediaria_data_inicio': sim.intermediaria_data_inicio,
            'intermediaria_periodicidade': sim.intermediaria_periodicidade,
            'chave_valor': sim.chave_valor, 'chave_data': sim.chave_data,
            'financiamento_valor': sim.financiamento_valor, 'financiamento_data': sim.financiamento_data,
        }

        plano_padrao = PlanoPadrao.query.filter_by(empreendimento_id=sim.empreendimento_id).first()
        resultado = comparar_proposta_vs_tabela(
            proposta, plano_padrao, sim.unidade.valor_total,
            sim.empreendimento.taxa_desconto_mensal, date.today()
        )

        sim.valor_nominal_proposta = resultado['proposta']['nominal_total']
        sim.vp_proposta = resultado['proposta']['vp_total']
        sim.valor_nominal_tabela = resultado['tabela']['nominal_total']
        sim.vp_tabela = resultado['tabela']['vp_total']
        sim.dif_pct_proposta = resultado['proposta']['dif_pct']
        sim.dif_pct_tabela = resultado['tabela']['dif_pct']
        sim.detalhes_json = resultado
        sim.status = 'pendente'  # Reset to pending after edit

        db.session.commit()
        flash('Simulacao atualizada.', 'success')
        return redirect(url_for('emp_bp.report', id=sim.id))

    if current_user.is_admin:
        empreendimentos = Empreendimento.query.filter_by(ativo=True).all()
    else:
        empreendimentos = Empreendimento.query.filter_by(
            ativo=True, empresa_id=current_user.empresa_id
        ).all()
    return render_template('empreendimentos.html', empreendimentos=empreendimentos, editando=sim)


@emp_bp.route('/<int:id>/deletar', methods=['POST'])
@login_required
def deletar_simulacao(id):
    sim = db.session.get(Simulacao, id)
    if not sim:
        flash('Simulacao nao encontrada.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))
    if not current_user.is_admin and sim.corretor_id != current_user.id:
        flash('Acesso negado.', 'danger')
        return redirect(url_for('emp_bp.minhas_simulacoes'))
    db.session.delete(sim)
    db.session.commit()
    flash('Simulacao excluida.', 'info')
    return redirect(url_for('emp_bp.minhas_simulacoes'))


# ═══════════════════════════════════════════
#  APPROVAL QUEUE
# ═══════════════════════════════════════════

@emp_bp.route('/fila')
@role_required('lider', 'adm')
def fila_aprovacao():
    status_filter = request.args.get('status', 'pendente')
    query = Simulacao.query

    if not current_user.is_admin:
        query = query.join(Empreendimento).filter(
            Empreendimento.empresa_id == current_user.empresa_id
        )

    if status_filter and status_filter != 'todos':
        query = query.filter(Simulacao.status == status_filter)

    sims = query.order_by(Simulacao.created_at.desc()).all()
    pendentes_count = Simulacao.query.filter_by(status='pendente').count()

    return render_template('fila_aprovacao.html', simulacoes=sims,
                           status_filter=status_filter, pendentes_count=pendentes_count)


@emp_bp.route('/fila/<int:id>/aprovar', methods=['POST'])
@role_required('lider', 'adm')
def aprovar_simulacao(id):
    sim = db.session.get(Simulacao, id)
    if sim and sim.status == 'pendente':
        sim.status = 'aprovada'
        sim.aprovador_id = current_user.id
        sim.data_aprovacao = datetime.utcnow()
        db.session.commit()
        flash(f'Simulacao {sim.codigo} aprovada.', 'success')
    return redirect(url_for('emp_bp.fila_aprovacao'))


@emp_bp.route('/fila/<int:id>/rejeitar', methods=['POST'])
@role_required('lider', 'adm')
def rejeitar_simulacao(id):
    sim = db.session.get(Simulacao, id)
    if sim and sim.status == 'pendente':
        sim.status = 'rejeitada'
        sim.aprovador_id = current_user.id
        sim.data_aprovacao = datetime.utcnow()
        sim.motivo_rejeicao = request.form.get('motivo', '').strip()
        db.session.commit()
        flash(f'Simulacao {sim.codigo} rejeitada.', 'info')
    return redirect(url_for('emp_bp.fila_aprovacao'))


# ═══════════════════════════════════════════
#  API ENDPOINTS (JSON)
# ═══════════════════════════════════════════

@api_bp.route('/empreendimentos')
@login_required
def api_empreendimentos():
    if current_user.is_admin:
        emps = Empreendimento.query.filter_by(ativo=True).all()
    else:
        emps = Empreendimento.query.filter_by(
            ativo=True, empresa_id=current_user.empresa_id
        ).all()
    return jsonify([{
        'id': e.id, 'nome': e.nome,
        'taxa_desconto_mensal': e.taxa_desconto_mensal
    } for e in emps])


@api_bp.route('/empreendimentos/<int:id>/blocos')
@login_required
def api_blocos(id):
    blocos = Bloco.query.filter_by(empreendimento_id=id).all()
    return jsonify([{'id': b.id, 'nome': b.nome} for b in blocos])


@api_bp.route('/blocos/<int:id>/unidades')
@login_required
def api_unidades(id):
    unidades = Unidade.query.filter_by(bloco_id=id).all()
    return jsonify([{
        'id': u.id, 'numero': u.numero, 'descricao': u.descricao,
        'area_coberta': u.area_coberta, 'area_descoberta': u.area_descoberta,
        'preco_m2': u.preco_m2, 'coef_area_descoberta': u.coef_area_descoberta,
        'valor_total': round(u.valor_total, 2), 'status': u.status,
        'area_total': u.area_total
    } for u in unidades])


@api_bp.route('/unidades/<int:id>')
@login_required
def api_unidade_detalhe(id):
    u = db.session.get(Unidade, id)
    if not u:
        return jsonify({'error': 'Unidade nao encontrada'}), 404
    emp = u.bloco.empreendimento
    return jsonify({
        'id': u.id, 'numero': u.numero, 'descricao': u.descricao,
        'bloco': u.bloco.nome, 'empreendimento': emp.nome,
        'area_coberta': u.area_coberta, 'area_descoberta': u.area_descoberta,
        'area_total': u.area_total, 'preco_m2': u.preco_m2,
        'coef_area_descoberta': u.coef_area_descoberta,
        'valor_total': round(u.valor_total, 2), 'status': u.status,
        'taxa_desconto_mensal': emp.taxa_desconto_mensal,
    })


@api_bp.route('/empreendimentos/<int:id>/plano-padrao')
@login_required
def api_plano_padrao(id):
    plano = PlanoPadrao.query.filter_by(empreendimento_id=id).first()
    if not plano:
        return jsonify({'error': 'Plano nao encontrado'}), 404
    return jsonify({
        'sinal_qtd': plano.sinal_qtd, 'sinal_pct': plano.sinal_pct,
        'mensal_qtd': plano.mensal_qtd, 'mensal_pct': plano.mensal_pct,
        'intermediaria_qtd': plano.intermediaria_qtd,
        'intermediaria_pct': plano.intermediaria_pct,
        'intermediaria_periodicidade': plano.intermediaria_periodicidade,
        'chave_pct': plano.chave_pct, 'financiamento_pct': plano.financiamento_pct,
    })


@api_bp.route('/calcular-vp', methods=['POST'])
@login_required
def api_calcular_vp():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Dados invalidos'}), 400

    unidade_id = data.get('unidade_id')
    empreendimento_id = data.get('empreendimento_id')

    unidade = db.session.get(Unidade, unidade_id)
    emp = db.session.get(Empreendimento, empreendimento_id)
    plano_padrao = PlanoPadrao.query.filter_by(empreendimento_id=empreendimento_id).first()

    if not all([unidade, emp, plano_padrao]):
        return jsonify({'error': 'Dados incompletos'}), 400

    proposta = {
        'sinal_qtd': data.get('sinal_qtd', 0),
        'sinal_valor': data.get('sinal_valor', 0),
        'sinal_data_inicio': data.get('sinal_data_inicio'),
        'mensal_qtd': data.get('mensal_qtd', 0),
        'mensal_valor': data.get('mensal_valor', 0),
        'mensal_data_inicio': data.get('mensal_data_inicio'),
        'intermediaria_qtd': data.get('intermediaria_qtd', 0),
        'intermediaria_valor': data.get('intermediaria_valor', 0),
        'intermediaria_data_inicio': data.get('intermediaria_data_inicio'),
        'intermediaria_periodicidade': data.get('intermediaria_periodicidade', 'S'),
        'chave_valor': data.get('chave_valor', 0),
        'chave_data': data.get('chave_data'),
        'financiamento_valor': data.get('financiamento_valor', 0),
        'financiamento_data': data.get('financiamento_data'),
    }

    resultado = comparar_proposta_vs_tabela(
        proposta, plano_padrao, unidade.valor_total,
        emp.taxa_desconto_mensal, date.today()
    )

    return jsonify(resultado)


@api_bp.route('/empreendimentos/<int:id>/regras')
@login_required
def api_regras(id):
    regras = RegrasEmpreendimento.query.filter_by(empreendimento_id=id).first()
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
