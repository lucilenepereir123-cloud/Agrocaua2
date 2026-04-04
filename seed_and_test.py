#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║           AgroCaua — Seed & Test  (v2 — corrigido)                         ║
║                                                                              ║
║  O que faz:                                                                  ║
║  1.  Login como superadmin                                                   ║
║  2.  Descobre TODAS as fazendas + sensores já existentes                     ║
║  3.  Para fazendas SEM sensor → cria sensor automaticamente                 ║
║  4.  Envia 15 leituras IoT para CADA sensor de CADA fazenda                 ║
║  5.  Dispara ML (analisar + alertas + previsões)                             ║
║  6.  Cria zonas de cultivo em todas as fazendas activas                      ║
║  7.  Cria mensagem de apoio                                                  ║
║  8.  Imprime resumo com todos os URLs dos dashboards                         ║
║                                                                              ║
║  Pode ser executado várias vezes — reaproveita sensores existentes.          ║
║                                                                              ║
║  Uso:  python seed_and_test.py                                               ║
║        python seed_and_test.py --url http://meu-servidor:5000                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import sys
import time
import argparse
import requests

# ─────────────────────────────────────────────────────────────
# Configuração
# ─────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="AgroCaua — Seed & Test v2")
parser.add_argument("--url",   default="http://localhost:5000", help="URL base do servidor")
parser.add_argument("--delay", type=float, default=0.2,         help="Delay (s) entre requisições")
args = parser.parse_args()

BASE  = args.url.rstrip("/")
DELAY = args.delay

# ─────────────────────────────────────────────────────────────
# Cores e contadores
# ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"
_ok = _fail = _skip = 0

def ok(msg):
    global _ok;   _ok   += 1; print(f"{GREEN}✓{RESET} {msg}")
def fail(msg):
    global _fail; _fail += 1; print(f"{RED}✗{RESET} {msg}")
def warn(msg):
    global _skip; _skip += 1; print(f"{YELLOW}!{RESET} {msg}")
def info(msg):  print(f"{CYAN}→{RESET} {msg}")
def section(t): print(f"\n{BOLD}{CYAN}{'─'*62}\n  {t}\n{'─'*62}{RESET}")


