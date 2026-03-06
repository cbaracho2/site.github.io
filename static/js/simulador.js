/* ═══════════════════════════════════════════
   SimulaIMOB - Simulador Logic
   ═══════════════════════════════════════════ */

let currentUnit = null;

// ── CASCADING SELECTS ────────────────────────

const selEmp = document.getElementById('selEmpreendimento');
const selBloco = document.getElementById('selBloco');
const selUnidade = document.getElementById('selUnidade');

if (selEmp) {
    selEmp.addEventListener('change', () => {
        const empId = selEmp.value;
        document.getElementById('empreendimento_id').value = empId;
        if (empId) {
            loadBlocos(empId);
        } else {
            selBloco.innerHTML = '<option value="">Selecione empreendimento</option>';
            selUnidade.innerHTML = '<option value="">Selecione bloco</option>';
            hideUnitCard();
        }
    });

    selBloco.addEventListener('change', () => {
        const blocoId = selBloco.value;
        if (blocoId) {
            loadUnidades(blocoId);
        } else {
            selUnidade.innerHTML = '<option value="">Selecione bloco</option>';
            hideUnitCard();
        }
    });

    selUnidade.addEventListener('change', () => {
        const unidadeId = selUnidade.value;
        document.getElementById('unidade_id').value = unidadeId;
        if (unidadeId) {
            loadUnidadeDetail(unidadeId);
        } else {
            hideUnitCard();
        }
    });
}

