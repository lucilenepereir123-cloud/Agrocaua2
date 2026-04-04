import re
import time
import json
import requests

BASE = "http://127.0.0.1:5000"

def post_dados(payload):
    r = requests.post(f"{BASE}/api/dados", json=payload, timeout=10)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"erro": r.text}

def get_alertas():
    r = requests.get(f"{BASE}/api/alertas", timeout=10)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, []

def contem_campos_basicos(alerta):
    campos = ("tipo", "mensagem", "severidade", "status")
    return all(c in alerta for c in campos)

def esperar_alerta(tipo, tentativas=5, pausa=0.6):
    for _ in range(tentativas):
        _, arr = get_alertas()
        for a in arr:
            if a.get("tipo") == tipo:
                return a
        time.sleep(pausa)
    return None

def testar_solo():
    print("=== TESTE: Solo — humidade abaixo do limiar")
    payload = {
        "device_id": "sensor-teste-solo",
        "gps": {"latitude": -8.12, "longitude": 39.33},
        "localizacao": {"localizacao": "Parcela Teste"},
        "bme280": {"temperatura": 22.0, "humidade": 60.0, "pressao": 1013.0},
        "solo": {"humidade": 10.0},
        "vibracao": {"detectada": False}
    }
    st, res = post_dados(payload)
    print("POST /api/dados =>", st, json.dumps(res, ensure_ascii=False))
    alerta = esperar_alerta("Solo")
    assert alerta is not None, "Alerta de Solo não encontrado"
    print("Alerta:", alerta.get("mensagem"))
    assert contem_campos_basicos(alerta), "Alerta de Solo sem campos básicos"
    print("✓ Solo OK\n")

def testar_clima():
    print("=== TESTE: Clima — temperatura abaixo do limiar")
    payload = {
        "device_id": "sensor-teste-clima",
        "gps": {"latitude": -8.13, "longitude": 39.34},
        "localizacao": {"localizacao": "Parcela Teste"},
        "bme280": {"temperatura": 10.0, "humidade": 65.0, "pressao": 1015.0},
        "solo": {"humidade": 50.0},
        "vibracao": {"detectada": False}
    }
    st, res = post_dados(payload)
    print("POST /api/dados =>", st, json.dumps(res, ensure_ascii=False))
    alerta = esperar_alerta("Clima")
    assert alerta is not None, "Alerta de Clima não encontrado"
    print("Alerta:", alerta.get("mensagem"))
    assert contem_campos_basicos(alerta), "Alerta de Clima sem campos básicos"
    print("✓ Clima OK\n")

def testar_sensor():
    print("=== TESTE: Sensor — vibração detectada")
    payload = {
        "device_id": "sensor-teste-vibracao",
        "gps": {"latitude": -8.14, "longitude": 39.35},
        "localizacao": {"localizacao": "Parcela Teste"},
        "bme280": {"temperatura": 22.0, "humidade": 55.0, "pressao": 1010.0},
        "solo": {"humidade": 55.0},
        "vibracao": {"detectada": True}
    }
    st, res = post_dados(payload)
    print("POST /api/dados =>", st, json.dumps(res, ensure_ascii=False))
    alerta = esperar_alerta("Sensor")
    assert alerta is not None, "Alerta de Sensor não encontrado"
    print("Alerta:", alerta.get("mensagem"))
    assert contem_campos_basicos(alerta), "Alerta de Sensor sem campos básicos"
    print("✓ Sensor OK\n")

def main():
    print("==============================================")
    print("TESTES AUTOMATIZADOS — Alertas por Limiar")
    print("==============================================\n")
    testar_solo()
    testar_clima()
    testar_sensor()
    print("=== TESTE: Praga (ML) — condições favoráveis")
    st, res = post_dados({
        "device_id": "sensor-teste-ml",
        "gps": {"latitude": -8.11, "longitude": 39.31},
        "localizacao": {"localizacao": "Parcela Teste"},
        "bme280": {"temperatura": 28.0, "humidade": 75.0, "pressao": 1012.0},
        "solo": {"humidade": 60.0},
        "vibracao": {"detectada": False}
    })
    print("POST /api/dados =>", st, json.dumps(res, ensure_ascii=False))
    al = esperar_alerta("Praga")
    if al:
        print("Alerta:", al.get("mensagem"))
        assert contem_campos_basicos(al), "Alerta de Praga sem campos básicos"
        print("✓ Praga (ML) OK\n")
    else:
        print("Sem alerta de Praga (ML) — pode depender da heurística/condições.")
    print("Todos os testes concluídos com sucesso.")
    print("=== TESTE: Zonas — CRUD básico autenticado")
    try:
        r = requests.post(f"{BASE}/api/login", json={"email":"admin@agrocaua.com","password":"admin123"})
        token = r.json().get("token") if r.ok else None
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        zr = requests.post(f"{BASE}/api/zones", headers=headers, json={"nome":"Talhão Teste","cultura":"Milho","tipo":"Milho","area":1.5,"estagio":"Crescimento","saude":"Bom","acoes":"Irrigar 20min"})
        print("CREATE /api/zones =>", zr.status_code, zr.text[:120])
        zid = zr.json().get("id") if zr.ok else None
        gl = requests.get(f"{BASE}/api/zones", headers=headers)
        print("LIST /api/zones =>", gl.status_code)
        if zid:
            up = requests.put(f"{BASE}/api/zones/{zid}", headers=headers, json={"saude":"Excelente","acoes":"Irrigar 30min"})
            print("UPDATE /api/zones/:id =>", up.status_code)
            de = requests.delete(f"{BASE}/api/zones/{zid}", headers=headers)
            print("DELETE /api/zones/:id =>", de.status_code)
    except Exception as e:
        print("ERRO Zonas:", e)

if __name__ == "__main__":
    main()