# ─────────────────────────────────────────────────────────────
# Helpers HTTP
# ─────────────────────────────────────────────────────────────
def post(path, data, token=None, label=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.post(f"{BASE}{path}", json=data, headers=headers, timeout=20)
        time.sleep(DELAY)
        if r.status_code in (200, 201):
            ok(f"{label or path}  [{r.status_code}]")
            return r.json() if r.content else {}
        body = r.text[:140].replace("\n", " ")
        fail(f"{label or path}  [{r.status_code}] {body}")
        return None
    except Exception as e:
        fail(f"{label or path}  Erro: {e}")
        return None

def get(path, token=None, label="", params=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get(f"{BASE}{path}", headers=headers, params=params, timeout=20)
        time.sleep(DELAY)
        if r.status_code == 200:
            ok(f"{label or path}  [{r.status_code}]")
            return r.json() if r.content else {}
        fail(f"{label or path}  [{r.status_code}] {r.text[:140]}")
        return None
    except Exception as e:
        fail(f"{label or path}  Erro: {e}")
        return None

def put(path, data, token=None, label=""):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.put(f"{BASE}{path}", json=data, headers=headers, timeout=20)
        time.sleep(DELAY)
        if r.status_code == 200:
            ok(f"{label or path}  [{r.status_code}]")
            return r.json() if r.content else {}
        body = r.text[:140].replace("\n", " ")
        fail(f"{label or path}  [{r.status_code}] {body}")
        return None
    except Exception as e:
        fail(f"{label or path}  Erro: {e}")
        return None

def login_user(email, password, label=""):
    """Faz login e devolve o token. A API devolve 'token' (não 'access_token')."""
    r = post("/api/login", {"email": email, "password": password}, label=label or f"Login {email}")
    if r:
        t = r.get("token") or r.get("access_token")
        if t:
            return t
    return None


# ─────────────────────────────────────────────────────────────
# 15 leituras IoT variadas para um device_id
# ─────────────────────────────────────────────────────────────
def leituras_para(device_id, lat=-8.8383, lon=13.2344, local="Luanda, Angola"):
    return [
        # 1-3  condições normais
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=26.5, humidade_ar=72.0, pressao_ar=1013.2,
             humidade_solo=48.0, vibracao=False, detecao_praga=False),
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=27.1, humidade_ar=70.5, pressao_ar=1012.8,
             humidade_solo=46.5, vibracao=False, detecao_praga=False),
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=25.8, humidade_ar=75.0, pressao_ar=1013.5,
             humidade_solo=50.0, vibracao=False, detecao_praga=False),
        # 4-5  subida de temperatura
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=31.0, humidade_ar=62.0, pressao_ar=1010.5,
             humidade_solo=38.0, vibracao=False, detecao_praga=False),
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=33.2, humidade_ar=57.0, pressao_ar=1009.8,
             humidade_solo=30.5, vibracao=False, detecao_praga=False),
        # 6   stress hídrico — solo seco (gera alerta)
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=34.5, humidade_ar=54.0, pressao_ar=1009.0,
             humidade_solo=16.8, vibracao=False, detecao_praga=False),
        # 7   PRAGA lagarta — alerta crítico
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=34.1, humidade_ar=58.0, pressao_ar=1008.5,
             humidade_solo=17.2, vibracao=True,
             detecao_praga=True, tipo_praga="lagarta", confianca=0.87),
        # 8   PRAGA afídeo
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=29.5, humidade_ar=66.0, pressao_ar=1010.0,
             humidade_solo=30.0, vibracao=True,
             detecao_praga=True, tipo_praga="afideo", confianca=0.76),
        # 9   recuperação após irrigação
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=28.0, humidade_ar=74.0, pressao_ar=1013.5,
             humidade_solo=52.0, vibracao=False, detecao_praga=False),
        # 10  chuva intensa — solo encharcado (gera alerta)
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=22.5, humidade_ar=93.0, pressao_ar=1006.5,
             humidade_solo=82.0, vibracao=False, detecao_praga=False),
        # 11  vibração sem praga (vento)
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=30.2, humidade_ar=60.0, pressao_ar=1011.0,
             humidade_solo=35.0, vibracao=True, detecao_praga=False),
        # 12  noite — temperatura baixa
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=19.2, humidade_ar=86.0, pressao_ar=1015.0,
             humidade_solo=55.0, vibracao=False, detecao_praga=False),
        # 13  manhã — estável
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=24.0, humidade_ar=76.0, pressao_ar=1013.0,
             humidade_solo=50.0, vibracao=False, detecao_praga=False),
        # 14  temperatura acima do limite >35°C (gera alerta)
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=36.8, humidade_ar=48.0, pressao_ar=1007.0,
             humidade_solo=14.0, vibracao=False, detecao_praga=False),
        # 15  leitura final estável
        dict(device_id=device_id, latitude=lat, longitude=lon, localizacao=local,
             temperatura_ar=28.5, humidade_ar=72.3, pressao_ar=1013.2,
             humidade_solo=45.8, vibracao=False, detecao_praga=False),
    ]


CULTURAS_PADRAO = ["milho", "feijao", "mandioca"]

ZONAS_TEMPLATE = [
    {"nome": "Zona Norte",   "cultura": "milho",    "tipo": "campo_aberto",
     "area_ha": 5.2, "estagio": "crescimento",   "saude": "boa",     "acoes": "Irrigação prevista amanhã"},
    {"nome": "Zona Sul",     "cultura": "mandioca", "tipo": "campo_aberto",
     "area_ha": 3.8, "estagio": "tuberizacao",   "saude": "atenção", "acoes": "Verificar sinais de praga"},
    {"nome": "Parcela Leste","cultura": "feijao",   "tipo": "campo_aberto",
     "area_ha": 2.1, "estagio": "florescimento", "saude": "boa",     "acoes": "Monitorar polinização"},
]

COORDS = {
    1: (-8.8383, 13.2344, "Luanda, Angola"),
    2: (-8.8391, 13.2355, "Luanda Norte, Angola"),
    3: (-8.8400, 13.2360, "Luanda Sul, Angola"),
}
DEFAULT_COORDS = (-8.8383, 13.2344, "Luanda, Angola")


