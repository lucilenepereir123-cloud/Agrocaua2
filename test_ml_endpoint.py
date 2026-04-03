#!/usr/bin/env python3
"""
Script de teste: testa o novo endpoint GET /api/analises_ml
"""

import requests
import json

# URL da API (ajuste conforme necessário)
API_URL = "http://localhost:5000/api/analises_ml"

print("=" * 80)
print("🧪 TESTE DO NOVO ENDPOINT ML")
print("=" * 80)

# Teste 1: Análise com dados históricos
print(f"\n📊 Teste 1: Análise com dados históricos")
print(f"GET {API_URL}")

try:
    response = requests.get(API_URL)
    print(f"✅ Status: {response.status_code}")

    if response.status_code == 200:
        resultado = response.json()
        print(f"\n📥 Tipo: {resultado.get('tipo')}")
        print(f"📊 Registros analisados: {resultado.get('registros_analisados', 0)}")

        if 'periodo' in resultado:
            p = resultado['periodo']
            print(f"📅 Período: {p.get('mais_antigo')} → {p.get('mais_recente')}")

        if 'previsoes' in resultado:
            prev = resultado['previsoes']
            print(f"\n🚨 ALERTAS:")
            if 'alertas' in prev:
                alertas = prev['alertas']
                for tipo, dados in alertas.items():
                    print(f"  • {tipo.upper()}: {dados['nivel']} (score: {dados['score']})")

            if 'mensagens_analise' in prev:
                print(f"\n📝 MENSAGENS:")
                msgs = prev['mensagens_analise']
                for tipo, msg in msgs.items():
                    print(f"  • {tipo.upper()}: {msg['simples']}")

    else:
        print(f"❌ Erro: {response.text}")

except requests.exceptions.ConnectionError:
    print(f"❌ ERRO: Não foi possível conectar à API em {API_URL}")
    print("   Verifique se a API está rodando (python app.py)")

# Teste 2: Análise com dados atuais via parâmetro
print(f"\n\n📊 Teste 2: Análise com dados atuais")
dados_atuais = {
    "temperatura_ar": 35.0,
    "humidade_ar": 20.0,
    "pressao_ar": 1005.0,
    "humidade_solo": 10.0
}

dados_json = json.dumps(dados_atuais)
url_com_dados = f"{API_URL}?dados_json={requests.utils.quote(dados_json)}"
print(f"GET {url_com_dados}")

try:
    response = requests.get(url_com_dados)
    print(f"✅ Status: {response.status_code}")

    if response.status_code == 200:
        resultado = response.json()
        print(f"\n📥 Tipo: {resultado.get('tipo')}")
        print(f"📊 Dados analisados: {resultado.get('dados_analisados')}")

        if 'previsoes' in resultado:
            prev = resultado['previsoes']
            print(f"\n🚨 ALERTAS:")
            if 'alertas' in prev:
                alertas = prev['alertas']
                for tipo, dados in alertas.items():
                    print(f"  • {tipo.upper()}: {dados['nivel']} (score: {dados['score']})")

    else:
        print(f"❌ Erro: {response.text}")

except Exception as e:
    print(f"❌ ERRO: {e}")

print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO")
print("=" * 80)