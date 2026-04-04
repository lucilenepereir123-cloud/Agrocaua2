import requests, json, time

BASE = "http://127.0.0.1:5000"

def hit(method, url, headers=None, json_body=None):
    t0 = time.perf_counter()
    try:
        if method == "GET":
            r = requests.get(url, headers=headers or {})
        elif method == "POST":
            r = requests.post(url, headers=headers or {}, json=json_body or {})
        elif method == "PUT":
            r = requests.put(url, headers=headers or {}, json=json_body or {})
        elif method == "DELETE":
            r = requests.delete(url, headers=headers or {})
        else:
            raise RuntimeError("unsupported method")
    except Exception as e:
        dt = time.perf_counter() - t0
        print(f"=== {method} {url}")
        print(f"ERROR: {e}")
        print(f"TIME_S: {dt:.3f}")
        return None, None
    dt = time.perf_counter() - t0
    print(f"=== {method} {url}")
    print(f"STATUS: {r.status_code}")
    print(f"TIME_S: {dt:.3f}")
    print("HEADERS:")
    for k,v in r.headers.items():
        print(f"{k}: {v}")
    print("BODY:")
    try:
        print(json.dumps(r.json(), ensure_ascii=False, indent=2))
    except Exception:
        print(r.text)
    print()
    return r, dt