# ════════════════════════════════════════════════════════════════
# 0. VERIFICAR SERVIDOR
# ════════════════════════════════════════════════════════════════
section("0. VERIFICAR SERVIDOR")
info(f"A ligar a {BASE} …")
try:
    r = requests.get(BASE, timeout=8)
    ok(f"Servidor respondeu  [{r.status_code}]")
except Exception as e:
    fail(f"Servidor não acessível: {e}")
    print(f"\n{RED}  Certifica-te de que o Flask está a correr em {BASE}{RESET}")
    print(f"  Exemplo:  python app.py   ou   flask run\n")
    sys.exit(1)


# ════════════════════════════════════════════════════════════════
# 1. LOGIN SUPERADMIN
# ════════════════════════════════════════════════════════════════
section("1. AUTENTICAÇÃO — SUPERADMIN")

# NOTA: a API devolve {"token": "..."}, não "access_token"
ADMIN_TOKEN = login_user("admin@agrocaua.com", "admin123", label="Login superadmin")
if not ADMIN_TOKEN:
    fail("Não foi possível obter token de admin. A parar.")
    sys.exit(1)
ok(f"Token admin: {ADMIN_TOKEN[:24]}…")


# ════════════════════════════════════════════════════════════════
# 2. DESCOBRIR FAZENDAS E SENSORES EXISTENTES
# ════════════════════════════════════════════════════════════════
section("2. DESCOBRIR FAZENDAS E SENSORES EXISTENTES")

resp_faz = get("/api/admin/fazendas", token=ADMIN_TOKEN, label="Listar fazendas")
resp_sen = get("/api/admin/sensores", token=ADMIN_TOKEN, label="Listar sensores")
resp_usr = get("/api/admin/users",    token=ADMIN_TOKEN, label="Listar utilizadores")

fazendas_raw = resp_faz if isinstance(resp_faz, list) else (resp_faz or {}).get("fazendas", [])
sensores_raw = resp_sen if isinstance(resp_sen, list) else (resp_sen or {}).get("sensores", [])
users_raw    = resp_usr if isinstance(resp_usr, list) else (resp_usr or {}).get("users", [])

info(f"Fazendas: {len(fazendas_raw)}  |  Sensores: {len(sensores_raw)}  |  Users: {len(users_raw)}")

# Índice: fazenda_id → lista de nomes de sensores
sensores_por_fazenda: dict = {}
for s in sensores_raw:
    fid = s.get("fazenda_id")
    if fid:
        sensores_por_fazenda.setdefault(fid, []).append(s["nome"])

# Índice: fazenda_id → primeiro agricultor activo
farmer_email_por_fazenda: dict = {}
for u in users_raw:
    fid = u.get("fazenda_id")
    if fid and u.get("role") == "agricultor" and u.get("is_active"):
        if fid not in farmer_email_por_fazenda:
            farmer_email_por_fazenda[fid] = u["email"]


# ════════════════════════════════════════════════════════════════
# 3. GARANTIR SENSOR EM CADA FAZENDA ACTIVA
# ════════════════════════════════════════════════════════════════
section("3. GARANTIR SENSOR EM CADA FAZENDA ACTIVA")

fazendas_ativas = [f for f in fazendas_raw if f.get("status") == "active"]

for faz in fazendas_ativas:
    fid   = faz["id"]
    fname = faz.get("nome", f"fazenda-{fid}")

    if fid in sensores_por_fazenda:
        info(f"Fazenda #{fid} '{fname}'  →  sensores já existem: {sensores_por_fazenda[fid]}")
        continue

    # Criar sensor para esta fazenda
    device_name = f"sensor-faz{fid}"
    res = post("/api/admin/sensores",
               {"nome": device_name, "tipo": "Clima", "fazenda_id": fid,
                "status": "online", "bateria": 95},
               token=ADMIN_TOKEN,
               label=f"Criar sensor '{device_name}' → fazenda #{fid} '{fname}'")
    if res:
        sensores_por_fazenda[fid] = [device_name]

# Garantir culturas em fazendas que não têm
for faz in fazendas_ativas:
    fid = faz["id"]
    culturas = faz.get("culturas") or []
    if not culturas:
        put(f"/api/admin/fazendas/{fid}",
            {"culturas": CULTURAS_PADRAO},
            token=ADMIN_TOKEN,
            label=f"Actualizar culturas fazenda #{fid}")
        faz["culturas"] = CULTURAS_PADRAO  # actualizar local para usar abaixo


