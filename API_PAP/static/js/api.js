/**
 * AgroCaua API Client — v3 (com ML integrado)
 */
const API_BASE = window.location.port === '5000'
    ? window.location.origin
    : 'http://localhost:5000';

function getToken()   { return localStorage.getItem('agrocaua_token'); }
function saveToken(t) { localStorage.setItem('agrocaua_token', t); }
function clearToken() { localStorage.removeItem('agrocaua_token'); localStorage.removeItem('agrocaua_user'); }

async function authenticatedFetch(endpoint, options = {}) {
    const token = getToken();
    const headers = { 'Content-Type': 'application/json', ...options.headers };
    if (token) headers['Authorization'] = `Bearer ${token}`;
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });
        if (response.status === 401) { clearToken(); window.location.href = '/login'; throw new Error('Authentication required'); }
        return response;
    } catch (error) { console.error('API request failed:', error); throw error; }
}

const API = {
    // ── Auth ──
    login:         (email, password) => fetch(`${API_BASE}/api/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) }),
    register:      (nome, email, password) => fetch(`${API_BASE}/api/register`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ nome, email, password }) }),
    logout:        () => authenticatedFetch('/api/logout', { method: 'POST' }),
    deleteAccount: () => authenticatedFetch('/api/delete-account', { method: 'DELETE' }),

    // ── Perfil ──
    getProfile:    () => authenticatedFetch('/api/profile'),
    updateProfile: (data) => authenticatedFetch('/api/profile', { method: 'PUT', body: JSON.stringify(data) }),

    // ── Fazenda ──
    fazenda: {
        /** Sensores registados na fazenda do agricultor autenticado */
        sensores: () => authenticatedFetch('/api/fazenda/sensores'),
        /** Perfil completo da fazenda (culturas, sensores, ML) */
        perfil:   () => authenticatedFetch('/api/fazenda/perfil'),
    },

    // ── Dados Sensor ──
    getAllData:    () => authenticatedFetch('/api/dados_sensores'),
    getGPS:       () => authenticatedFetch('/api/gps'),
    getBME280:    () => authenticatedFetch('/api/bme280'),
    getSolo:      () => authenticatedFetch('/api/solo'),
    getVibracao:  () => authenticatedFetch('/api/vibracao'),
    getVisao:     () => authenticatedFetch('/api/visao'),
    getAlertas:   () => authenticatedFetch('/api/alertas'),

    // ── ML — módulo completo ──
    ml: {
        /** Análise on-demand — envia dados opcionais, recebe previsões + recomendações */
        analisar: (dados = {}) => authenticatedFetch('/api/ml/analisar', {
            method: 'POST',
            body: JSON.stringify(dados)
        }),
        /** Alertas ML agregados + recomendações em linguagem natural */
        alertas: () => authenticatedFetch('/api/ml/alertas'),
        /** Últimas previsões guardadas na tabela previsoes */
        previsoes: (limit = 10) => authenticatedFetch(`/api/previsoes/recentes?limit=${limit}`),
    },

    // ── Zonas ──
    zones: {
        list:   (fazendaId='') => authenticatedFetch(`/api/zones${fazendaId ? `?fazenda_id=${fazendaId}` : ''}`),
        create: (d)            => authenticatedFetch('/api/zones',      { method: 'POST',   body: JSON.stringify(d) }),
        update: (id, d)        => authenticatedFetch(`/api/zones/${id}`,{ method: 'PUT',    body: JSON.stringify(d) }),
        remove: (id)           => authenticatedFetch(`/api/zones/${id}`,{ method: 'DELETE' }),
    },

    // ── Admin ──
    admin: {
        getStats:    () => authenticatedFetch('/api/admin/stats'),
        getConfig:   () => authenticatedFetch('/api/admin/configuracoes'),
        saveConfig:  (d) => authenticatedFetch('/api/admin/configuracoes', { method: 'POST', body: JSON.stringify(d) }),
        getUsers:    () => authenticatedFetch('/api/admin/users'),
        createUser:  (d)      => authenticatedFetch('/api/admin/users',       { method: 'POST',   body: JSON.stringify(d) }),
        updateUser:  (id, d)  => authenticatedFetch(`/api/admin/users/${id}`, { method: 'PUT',    body: JSON.stringify(d) }),
        deleteUser:  (id)     => authenticatedFetch(`/api/admin/users/${id}`, { method: 'DELETE' }),
        getFazendas: () => authenticatedFetch('/api/admin/fazendas'),
        createFazenda: (d)     => authenticatedFetch('/api/admin/fazendas',        { method: 'POST',   body: JSON.stringify(d) }),
        updateFazenda: (id, d) => authenticatedFetch(`/api/admin/fazendas/${id}`,  { method: 'PUT',    body: JSON.stringify(d) }),
        deleteFazenda: (id)    => authenticatedFetch(`/api/admin/fazendas/${id}`,  { method: 'DELETE' }),
        getFazendaDetalhes: (id) => authenticatedFetch(`/api/admin/fazendas/${id}/detalhes`),
        activateFarm: (id, unit_code='') => authenticatedFetch(`/api/admin/fazendas/${id}/ativar`, { method: 'POST', body: JSON.stringify({ unit_code }) }),
        getSensores:   () => authenticatedFetch('/api/admin/sensores'),
        createSensor:  (d)     => authenticatedFetch('/api/admin/sensores',       { method: 'POST',   body: JSON.stringify(d) }),
        updateSensor:  (id, d) => authenticatedFetch(`/api/admin/sensores/${id}`, { method: 'PUT',    body: JSON.stringify(d) }),
        deleteSensor:  (id)    => authenticatedFetch(`/api/admin/sensores/${id}`, { method: 'DELETE' }),
        deviceIdsDesconhecidos: () => authenticatedFetch('/api/admin/sensores/device_ids_desconhecidos'),
        criarMensagem:        (d)   => authenticatedFetch('/api/admin/mensagens',               { method: 'POST', body: JSON.stringify(d) }),
        minhasMensagens:      ()    => authenticatedFetch('/api/admin/mensagens/minhas'),
        listarMensagensAdmin: (q='')=> authenticatedFetch(`/api/admin/mensagens${q}`),
        responderMensagem:    (id, resposta) => authenticatedFetch(`/api/admin/mensagens/${id}/responder`, { method: 'PUT', body: JSON.stringify({ resposta }) }),
        marcarMensagemLida:   (id)  => authenticatedFetch(`/api/admin/mensagens/${id}/ler`, { method: 'PUT' }),
        alertasAgricultores:  ()    => authenticatedFetch('/api/admin/alertas/agricultores'),
        relatoriosDados:      (periodo=30, fazendaId='') => authenticatedFetch(`/api/admin/relatorios/dados?periodo=${periodo}${fazendaId ? `&fazenda_id=${fazendaId}` : ''}`),
        relatoriosAgricultor: (periodo='mensal') => authenticatedFetch(`/api/admin/relatorios/agricultor?periodo=${periodo}`),
        getLogs: (limit=200, offset=0) => authenticatedFetch(`/api/admin/logs?limit=${limit}&offset=${offset}`),
    }
};

function getCurrentUser() {
    try { return JSON.parse(localStorage.getItem('agrocaua_user')); } catch { return null; }
}
function hasRole(...roles) {
    const u = getCurrentUser();
    return u && roles.includes(u.role);
}
function requireSuperAdmin() {
    if (!hasRole('superadmin')) { clearToken(); window.location.href = '/admin/login'; }
}
function requireAuth() {
    if (!getToken()) window.location.href = '/login';
}