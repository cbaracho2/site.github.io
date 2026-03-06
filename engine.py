"""VP (Present Value) Calculation Engine for payment plan simulation."""

from datetime import date
from dateutil.relativedelta import relativedelta

PERIODICIDADE_MAP = {
    'M': 1,   # Mensal
    'B': 2,   # Bimestral
    'T': 3,   # Trimestral
    'S': 6,   # Semestral
    'A': 12,  # Anual
}

PERIODICIDADE_LABELS = {
    'M': 'Mensal',
    'B': 'Bimestral',
    'T': 'Trimestral',
    'S': 'Semestral',
    'A': 'Anual',
}


def gerar_datas_pagamento(data_inicio, quantidade, periodicidade='M'):
    """Generate payment dates based on start date, quantity, and periodicity."""
    if not data_inicio or quantidade <= 0:
        return []
    if isinstance(data_inicio, str):
        data_inicio = date.fromisoformat(data_inicio)
    intervalo = PERIODICIDADE_MAP.get(periodicidade, 1)
    return [data_inicio + relativedelta(months=i * intervalo) for i in range(quantidade)]


def construir_fluxo_pagamentos(plano):
    """
    Build list of {data, valor, tipo} from a payment plan dict.

    plano keys: sinal_qtd, sinal_valor, sinal_data_inicio,
                mensal_qtd, mensal_valor, mensal_data_inicio,
                intermediaria_qtd, intermediaria_valor, intermediaria_data_inicio,
                intermediaria_periodicidade,
                chave_valor, chave_data,
                financiamento_valor, financiamento_data
    """
    pagamentos = []

    # Sinal
    qtd = plano.get('sinal_qtd', 0) or 0
    valor = plano.get('sinal_valor', 0) or 0
    if qtd > 0 and valor > 0:
        datas = gerar_datas_pagamento(plano.get('sinal_data_inicio'), qtd, 'M')
        for d in datas:
            pagamentos.append({'data': d, 'valor': valor, 'tipo': 'Sinal'})

    # Mensal
    qtd = plano.get('mensal_qtd', 0) or 0
    valor = plano.get('mensal_valor', 0) or 0
    if qtd > 0 and valor > 0:
        datas = gerar_datas_pagamento(plano.get('mensal_data_inicio'), qtd, 'M')
        for d in datas:
            pagamentos.append({'data': d, 'valor': valor, 'tipo': 'Mensal'})

    # Intermediaria
    qtd = plano.get('intermediaria_qtd', 0) or 0
    valor = plano.get('intermediaria_valor', 0) or 0
    if qtd > 0 and valor > 0:
        periodicidade = plano.get('intermediaria_periodicidade', 'S')
        datas = gerar_datas_pagamento(plano.get('intermediaria_data_inicio'), qtd, periodicidade)
        for d in datas:
            pagamentos.append({'data': d, 'valor': valor, 'tipo': 'Intermediaria'})

    # Chave (single)
    valor = plano.get('chave_valor', 0) or 0
    if valor > 0:
        chave_data = plano.get('chave_data')
        if chave_data:
            if isinstance(chave_data, str):
                chave_data = date.fromisoformat(chave_data)
            pagamentos.append({'data': chave_data, 'valor': valor, 'tipo': 'Chave'})

    # Financiamento (single)
    valor = plano.get('financiamento_valor', 0) or 0
    if valor > 0:
        fin_data = plano.get('financiamento_data')
        if fin_data:
            if isinstance(fin_data, str):
                fin_data = date.fromisoformat(fin_data)
            pagamentos.append({'data': fin_data, 'valor': valor, 'tipo': 'Financiamento'})

    return sorted(pagamentos, key=lambda p: p['data'])