# ════════════════════════════════════════════════════════════════
# 4. ENVIAR DADOS IoT — 15 LEITURAS × SENSOR × FAZENDA
# ════════════════════════════════════════════════════════════════
section("4. ENVIAR DADOS IoT  (15 leituras × sensor × fazenda)")

for faz in fazendas_ativas:
    fid    = faz["id"]
    fname  = faz.get("nome", f"fazenda-{fid}")
    devices = sensores_por_fazenda.get(fid, [])

    if not devices:
        warn(f"Fazenda #{fid} '{fname}' — sem sensores, a ignorar")
        continue

    lat, lon, local = COORDS.get(fid, DEFAULT_COORDS)
    print(f"\n  {BOLD}Fazenda #{fid} — '{fname}'{RESET}  sensores: {devices}")

    for device_id in devices:
        for i, leitura in enumerate(leituras_para(device_id, lat, lon, local), 1):
            praga = f" [PRAGA:{leitura.get('tipo_praga')}]" if leitura.get("detecao_praga") else ""
            post("/api/dados", leitura,
                 label=f"    {device_id}  #{i:02d}/15{praga}")


# ════════════════════════════════════════════════════════════════
# 5. MACHINE LEARNING — disparar para cada fazenda
# ════════════════════════════════════════════════════════════════
section("5. MACHINE LEARNING")

# Cache de tokens de agricultores
_farmer_tokens: dict = {}

def get_farmer_token(fid):
    """Devolve token do agricultor da fazenda, ou admin como fallback."""
    if fid in _farmer_tokens:
        return _farmer_tokens[fid]
    email = farmer_email_por_fazenda.get(fid)
    if email:
        t = login_user(email, "senha123", label=f"  Login agricultor {email}")
        if t:
            _farmer_tokens[fid] = t
            return t
    return ADMIN_TOKEN

for faz in fazendas_ativas:
    fid     = faz["id"]
    fname   = faz.get("nome", f"fazenda-{fid}")
    culturas = faz.get("culturas") or CULTURAS_PADRAO
    devices  = sensores_por_fazenda.get(fid, [])
    token    = get_farmer_token(fid)

    payload = {
        "fazenda_id":   fid,
        "culturas":     culturas,
        # dados de stress para recomendações mais ricas
        "dados_sensor": {
            "temperatura_ar": 34.1, "humidade_ar": 58.0,
            "pressao_ar": 1008.5,   "humidade_solo": 17.2,
            "vibracao": True
        }
    }
    if devices:
        payload["device_id"] = devices[0]

    post("/api/ml/analisar", payload, token=token,
         label=f"ML analisar fazenda #{fid} '{fname}'")

# Endpoints ML globais (sem token necessário)
get("/api/ml/alertas",         label="ML alertas globais")
get("/api/previsoes/recentes", label="ML previsões recentes")


# ════════════════════════════════════════════════════════════════
# 6. ZONAS DE CULTIVO
# ════════════════════════════════════════════════════════════════
section("6. ZONAS DE CULTIVO")

for faz in fazendas_ativas:
    fid   = faz["id"]
    fname = faz.get("nome", f"fazenda-{fid}")
    token = get_farmer_token(fid)
    print(f"\n  {BOLD}Fazenda #{fid} — '{fname}'{RESET}")
    for z in ZONAS_TEMPLATE:
        post("/api/zones", z, token=token,
             label=f"    Zona '{z['nome']}'")


# ════════════════════════════════════════════════════════════════
# 7. MENSAGEM DE APOIO
# ════════════════════════════════════════════════════════════════
section("7. MENSAGEM DE APOIO")

# Usar o token do agricultor da primeira fazenda activa com agricultor
farmer_token_msg = ADMIN_TOKEN
for faz in fazendas_ativas:
    t = get_farmer_token(faz["id"])
    if t != ADMIN_TOKEN:
        farmer_token_msg = t
        break

resp_msg = post("/api/admin/mensagens",
    {"assunto":    "Sensor offline há 2 dias",
     "conteudo":   "O sensor não envia dados desde segunda-feira. Já verifiquei a alimentação.",
     "prioridade": "alto"},
    token=farmer_token_msg,
    label="Agricultor envia mensagem de apoio")