def main():
    # 1) Public GETs before data
    hit("GET", f"{BASE}/api/gps")
    hit("GET", f"{BASE}/api/bme280")
    hit("GET", f"{BASE}/api/solo")
    hit("GET", f"{BASE}/api/vibracao")
    hit("GET", f"{BASE}/api/culturas")
    hit("GET", f"{BASE}/api/previsoes/recentes")
    hit("GET", f"{BASE}/api/dados_sensores")

    # 2) Login superadmin
    r,_ = hit("POST", f"{BASE}/api/login", json_body={"email":"admin@agrocaua.com","password":"admin123"})
    token = None
    if r is not None and r.ok:
        try:
            token = r.json().get("token")
        except Exception:
            token = None
    if token:
        auth = {"Authorization": f"Bearer {token}"}
    else:
        auth = {}
        print("WARN: no JWT token acquired; auth endpoints may fail.\n")

    # 3) Profile (auth)
    hit("GET", f"{BASE}/api/profile", headers=auth)

    # 4) Inject sample sensor data
    payload = {
        "device_id": "sensor-001",
        "gps": {"latitude": -8.12, "longitude": 39.33},
        "localizacao": {"localizacao": "Parcela A"},
        "bme280": {"temperatura": 23.4, "humidade": 61.2, "pressao": 1011.8},
        "solo": {"humidade": 45.5},
        "vibracao": {"detectada": False},
        "visao": {"detecao_praga": False, "tipo_praga": None, "confianca": None}
    }
    hit("POST", f"{BASE}/api/dados", json_body=payload)

    # 5) Public GETs after data
    hit("GET", f"{BASE}/api/dados_sensores")
    hit("GET", f"{BASE}/api/gps")
    hit("GET", f"{BASE}/api/bme280")
    hit("GET", f"{BASE}/api/solo")
    hit("GET", f"{BASE}/api/vibracao")
    hit("GET", f"{BASE}/api/culturas")
    hit("GET", f"{BASE}/api/previsoes/recentes")

    # 6) Admin endpoints (auth)
    hit("GET", f"{BASE}/api/admin/stats", headers=auth)
    hit("GET", f"{BASE}/api/admin/users", headers=auth)
    hit("GET", f"{BASE}/api/admin/fazendas", headers=auth)
    hit("GET", f"{BASE}/api/admin/sensores", headers=auth)

    # 6.1) Fazendas: criação inválida (erro 400)
    hit("POST", f"{BASE}/api/admin/fazendas", headers=auth, json_body={})
    # 6.2) Fazendas: criação válida
    rf, _ = hit("POST", f"{BASE}/api/admin/fazendas", headers=auth, json_body={
        "nome": "Fazenda QA",
        "proprietario": "Teste",
        "localizacao": "Zona QA",
        "hectares": 12.5,
        "cultura": "Milho",
        "status": "active"
    })
    fazenda_id = None
    if rf and rf.ok:
        try: fazenda_id = rf.json().get("id")
        except Exception: fazenda_id = None
    # 6.2.1) Nova fazenda NÃO ativada + agricultor associado: deve retornar relatório vazio
    rfn, _ = hit("POST", f"{BASE}/api/admin/fazendas", headers=auth, json_body={
        "nome": "Fazenda Nova",
        "proprietario": "Novo",
        "localizacao": "Zona N",
        "hectares": 5.0,
        "cultura": "Soja",
        "status": "active"
    })
    fazenda_nova_id = None
    if rfn and rfn.ok:
        try: fazenda_nova_id = rfn.json().get("id")
        except Exception: fazenda_nova_id = None
    # criar agricultor associado à fazenda nova (não ativada)
    if fazenda_nova_id:
        ru, _ = hit("POST", f"{BASE}/api/admin/users", headers=auth, json_body={
            "nome": "Agricultor Novo",
            "email": "novo_agricultor@example.com",
            "password": "senha123",
            "role": "agricultor",
            "fazenda_id": fazenda_nova_id
        })
        # login como agricultor novo
        rlogin, _ = hit("POST", f"{BASE}/api/login", json_body={"email":"novo_agricultor@example.com","password":"senha123"})
        agric_token = None
        if rlogin and rlogin.ok:
            try: agric_token = rlogin.json().get("token")
            except Exception: agric_token = None
        agric_auth = {"Authorization": f"Bearer {agric_token}"} if agric_token else {}
        if agric_auth:
            rr, _ = hit("GET", f"{BASE}/api/admin/relatorios/agricultor?periodo=mensal", headers=agric_auth)
            if rr and rr.ok:
                try:
                    data = rr.json()
                    resumo = data.get("resumo") or {}
                    graf = data.get("grafico_diario") or []
                    assert (resumo.get("total_leituras") or 0) == 0, "Conta nova deve ter total_leituras=0"
                    assert len(graf) == 0, "Conta nova deve ter grafico_diario vazio"
                except Exception as e:
                    print("Falha na validação de conta nova:", e)
    # 6.3) Fazendas: update existente
    if fazenda_id:
        hit("PUT", f"{BASE}/api/admin/fazendas/{fazenda_id}", headers=auth, json_body={
            "localizacao": "Zona QA Norte",
            "hectares": 15.0
        })
    # 6.4) Fazendas: update inexistente (404)
    hit("PUT", f"{BASE}/api/admin/fazendas/999999", headers=auth, json_body={"nome":"X"})

    # 6.5) Sensores: criação inválida (tipo inválido)
    hit("POST", f"{BASE}/api/admin/sensores", headers=auth, json_body={
        "nome": "S-INV",
        "tipo": "X"
    })
    # 6.6) Sensores: criação válida
    rs, _ = hit("POST", f"{BASE}/api/admin/sensores", headers=auth, json_body={
        "nome": "sensor-qa-1",
        "tipo": "Solo",
        "fazenda_id": fazenda_id,
        "status": "online",
        "bateria": 88
    })
    sensor_id = None
    if rs and rs.ok:
        try: sensor_id = rs.json().get("id")
        except Exception: sensor_id = None
    # 6.7) Sensores: update existente
    if sensor_id:
        hit("PUT", f"{BASE}/api/admin/sensores/{sensor_id}", headers=auth, json_body={
            "status": "warn",
            "bateria": 30
        })
    # 6.8) Sensores: update inexistente (404)
    hit("PUT", f"{BASE}/api/admin/sensores/999999", headers=auth, json_body={"status":"offline"})
    # 6.9) Sensores: delete inexistente (404)
    hit("DELETE", f"{BASE}/api/admin/sensores/999999", headers=auth)

    # 6.10) Detalhes da fazenda
    if fazenda_id:
        hit("GET", f"{BASE}/api/admin/fazendas/{fazenda_id}/detalhes", headers=auth)

    # 6.11) Relatórios BI
    hit("GET", f"{BASE}/api/admin/relatorios/dados?periodo=7", headers=auth)

    # 6.12) Sensores: delete existente
    if sensor_id:
        hit("DELETE", f"{BASE}/api/admin/sensores/{sensor_id}", headers=auth)

    # 6.13) Fazendas: delete existente
    if fazenda_id:
        hit("DELETE", f"{BASE}/api/admin/fazendas/{fazenda_id}", headers=auth)

    # 6.14) ML dedicated endpoints
    hit("POST", f"{BASE}/api/ml/analisar", json_body={
        "temperatura_ar": 24.1,
        "humidade_ar": 60.0,
        "pressao_ar": 1012.3,
        "humidade_solo": 55.0
    })
    hit("GET", f"{BASE}/api/ml/alertas")

    # 6.15) Alertas derivados e visão
    hit("GET", f"{BASE}/api/alertas")
    # Visão pode retornar 404 se não houver previsões
    hit("GET", f"{BASE}/api/visao")

    # 7) Contact form (public)
    hit("POST", f"{BASE}/api/contacto", json_body={
        "nome":"Teste QA",
        "email":"qa@example.com",
        "telefone":"",
        "assunto":"Teste",
        "mensagem":"Mensagem de teste"
    })

    # 7.1) Mensagens (agricultor autenticado via JWT)
    rm, _ = hit("POST", f"{BASE}/api/admin/mensagens", headers=auth, json_body={
        "assunto": "Ajuda urgente",
        "conteudo": "Problema no pivô",
        "prioridade": "critico"
    })
    mid = None
    if rm and rm.ok:
        try: mid = rm.json().get("id")
        except Exception: mid = None
    # 7.2) Mensagens erro (sem assunto)
    hit("POST", f"{BASE}/api/admin/mensagens", headers=auth, json_body={
        "conteudo": "Sem assunto"
    })
    # 7.3) Listar mensagens admin com filtros
    hit("GET", f"{BASE}/api/admin/mensagens?origem=&status=&prioridade=", headers=auth)
    # 7.4) Alertas de agricultores (críticos)
    hit("GET", f"{BASE}/api/admin/alertas/agricultores", headers=auth)
    # 7.5) Responder mensagem
    if mid:
        hit("PUT", f"{BASE}/api/admin/mensagens/{mid}/responder", headers=auth, json_body={
            "resposta": "Equipe acionada. Verifique o painel."
        })
        # 7.6) Marcar como lida
        hit("PUT", f"{BASE}/api/admin/mensagens/{mid}/ler", headers=auth)

    # 8) Logout (auth)
    hit("POST", f"{BASE}/api/logout", headers=auth)

    # 9) ML smoke tests
    hit("POST", f"{BASE}/api/ml/analisar", json_body={
        "dados_sensor": {
            "temperatura_ar": 24.1,
            "humidade_ar": 60.0,
            "pressao_ar": 1012.3,
            "humidade_solo": 55.0,
            "vibracao": False
        }
    })
    hit("GET", f"{BASE}/api/ml/alertas")

if __name__ == "__main__":
    main()
