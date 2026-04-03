#!/usr/bin/env python3
"""
Script de teste: envia dados com sensores para a API e mostra resposta com alertas
"""

import requests
import json
from datetime import datetime

# URL da API (ajuste conforme necessário)
API_URL = "http://localhost:5000/api/dados"

# Dados de teste com sensores
dados_teste = {
    "device_id": "SENSOR_TESTE_001",
    "timestamp": datetime.now().isoformat(),
    "gps": {
        "latitude": 38.7223,
        "longitude": -9.1393
    },
    "localizacao": "Lisboa, Portugal",
    "bme280": {
        "temperatura": 32.5,
        "humidade": 25.0,
        "pressao": 1008.5
    },
    "solo": {
        "humidade": 15.0
    },
    "vibracao": {
        "detectada": True
    }
}

print("=" * 80)
print("🧪 TESTE DE API COM ALERTAS ML")
print("=" * 80)
print(f"\n📤 Enviando dados para: {API_URL}")
print(f"\n📊 Dados de teste:")
print(json.dumps(dados_teste, indent=2, ensure_ascii=False))

try:
    # Fazer POST
    response = requests.post(API_URL, json=dados_teste)
    
    print(f"\n✅ Status: {response.status_code}")
    
    if response.status_code in [200, 201]:
        resultado = response.json()
        
        print("\n" + "=" * 80)
        print("📥 RESPOSTA DA API")
        print("=" * 80)
        
        # Exibir resposta completa
        print(json.dumps(resultado, indent=2, ensure_ascii=False))
        
        # Extrair e destacar alertas
        if 'previsoes' in resultado:
            previsoes = resultado['previsoes']
            
            print("\n" + "=" * 80)
            print("🚨 ALERTAS DETECTADOS")
            print("=" * 80)
            
            if 'alertas' in previsoes:
                alertas = previsoes['alertas']
                
                # Estresse Hídrico
                if 'estresse_hidrico' in alertas:
                    sh = alertas['estresse_hidrico']
                    print(f"\n💧 ESTRESSE HÍDRICO:")
                    print(f"   Nível: {sh['nivel'].upper()}")
                    print(f"   Score: {sh['score']}")
                
                # Risco de Incêndio
                if 'risco_incendio' in alertas:
                    ri = alertas['risco_incendio']
                    print(f"\n🔥 RISCO DE INCÊNDIO:")
                    print(f"   Nível: {ri['nivel'].upper()}")
                    print(f"   Score: {ri['score']}")
                
                # Mudança Climática
                if 'mudanca_climatica' in alertas:
                    mc = alertas['mudanca_climatica']
                    print(f"\n🌡️  MUDANÇA CLIMÁTICA:")
                    print(f"   Nível: {mc['nivel'].upper()}")
                    print(f"   Score: {mc['score']}")
                    print(f"   Delta Temperatura: {mc['delta_temperatura']}°C")
                    print(f"   Delta Pressão: {mc['delta_pressao']} hPa")
            
            # Mensagens de Análise
            if 'mensagens_analise' in previsoes:
                mensagens = previsoes['mensagens_analise']
                print("\n" + "=" * 80)
                print("📝 MENSAGENS DE ANÁLISE")
                print("=" * 80)
                
                for chave, mensagem in mensagens.items():
                    print(f"\n{chave.upper().replace('_', ' ')}:")
                    print(f"  → {mensagem}")
            
            # Análise Agregada
            if 'analise_agregada' in previsoes:
                agregada = previsoes['analise_agregada']
                print("\n" + "=" * 80)
                print("📈 ANÁLISE AGREGADA")
                print("=" * 80)
                print(f"\nNúmero de sensores: {agregada['num_sensores']}")
                print(f"Temperatura: {agregada['temperatura_range']}")
                print(f"Humidade: {agregada['humidade_range']}")
                print(f"Variação temperatura: {agregada['variacao_temperatura']}°C")
                print(f"Variação humidade: {agregada['variacao_humidade']}%")
        
        print("\n" + "=" * 80)
        print("✅ TESTE CONCLUÍDO COM SUCESSO")
        print("=" * 80)
    else:
        print(f"\n❌ Erro na resposta:")
        print(response.text)

except requests.exceptions.ConnectionError:
    print(f"\n❌ ERRO: Não foi possível conectar à API em {API_URL}")
    print("   Verifique se a API está rodando (python app.py)")
except Exception as e:
    print(f"\n❌ ERRO: {e}")

print()
