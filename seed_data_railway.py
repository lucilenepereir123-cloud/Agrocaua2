"""
seed_data_railway.py
Popula a plataforma AgroCaua com dados realistas de sensores IoT.
Uso: python seed_data_railway.py --url https://web-production-883671.up.railway.app
"""
import requests
import json
import random
import time
import argparse
from datetime import datetime, timedelta, timezone

# ── Configuração ──────────────────────────────────────────────
DEFAULT_URL  = "https://web-production-883671.up.railway.app"
DEVICE_ID    = "esp32-001"
LOCALIZACAO  = "https://maps.app.goo.gl/pfaKcQX3wUT6Cv34A"
LATITUDE     = -9.0122   # Kifangondo, Angola
LONGITUDE    = 13.2337

# ── Perfis de dados ───────────────────────────────────────────
def gerar_leitura(hora_offset_h=0, com_praga=False, solo_seco=False):
    """Gera uma leitura IoT realista."""
    hora = (datetime.now(timezone.utc) - timedelta(hours=hora_offset_h))

    # Temperatura: varia por hora do dia (mais quente ao meio-dia)
    hora_do_dia = (hora.hour + 12) % 24
    temp_base = 22 + 8 * abs(hora_do_dia - 12) / 12
    temp = round(temp_base + random.uniform(-2, 2), 1)

    # Humidade do ar: inversa da temperatura
    hum_ar = round(65 - (temp - 22) * 1.5 + random.uniform(-5, 5), 1)
    hum_ar = max(30, min(95, hum_ar))

    # Pressão: ligeiras variações
    pressao = round(1013.25 + random.uniform(-8, 8), 1)

    # Humidade do solo
    if solo_seco:
        hum_solo = round(random.uniform(15, 28), 1)
    else:
        hum_solo = round(random.uniform(35, 70), 1)

    # Vibração: rara
    vibracao = random.random() < 0.05

    # Praga
    detecao_praga = com_praga
    tipo_praga    = random.choice(["Lagarta", "Pulgão", "Mosca-branca"]) if com_praga else None
    confianca     = round(random.uniform(0.75, 0.96), 2) if com_praga else None

    return {
        "device_id": DEVICE_ID,
        "timestamp": hora.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "localizacao": {"localizacao": LOCALIZACAO},
        "gps": {"latitude": LATITUDE + random.uniform(-0.001, 0.001),
                "longitude": LONGITUDE + random.uniform(-0.001, 0.001)},
        "bme280": {
            "temperatura": temp,
            "humidade": hum_ar,
            "pressao": pressao
        },
        "solo": {"humidade": hum_solo},
        "vibracao": {"detectada": vibracao},
        "visao": {
            "detecao_praga": detecao_praga,
            "tipo_praga": tipo_praga,
            "confianca": confianca
        }
    }


def enviar(url, payload, idx, total):
    endpoint = f"{url.rstrip('/')}/api/dados"
    try:
        r = requests.post(endpoint, json=payload, timeout=15)
        ts = payload['timestamp']
        if r.status_code in (200, 201):
            print(f"  [{idx:>3}/{total}] ✓ {ts} — temp:{payload['bme280']['temperatura']}°C solo:{payload['solo']['humidade']}%")
        else:
            print(f"  [{idx:>3}/{total}] ✗ {ts} — HTTP {r.status_code}: {r.text[:80]}")
    except Exception as e:
        print(f"  [{idx:>3}/{total}] ✗ Erro: {e}")


def main():
    parser = argparse.ArgumentParser(description="Seed AgroCaua com dados IoT")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL base da plataforma")
    parser.add_argument("--dias", type=int, default=7, help="Dias de histórico (padrão: 7)")
    parser.add_argument("--por-hora", type=int, default=2, help="Leituras por hora (padrão: 2)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay entre pedidos em segundos")
    args = parser.parse_args()

    total_horas  = args.dias * 24
    leituras     = []

    print(f"\n🌱 AgroCaua Seed Script")
    print(f"   URL:    {args.url}")
    print(f"   Dias:   {args.dias}")
    print(f"   Device: {DEVICE_ID}")
    print(f"   Total:  ~{total_horas * args.por_hora} leituras\n")

    # Gerar leituras: do mais antigo para o mais recente
    for h in range(total_horas, 0, -1):
        for _ in range(args.por_hora):
            offset = h - random.uniform(0, 0.9)
            # 5% das leituras têm praga, 10% têm solo seco
            com_praga = random.random() < 0.05
            solo_seco = random.random() < 0.10
            leituras.append(gerar_leitura(offset, com_praga, solo_seco))

    # Adicionar algumas leituras recentes (última hora)
    for i in range(6):
        leituras.append(gerar_leitura(i * 0.1))

    total = len(leituras)
    print(f"Enviando {total} leituras para {args.url}...\n")

    for i, payload in enumerate(leituras, 1):
        enviar(args.url, payload, i, total)
        if args.delay > 0:
            time.sleep(args.delay)

    print(f"\n✅ Concluído! {total} leituras enviadas.")
    print(f"   Abre o dashboard: {args.url}/dashboard")

if __name__ == "__main__":
    main()