def calcular_vp(pagamentos, taxa_mensal, data_base=None):
    """
    Calculate Present Value of a payment schedule.
    VP = SUM(payment_i / (1 + taxa_mensal)^months_i)
    """
    if data_base is None:
        data_base = date.today()
    if isinstance(data_base, str):
        data_base = date.fromisoformat(data_base)

    detalhes = []
    vp_total = 0.0
    nominal_total = 0.0

    for pgto in pagamentos:
        d = pgto['data']
        if isinstance(d, str):
            d = date.fromisoformat(d)

        delta = relativedelta(d, data_base)
        meses = max(delta.years * 12 + delta.months, 0)

        fator = (1 + taxa_mensal) ** meses
        vp = pgto['valor'] / fator

        detalhes.append({
            'data': d.isoformat(),
            'valor': round(pgto['valor'], 2),
            'tipo': pgto['tipo'],
            'meses': meses,
            'fator': round(fator, 6),
            'vp': round(vp, 2),
        })

        vp_total += vp
        nominal_total += pgto['valor']

    dif_pct = 0.0
    if nominal_total > 0:
        dif_pct = round((vp_total - nominal_total) / nominal_total * 100, 2)

    return {
        'vp_total': round(vp_total, 2),
        'nominal_total': round(nominal_total, 2),
        'dif_pct': dif_pct,
        'detalhes': detalhes,
    }


def construir_plano_padrao_pagamentos(plano_padrao, valor_unidade, data_base=None):
    """
    Convert standard plan (percentages) into absolute payment schedule.
    """
    if data_base is None:
        data_base = date.today()
    if isinstance(data_base, str):
        data_base = date.fromisoformat(data_base)

    sinal_total = valor_unidade * (plano_padrao.sinal_pct or 0) / 100
    sinal_valor = sinal_total / max(plano_padrao.sinal_qtd or 1, 1)

    mensal_total = valor_unidade * (plano_padrao.mensal_pct or 0) / 100
    mensal_valor = mensal_total / max(plano_padrao.mensal_qtd or 1, 1)

    inter_total = valor_unidade * (plano_padrao.intermediaria_pct or 0) / 100
    inter_valor = inter_total / max(plano_padrao.intermediaria_qtd or 1, 1)

    chave_valor = valor_unidade * (plano_padrao.chave_pct or 0) / 100
    financ_valor = valor_unidade * (plano_padrao.financiamento_pct or 0) / 100

    # Estimate delivery date from mensal quantity
    mensal_qtd = plano_padrao.mensal_qtd or 24
    data_entrega = data_base + relativedelta(months=mensal_qtd + 1)

    plano_dict = {
        'sinal_qtd': plano_padrao.sinal_qtd or 0,
        'sinal_valor': sinal_valor,
        'sinal_data_inicio': data_base,
        'mensal_qtd': plano_padrao.mensal_qtd or 0,
        'mensal_valor': mensal_valor,
        'mensal_data_inicio': data_base + relativedelta(months=1),
        'intermediaria_qtd': plano_padrao.intermediaria_qtd or 0,
        'intermediaria_valor': inter_valor,
        'intermediaria_data_inicio': data_base + relativedelta(months=6),
        'intermediaria_periodicidade': plano_padrao.intermediaria_periodicidade or 'S',
        'chave_valor': chave_valor,
        'chave_data': data_entrega,
        'financiamento_valor': financ_valor,
        'financiamento_data': data_entrega,
    }

    return construir_fluxo_pagamentos(plano_dict)


def comparar_proposta_vs_tabela(proposta_dict, plano_padrao, valor_unidade, taxa_mensal, data_base=None):
    """
    Build the full comparison: tabela vs proposta.
    Returns dict with nominal, VP, and dif_pct for both sides.
    """
    if data_base is None:
        data_base = date.today()

    # Build proposta
    pgtos_proposta = construir_fluxo_pagamentos(proposta_dict)
    resultado_proposta = calcular_vp(pgtos_proposta, taxa_mensal, data_base)

    # Build tabela
    pgtos_tabela = construir_plano_padrao_pagamentos(plano_padrao, valor_unidade, data_base)
    resultado_tabela = calcular_vp(pgtos_tabela, taxa_mensal, data_base)

    return {
        'tabela': resultado_tabela,
        'proposta': resultado_proposta,
        'comparativo': {
            'nominal_tabela': resultado_tabela['nominal_total'],
            'nominal_proposta': resultado_proposta['nominal_total'],
            'vp_tabela': resultado_tabela['vp_total'],
            'vp_proposta': resultado_proposta['vp_total'],
            'dif_pct_tabela': resultado_tabela['dif_pct'],
            'dif_pct_proposta': resultado_proposta['dif_pct'],
        }
    }
