/* ═══════════════════════════════════════════
   SimulaIMOB - Global Utilities
   ═══════════════════════════════════════════ */

function formatBRL(value) {
    if (value == null || isNaN(value)) return 'R$ 0,00';
    return 'R$ ' + Number(value).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

function formatPct(value) {
    if (value == null || isNaN(value)) return '0,00%';
    return Number(value).toLocaleString('pt-BR', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }) + '%';
}

function parseBRL(str) {
    if (!str) return 0;
    return parseFloat(str.replace(/[R$\s.]/g, '').replace(',', '.')) || 0;
}

function debounce(fn, delay) {
    let timer;
    return function (...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

async function fetchAPI(url, options = {}) {
    try {
        const resp = await fetch(url, {
            headers: { 'Content-Type': 'application/json', ...options.headers },
            ...options
        });
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: 'Erro no servidor' }));
            throw new Error(err.error || `HTTP ${resp.status}`);
        }
        return await resp.json();
    } catch (e) {
        console.error('API Error:', e);
        throw e;
    }
}

// Auto-dismiss flash messages
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('.alert').forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-8px)';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Tab switching
function initTabs(container) {
    const el = container || document;
    el.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const group = tab.closest('.tabs');
            const parent = group.parentElement;
            group.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            const target = tab.dataset.tab;
            parent.querySelectorAll('.tab-content').forEach(tc => tc.classList.remove('active'));
            const targetEl = parent.querySelector(`[data-tab-content="${target}"]`);
            if (targetEl) targetEl.classList.add('active');
        });
    });
}

document.addEventListener('DOMContentLoaded', () => initTabs());