async function loadBlocos(empId, preselect) {
    selBloco.innerHTML = '<option value="">Carregando...</option>';
    selUnidade.innerHTML = '<option value="">Selecione bloco</option>';
    hideUnitCard();
    try {
        const data = await fetchAPI('/api/empreendimentos/' + empId + '/blocos');
        selBloco.innerHTML = '<option value="">Selecione...</option>';
        data.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            opt.textContent = b.nome;
            if (preselect && String(b.id) === String(preselect)) opt.selected = true;
            selBloco.appendChild(opt);
        });
    } catch (e) {
        selBloco.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function loadUnidades(blocoId, preselect) {
    selUnidade.innerHTML = '<option value="">Carregando...</option>';
    hideUnitCard();
    try {
        const data = await fetchAPI('/api/blocos/' + blocoId + '/unidades');
        selUnidade.innerHTML = '<option value="">Selecione...</option>';
        data.forEach(u => {
            const opt = document.createElement('option');
            opt.value = u.id;
            opt.textContent = `${u.numero} - ${u.descricao || ''} (${u.status})`;
            if (preselect && String(u.id) === String(preselect)) opt.selected = true;
            selUnidade.appendChild(opt);
        });
    } catch (e) {
        selUnidade.innerHTML = '<option value="">Erro ao carregar</option>';
    }
}

async function loadUnidadeDetail(unidadeId) {
    try {
        const data = await fetchAPI('/api/unidades/' + unidadeId);
        currentUnit = data;
        showUnitCard(data);
        showStickyTotal();
        updateNominalTotal();
    } catch (e) {
        hideUnitCard();
    }
}

function showUnitCard(u) {
    const card = document.getElementById('unitCard');
    card.classList.remove('hidden');
    document.getElementById('unitTitle').textContent = `${u.empreendimento} - ${u.bloco} - Unidade ${u.numero}`;
    document.getElementById('unitAreaCob').textContent = u.area_coberta.toFixed(2) + ' m\u00B2';
    document.getElementById('unitAreaDesc').textContent = u.area_descoberta.toFixed(2) + ' m\u00B2';
    document.getElementById('unitPrecoM2').textContent = formatBRL(u.preco_m2);
    document.getElementById('unitCoef').textContent = u.coef_area_descoberta;
    document.getElementById('unitValorTotal').textContent = formatBRL(u.valor_total);
}

function hideUnitCard() {
    document.getElementById('unitCard').classList.add('hidden');
    currentUnit = null;
    const sticky = document.getElementById('stickyTotal');
    if (sticky) sticky.style.display = 'none';
}

function showStickyTotal() {
    const sticky = document.getElementById('stickyTotal');
    if (sticky && currentUnit) {
        sticky.style.display = 'flex';
        document.getElementById('stickyUnitValue').textContent = formatBRL(currentUnit.valor_total);
    }
}

// ── REAL-TIME NOMINAL TOTAL ──────────────────

function getFormValue(name) {
    const el = document.querySelector(`[name="${name}"]`);
    return el ? (parseFloat(el.value) || 0) : 0;
}

function updateNominalTotal() {
    const sinal = getFormValue('sinal_qtd') * getFormValue('sinal_valor');
    const mensal = getFormValue('mensal_qtd') * getFormValue('mensal_valor');
    const inter = getFormValue('intermediaria_qtd') * getFormValue('intermediaria_valor');
    const chave = getFormValue('chave_valor');
    const financ = getFormValue('financiamento_valor');
    const total = sinal + mensal + inter + chave + financ;

    document.getElementById('stickyTotalValue').textContent = formatBRL(total);
}

// Listen to all plan inputs
document.querySelectorAll('.plan-input').forEach(input => {
    input.addEventListener('input', debounce(updateNominalTotal, 200));
});

// ── VP CALCULATION ───────────────────────────

const btnCalcular = document.getElementById('btnCalcular');
if (btnCalcular) {
    btnCalcular.addEventListener('click', async () => {
        if (!currentUnit) {
            alert('Selecione uma unidade primeiro.');
            return;
        }

        btnCalcular.disabled = true;
        btnCalcular.textContent = 'Calculando...';

        const payload = {
            unidade_id: parseInt(document.getElementById('unidade_id').value),
            empreendimento_id: parseInt(document.getElementById('empreendimento_id').value),
            sinal_qtd: getFormValue('sinal_qtd'),
            sinal_valor: getFormValue('sinal_valor'),
            sinal_data_inicio: document.querySelector('[name="sinal_data_inicio"]').value || null,
            mensal_qtd: getFormValue('mensal_qtd'),
            mensal_valor: getFormValue('mensal_valor'),
            mensal_data_inicio: document.querySelector('[name="mensal_data_inicio"]').value || null,
            intermediaria_qtd: getFormValue('intermediaria_qtd'),
            intermediaria_valor: getFormValue('intermediaria_valor'),
            intermediaria_data_inicio: document.querySelector('[name="intermediaria_data_inicio"]').value || null,
            intermediaria_periodicidade: document.querySelector('[name="intermediaria_periodicidade"]').value,
            chave_valor: getFormValue('chave_valor'),
            chave_data: document.querySelector('[name="chave_data"]').value || null,
            financiamento_valor: getFormValue('financiamento_valor'),
            financiamento_data: document.querySelector('[name="financiamento_data"]').value || null,
        };

        try {
            const result = await fetchAPI('/api/calcular-vp', {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            showVPResult(result);
        } catch (e) {
            alert('Erro ao calcular VP: ' + e.message);
        } finally {
            btnCalcular.disabled = false;
            btnCalcular.textContent = 'Calcular VP';
        }
    });
}

function showVPResult(result) {
    const preview = document.getElementById('resultPreview');
    preview.classList.remove('hidden');

    const comp = result.comparativo;
    document.getElementById('vpNomTabela').textContent = formatBRL(comp.nominal_tabela);
    document.getElementById('vpNomProposta').textContent = formatBRL(comp.nominal_proposta);
    document.getElementById('vpTabela').textContent = formatBRL(comp.vp_tabela);
    document.getElementById('vpProposta').textContent = formatBRL(comp.vp_proposta);
    document.getElementById('vpDifTabela').textContent = formatPct(comp.dif_pct_tabela);
    document.getElementById('vpDifProposta').textContent = formatPct(comp.dif_pct_proposta);

    // Scroll to result
    preview.scrollIntoView({ behavior: 'smooth', block: 'center' });
}
