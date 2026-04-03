/**
 * AgroCaua — Recomendações UI v3.0
 * Shared renderer for ML recommendation cards across all pages.
 *
 * Usage:
 *   RecUI.renderBanner(nivelGeral, resumo, numAlertas, bannerId, badgeId, subtitleId?)
 *   RecUI.renderLista(recs, containerId, onRetryFn?)
 *   RecUI.renderInline(rec, containerId)
 *   RecUI.setLoading(containerId)
 *   RecUI.setError(containerId, msg, onRetryFn)
 */

const RecUI = (() => {

  // ── Configurações de nível geral ──────────────────────────
  const NIVEL_CFG = {
    seguro:  { cls: 'nivel-seguro',  icon: '✅', label: 'Sistema em Condições Normais',      badgeCls: 'seguro' },
    atencao: { cls: 'nivel-atencao', icon: '⚠️', label: 'Atenção — Monitorar Condições',     badgeCls: 'atencao' },
    alerta:  { cls: 'nivel-alerta',  icon: '🔶', label: 'Alerta — Acção Recomendada',        badgeCls: 'alerta' },
    critico: { cls: 'nivel-critico', icon: '🚨', label: 'CRÍTICO — Acção Urgente Necessária', badgeCls: 'critico' },
  };

  // ── Configurações de urgência ──────────────────────────────
  const URG_CFG = {
    URGENTE: { cls: 'urg-urgente', pillCls: 'urgente', icon: '🚨' },
    ALTA:    { cls: 'urg-alta',    pillCls: 'alta',    icon: '🔴' },
    MEDIA:   { cls: 'urg-media',   pillCls: 'media',   icon: '🟡' },
    BAIXA:   { cls: 'urg-baixa',   pillCls: 'baixa',   icon: '🟢' },
  };

  // ── Ícones por categoria ───────────────────────────────────
  const CAT_ICON = {
    'Gestão de Água':        '💧',
    'Água':                  '💧',
    'Segurança — Incêndio':  '🔥',
    'Incêndio':              '🔥',
    'Praga':                 '🐛',
    'Proteção de Culturas':  '🌿',
    'Saúde do Solo':         '🌱',
    'Solo':                  '🌱',
    'Condições Meteorológicas': '⛅',
    'Previsão Climática':    '🔭',
    'Colheita do Cafe':      '☕',
    'Colheita':              '🌾',
    'Fertilidade':           '🧪',
    'Irrigação':             '💦',
  };

  function getCatIcon(categoria) {
    if (!categoria) return '📋';
    for (const [key, icon] of Object.entries(CAT_ICON)) {
      if (categoria.includes(key)) return icon;
    }
    return '📋';
  }

  function _el(id) { return document.getElementById(id); }

  // ── Render Banner ──────────────────────────────────────────
  function renderBanner(nivel, resumo, numAlertas, bannerId, badgeId, subtitleId) {
    const cfg = NIVEL_CFG[nivel] || NIVEL_CFG.seguro;
    const banner = _el(bannerId);
    if (banner) {
      // Remove all nivel classes and apply the right one
      banner.classList.remove('nivel-seguro', 'nivel-atencao', 'nivel-alerta', 'nivel-critico');
      banner.classList.add(cfg.cls);

      // Update icon if exists
      const iconEl = banner.querySelector('[data-rec-icon]');
      if (iconEl) iconEl.textContent = cfg.icon;

      // Update title if exists
      const titleEl = banner.querySelector('[data-rec-title]');
      if (titleEl) titleEl.textContent = cfg.label;

      // Update subtitle
      const subEl = subtitleId ? _el(subtitleId) : banner.querySelector('[data-rec-subtitle]');
      if (subEl) subEl.textContent = resumo || 'Análise ML concluída.';
    }

    // Badge
    const badge = _el(badgeId);
    if (badge) {
      const count = numAlertas || 0;
      badge.className = `rec-nivel-badge ${cfg.badgeCls}`;
      badge.textContent = count > 0
        ? `${count} alerta${count !== 1 ? 's' : ''}`
        : cfg.badgeCls.charAt(0).toUpperCase() + cfg.badgeCls.slice(1);
      badge.classList.remove('hidden');
    }
  }

  // ── Render Lista de cards ──────────────────────────────────
  function renderLista(recs, containerId, onRetryFn) {
    const lista = _el(containerId);
    if (!lista) return;

    if (!recs || !recs.length) {
      lista.innerHTML = `
        <div class="rec-empty">
          <div class="rec-empty-icon">✅</div>
          <p class="rec-empty-title">Sem recomendações pendentes</p>
          <p class="rec-empty-sub">O modelo ML não identificou situações que requeiram ação imediata. Todas as condições estão dentro dos parâmetros normais.</p>
        </div>`;
      return;
    }

    lista.innerHTML = recs.map((r, idx) => {
      const urg  = URG_CFG[r.urgencia] || URG_CFG.BAIXA;
      const icon = getCatIcon(r.categoria);
      const pct  = r.score != null ? Math.round(r.score * 100) : null;
      const delay = idx * 0.05;
      return `
        <div class="rec-card ${urg.cls}" style="animation-delay:${delay}s">
          <div class="rec-card-header">
            <div class="rec-card-meta">
              <div class="rec-cat-icon">${icon}</div>
              <div class="rec-cat-info">
                <div class="rec-cat-name">${r.categoria || '—'}</div>
                <div class="rec-urg-label">${r.urgencia === 'URGENTE' ? '🚨 ' : ''}${
                  r.urgencia === 'URGENTE' ? 'Urgente' :
                  r.urgencia === 'ALTA'    ? 'Alta Prioridade' :
                  r.urgencia === 'MEDIA'   ? 'Prioridade Média' : 'Baixa Prioridade'
                }</div>
              </div>
            </div>
            <span class="rec-urg-pill ${urg.pillCls}">${r.urgencia}</span>
          </div>
          <p class="rec-accao">${r.accao || '—'}</p>
          ${pct != null ? `
          <div class="rec-score-section">
            <div class="rec-score-label">
              <span>Nível de risco</span>
              <span>${pct}%</span>
            </div>
            <div class="rec-score-track">
              <div class="rec-score-fill" style="width:0%" data-target="${pct}"></div>
            </div>
          </div>` : ''}
        </div>`;
    }).join('');

    // Animate score bars after render
    requestAnimationFrame(() => {
      lista.querySelectorAll('.rec-score-fill[data-target]').forEach(bar => {
        const target = bar.getAttribute('data-target');
        setTimeout(() => { bar.style.width = target + '%'; }, 100);
      });
    });
  }

  // ── Render inline (single rec, for Clima/Solo/Visao) ──────
  function renderInline(rec, containerId) {
    const el = _el(containerId);
    if (!el || !rec) return;
    const urg  = URG_CFG[rec.urgencia] || URG_CFG.BAIXA;
    const icon = getCatIcon(rec.categoria);
    el.className = `rec-inline ${urg.cls}`;
    el.innerHTML = `
      <span class="rec-inline-icon">${icon}</span>
      <div class="rec-inline-body">
        <div class="rec-inline-cat">${rec.categoria || '—'}
          <span class="rec-urg-pill ${urg.pillCls}" style="margin-left:0.4rem">${rec.urgencia}</span>
        </div>
        <p class="rec-inline-text">${rec.accao || '—'}</p>
      </div>`;
    el.classList.remove('hidden');
  }

  // ── Loading state ──────────────────────────────────────────
  function setLoading(containerId) {
    const lista = _el(containerId);
    if (!lista) return;
    lista.innerHTML = `
      <div class="rec-loading">
        <div class="rec-spinner"></div>
        <p>A consultar o modelo de Machine Learning...</p>
      </div>`;
  }

  // ── Error state ────────────────────────────────────────────
  function setError(containerId, msg, onRetryFn) {
    const lista = _el(containerId);
    if (!lista) return;
    const retryId = 'rec-retry-' + containerId;
    lista.innerHTML = `
      <div class="rec-error">
        <div class="rec-error-icon">📡</div>
        <p>Erro ao comunicar com o módulo ML${msg ? ': ' + msg : '.'}</p>
        ${onRetryFn ? `<button class="rec-error-btn" id="${retryId}">Tentar novamente</button>` : ''}
      </div>`;
    if (onRetryFn) {
      const btn = document.getElementById(retryId);
      if (btn) btn.onclick = onRetryFn;
    }
  }

  return { renderBanner, renderLista, renderInline, setLoading, setError };
})();