# Admin responde à última mensagem
msgs = get("/api/admin/mensagens", token=ADMIN_TOKEN, label="Listar mensagens (buscar ID)")
if msgs:
    lista_m = msgs if isinstance(msgs, list) else msgs.get("mensagens", [])
    if lista_m:
        mid = lista_m[-1].get("id", 1)
        put(f"/api/admin/mensagens/{mid}/responder",
            {"resposta": "Verificámos o sensor — equipa técnica em deslocação amanhã."},
            token=ADMIN_TOKEN, label=f"Admin responde mensagem #{mid}")
        put(f"/api/admin/mensagens/{mid}/ler", {},
            token=ADMIN_TOKEN, label=f"Admin marca mensagem #{mid} como lida")


# ════════════════════════════════════════════════════════════════
# 8. VERIFICAÇÃO FINAL
# ════════════════════════════════════════════════════════════════
section("8. VERIFICAÇÃO FINAL DOS ENDPOINTS")
get("/api/alertas",         label="Alertas activos")
get("/api/bme280",          label="BME280 (temperatura/humidade/pressão)")
get("/api/solo",            label="Solo — último valor")
get("/api/gps",             label="GPS — última posição")
get("/api/vibracao",        label="Vibração — último estado")
get("/api/visao",           label="Visão — última detecção")
get("/api/admin/stats",     token=ADMIN_TOKEN, label="Estatísticas admin")


# ════════════════════════════════════════════════════════════════
# RESUMO FINAL
# ════════════════════════════════════════════════════════════════
total_leituras = sum(
    15 * len(sensores_por_fazenda.get(f["id"], []))
    for f in fazendas_ativas
)

print(f"\n{BOLD}{'═'*62}{RESET}")
print(f"{BOLD}  RESUMO FINAL{RESET}")
print(f"{BOLD}{'═'*62}{RESET}")
print(f"  {GREEN}✓ Sucesso : {_ok}{RESET}")
print(f"  {YELLOW}! Avisos  : {_skip}{RESET}")
print(f"  {RED}✗ Falhas  : {_fail}{RESET}")
print(f"  {CYAN}Leituras IoT enviadas: ~{total_leituras}{RESET}")

print(f"\n{BOLD}{CYAN}  Fazendas populadas:{RESET}")
for faz in fazendas_ativas:
    fid     = faz["id"]
    devices = sensores_por_fazenda.get(fid, [])
    n       = 15 * len(devices)
    email   = farmer_email_por_fazenda.get(fid, "(sem agricultor)")
    print(f"   #{fid:2d}  {faz.get('nome','?'):<22}  {email:<30}  {n} leituras  {devices}")

print(f"\n{BOLD}{CYAN}  Dashboards:{RESET}")
pages = [
    ("/dashboard",            "Dashboard principal"),
    ("/dashboard/sensores",   "Sensores IoT"),
    ("/dashboard/solo",       "Solo"),
    ("/dashboard/clima",      "Clima"),
    ("/dashboard/agronomia",  "Agronomia + ML"),
    ("/dashboard/alertas",    "Alertas"),
    ("/dashboard/culturas",   "Culturas / Zonas"),
    ("/dashboard/relatorios", "Relatórios"),
    ("/dashboard/gps",        "GPS"),
    ("/dashboard/visao",      "Visão"),
    ("/dashboard/apoio",      "Apoio"),
    ("/admin",                "Painel Superadmin"),
]
for path, nome in pages:
    print(f"   {CYAN}→{RESET}  {BASE}{path:<32} {nome}")

print(f"\n  {BOLD}Credenciais superadmin:{RESET}  admin@agrocaua.com  /  admin123")
print(f"  {BOLD}Credenciais agricultores:{RESET}")
farmer_emails_shown = set()
for faz in fazendas_ativas:
    e = farmer_email_por_fazenda.get(faz["id"])
    if e and e not in farmer_emails_shown:
        print(f"    {e}  /  senha123  (fazenda #{faz['id']} — {faz.get('nome','?')})")
        farmer_emails_shown.add(e)

if _fail > 3:
    print(f"\n  {YELLOW}Dica:{RESET} Se muitas falhas, verifica que Flask está a correr")
    print(f"  e que a pasta ML/ está no directório do projecto.")

print(f"\n{BOLD}  Pronto! Abre {BASE}/login e entra com qualquer conta acima.{RESET}\n")