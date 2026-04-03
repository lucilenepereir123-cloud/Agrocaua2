#!/usr/bin/env python3
"""
Script para treinar modelos ML com dados sintéticos
"""

import numpy as np
import os
from ML.preprocessor import SensorPreprocessor
from ML.ml_models import SimpleLogisticRegression, SimpleLinearRegression

def gerar_dados_sinteticos(n_samples=1000):
    """Gerar dados sintéticos de sensores"""
    np.random.seed(42)

    # Dados base
    temperatura_ar = np.random.normal(25, 5, n_samples)  # 25°C ± 5°C
    humidade_ar = np.random.normal(60, 15, n_samples)    # 60% ± 15%
    pressao_ar = np.random.normal(1013, 10, n_samples)   # 1013 hPa ± 10
    humidade_solo = np.random.normal(50, 20, n_samples)  # 50% ± 20%

    # Criar targets
    # Praga detectada se temperatura alta + humidade baixa + solo seco
    praga_detectada = ((temperatura_ar > 28) & (humidade_ar < 50) & (humidade_solo < 30)).astype(int)

    # Tipo de praga (0=Nenhuma, 1=Afídeos, 2=Ácaros, 3=Míldio)
    tipo_praga = np.zeros(n_samples, dtype=int)
    mask_praga = praga_detectada == 1
    tipo_praga[mask_praga] = np.random.choice([1, 2, 3], size=mask_praga.sum())

    # Temperatura futura (ligeiramente diferente da atual)
    temperatura_futura = temperatura_ar + np.random.normal(0, 2, n_samples)

    # Humidade futura
    humidade_futura = humidade_ar + np.random.normal(0, 5, n_samples)
    humidade_futura = np.clip(humidade_futura, 0, 100)

    return {
        'X': np.column_stack([temperatura_ar, humidade_ar, pressao_ar, humidade_solo]),
        'y_praga': praga_detectada,
        'y_tipo': tipo_praga,
        'y_temp': temperatura_futura,
        'y_humidade': humidade_futura
    }

def main():
    print("🔧 Gerando dados sintéticos...")
    dados = gerar_dados_sinteticos(2000)

    print("📊 Preparando preprocessor...")
    preprocessor = SensorPreprocessor()
    preprocessor.fit(dados['X'])

    # Salvar preprocessor
    os.makedirs('ML/models', exist_ok=True)
    preprocessor.save('ML/models/preprocessor.pkl')

    print("🤖 Treinando modelos...")

    # Modelo para detectar praga
    clf_praga = SimpleLogisticRegression(learning_rate=0.01, n_iterations=1000)
    clf_praga.fit(dados['X'], dados['y_praga'])

    # Modelo para classificar tipo de praga (apenas para dados com praga)
    mask_praga = dados['y_praga'] == 1
    if mask_praga.sum() > 0:
        clf_tipo = SimpleLogisticRegression(learning_rate=0.01, n_iterations=1000)
        clf_tipo.fit(dados['X'][mask_praga], dados['y_tipo'][mask_praga])
    else:
        clf_tipo = SimpleLogisticRegression()
        clf_tipo.fit(dados['X'][:10], dados['y_tipo'][:10])  # Treino mínimo

    # Modelo para prever temperatura futura
    reg_temp = SimpleLinearRegression()
    reg_temp.fit(dados['X'], dados['y_temp'])

    # Modelo para prever humidade futura
    reg_humidade = SimpleLinearRegression()
    reg_humidade.fit(dados['X'], dados['y_humidade'])

    print("💾 Salvando modelos...")

    import pickle
    with open('ML/models/praga_detector.pkl', 'wb') as f:
        pickle.dump(clf_praga, f)

    with open('ML/models/tipo_praga_classifier.pkl', 'wb') as f:
        pickle.dump(clf_tipo, f)

    with open('ML/models/temperatura_predictor.pkl', 'wb') as f:
        pickle.dump(reg_temp, f)

    with open('ML/models/humidade_predictor.pkl', 'wb') as f:
        pickle.dump(reg_humidade, f)

    print("✅ Treinamento concluído!")
    print("📁 Modelos salvos em ML/models/")

if __name__ == "__main__":
    main()