"""
Modulo de Recomendacoes em Linguagem Natural.
Transforma os scores e niveis do PredictorML em accoes concretas
para o agricultor, em linguagem simples e directa.

Uso:
    from ML.recomendador import gerar_recomendacoes
    recs = gerar_recomendacoes(resultado_predictor, dados_sensor, cultura='cafe')
"""

from datetime import datetime


# ---------------------------------------------------------------------------
# Limites de conforto por cultura
# ---------------------------------------------------------------------------

CULTURAS = {
    # ─── Café (principal cultura comercial do Kwanza Sul) ───────────────────
    'cafe': {
        # Arabica (zonas altas >=800m): 18-28 C; Robusta: ate 30 C
        # Gama combinada pratica para Cuanza-Sul: 18-30 C
        'temp_min': 18.0, 'temp_max': 30.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 55.0,
        'humidade_ar_min':   65.0, 'humidade_ar_max':   85.0,
        'nome_display': 'Café',
        'ph_min': 5.5, 'ph_max': 6.5,
        'precipitacao_anual_min': 1200, 'precipitacao_anual_max': 2000,
        'altitude_min': 500, 'altitude_max': 1800,
        'ciclo_dias': 365,  # perene
        'observacoes': 'Principal cultura de exportação do Kwanza Sul. Requer sombra parcial e solo bem drenado.',
        'fases': {
            'florescimento': {'hum_solo_min': 35.0},
            'frutificacao':  {'hum_solo_min': 30.0},
            'maturacao':     {'hum_solo_min': 25.0},
            'repouso':       {'hum_solo_min': 20.0},
        },
    },

    # ─── Milho (cereais) ────────────────────────────────────────────────────
    'milho': {
        'temp_min': 18.0, 'temp_max': 32.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 65.0,
        'humidade_ar_min':   45.0, 'humidade_ar_max':   75.0,
        'nome_display': 'Milho',
        'ph_min': 5.8, 'ph_max': 7.0,
        'precipitacao_anual_min': 500, 'precipitacao_anual_max': 1500,
        'ciclo_dias': 120,
        'observacoes': 'Cereal mais cultivado em Angola. Adapta-se bem às chuvas sazonais do Kwanza Sul.',
        'fases': {
            'germinacao':    {'hum_solo_min': 40.0, 'temp_max': 35.0},
            'crescimento':   {'hum_solo_min': 35.0},
            'polinizacao':   {'hum_solo_min': 45.0, 'hum_ar_min': 50.0},  # fase crítica
            'enchimento':    {'hum_solo_min': 35.0},
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Mandioca (raízes e tubérculos) ────────────────────────────────────
    'mandioca': {
        'temp_min': 20.0, 'temp_max': 35.0,
        'humidade_solo_min': 20.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   80.0,
        'nome_display': 'Mandioca',
        'ph_min': 5.5, 'ph_max': 7.0,
        'precipitacao_anual_min': 500, 'precipitacao_anual_max': 1500,
        'ciclo_dias': 270,  # 9-12 meses
        'observacoes': 'Cultura de segurança alimentar resistente à seca. Muito cultivada no interior do Kwanza Sul.',
        'fases': {
            'brotacao':      {'hum_solo_min': 35.0},
            'crescimento':   {'hum_solo_min': 25.0},
            'tuberizacao':   {'hum_solo_min': 30.0},
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Feijão (leguminosas) ───────────────────────────────────────────────
    'feijao': {
        'temp_min': 16.0, 'temp_max': 30.0,
        'humidade_solo_min': 30.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   75.0,
        'nome_display': 'Feijão',
        'ph_min': 6.0, 'ph_max': 7.0,
        'precipitacao_anual_min': 400, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 90,
        'observacoes': 'Leguminosa essencial na dieta angolana. Fixa azoto no solo e pode ser rotacionado com milho.',
        'fases': {
            'germinacao':    {'hum_solo_min': 40.0, 'temp_max': 32.0},
            'florescimento': {'hum_solo_min': 40.0},  # fase crítica para rendimento
            'enchimento':    {'hum_solo_min': 35.0},
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Batata-doce ────────────────────────────────────────────────────────
    'batata_doce': {
        'temp_min': 20.0, 'temp_max': 32.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   80.0,
        'nome_display': 'Batata-doce',
        'ph_min': 5.5, 'ph_max': 6.5,
        'precipitacao_anual_min': 500, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 150,
        'observacoes': 'Tuberosa resistente e de alta produtividade. Cultivada em várias regiões do Kwanza Sul.',
        'fases': {
            'enraizamento':  {'hum_solo_min': 40.0},
            'crescimento':   {'hum_solo_min': 30.0},
            'tuberizacao':   {'hum_solo_min': 35.0},
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Amendoim ───────────────────────────────────────────────────────────
    'amendoim': {
        'temp_min': 20.0, 'temp_max': 33.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 55.0,
        'humidade_ar_min':   45.0, 'humidade_ar_max':   70.0,
        'nome_display': 'Amendoim',
        'ph_min': 5.5, 'ph_max': 6.5,
        'precipitacao_anual_min': 500, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 120,
        'observacoes': 'Leguminosa oleaginosa importante no Kwanza Sul. Fixa azoto e melhora a fertilidade do solo.',
        'fases': {
            'germinacao':    {'hum_solo_min': 35.0},
            'florescimento': {'hum_solo_min': 35.0},
            'frutificacao':  {'hum_solo_min': 40.0},  # entrada das vagens no solo - fase crítica
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Arroz ──────────────────────────────────────────────────────────────
    'arroz': {
        'temp_min': 20.0, 'temp_max': 35.0,
        'humidade_solo_min': 60.0, 'humidade_solo_max': 100.0,  # cultivo alagado
        'humidade_ar_min':   60.0, 'humidade_ar_max':   90.0,
        'nome_display': 'Arroz',
        'ph_min': 5.5, 'ph_max': 7.0,
        'precipitacao_anual_min': 1000, 'precipitacao_anual_max': 2000,
        'ciclo_dias': 150,
        'observacoes': 'Cultivado em zonas alagadas e várzeas do Kwanza Sul. Necessita de elevada disponibilidade de água.',
        'fases': {
            'germinacao':    {'hum_solo_min': 70.0},
            'perfilhamento': {'hum_solo_min': 75.0},
            'espigamento':   {'hum_solo_min': 80.0},  # fase mais crítica
            'maturacao':     {'hum_solo_min': 60.0},
        },
    },

    # ─── Soja ───────────────────────────────────────────────────────────────
    'soja': {
        'temp_min': 20.0, 'temp_max': 30.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   70.0,
        'nome_display': 'Soja',
        'ph_min': 6.0, 'ph_max': 7.0,
        'precipitacao_anual_min': 600, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 120,
        'observacoes': 'Cultura de crescente interesse no Kwanza Sul. Requer inoculação de rizóbio para boa fixação de azoto.',
        'fases': {
            'germinacao':    {'hum_solo_min': 40.0},
            'vegetativo':    {'hum_solo_min': 35.0},
            'florescimento': {'hum_solo_min': 40.0},  # fase crítica
            'enchimento':    {'hum_solo_min': 40.0},
            'maturacao':     {'hum_solo_min': 20.0},
        },
    },

    # ─── Horticultura — Tomate ─────────────────────────────────────────────
    'tomate': {
        'temp_min': 18.0, 'temp_max': 30.0,
        'humidade_solo_min': 40.0, 'humidade_solo_max': 70.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   70.0,
        'nome_display': 'Tomate',
        'ph_min': 5.5, 'ph_max': 6.8,
        'precipitacao_anual_min': 600, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 90,
        'observacoes': 'Hortícola de elevado valor económico. Cultivado em perímetros de regadio do Kwanza Sul.',
        'fases': {
            'transplante':   {'hum_solo_min': 50.0},
            'crescimento':   {'hum_solo_min': 45.0},
            'florescimento': {'hum_solo_min': 50.0, 'hum_ar_max': 70.0},  # alta humidade = fungos
            'frutificacao':  {'hum_solo_min': 50.0},
            'maturacao':     {'hum_solo_min': 40.0},
        },
    },

    # ─── Horticultura — Cebola ─────────────────────────────────────────────
    'cebola': {
        'temp_min': 12.0, 'temp_max': 28.0,
        'humidade_solo_min': 30.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   40.0, 'humidade_ar_max':   65.0,
        'nome_display': 'Cebola',
        'ph_min': 6.0, 'ph_max': 7.0,
        'precipitacao_anual_min': 400, 'precipitacao_anual_max': 800,
        'ciclo_dias': 120,
        'observacoes': 'Hortícola de elevada procura. Exige solo bem drenado e baixa humidade na maturação para evitar podridão.',
        'fases': {
            'germinacao':    {'hum_solo_min': 45.0},
            'crescimento':   {'hum_solo_min': 40.0},
            'bulbificacao':  {'hum_solo_min': 35.0},
            'maturacao':     {'hum_solo_min': 20.0, 'hum_ar_max': 60.0},
        },
    },

    # ─── Horticultura — Couve ──────────────────────────────────────────────
    'couve': {
        'temp_min': 15.0, 'temp_max': 28.0,
        'humidade_solo_min': 40.0, 'humidade_solo_max': 70.0,
        'humidade_ar_min':   55.0, 'humidade_ar_max':   80.0,
        'nome_display': 'Couve',
        'ph_min': 6.0, 'ph_max': 7.0,
        'precipitacao_anual_min': 600, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 75,
        'observacoes': 'Hortícola folhosa muito consumida. Produção contínua possível com irrigação regular.',
    },

    # ─── Banana/Bananeira ──────────────────────────────────────────────────
    'banana': {
        'temp_min': 20.0, 'temp_max': 35.0,
        'humidade_solo_min': 50.0, 'humidade_solo_max': 80.0,
        'humidade_ar_min':   65.0, 'humidade_ar_max':   90.0,
        'nome_display': 'Banana',
        'ph_min': 5.5, 'ph_max': 7.0,
        'precipitacao_anual_min': 1200, 'precipitacao_anual_max': 2500,
        'ciclo_dias': 365,  # perene
        'observacoes': 'Fruticola importante no Kwanza Sul. Exige elevada humidade e ausência de ventos fortes.',
        'fases': {
            'brotacao':      {'hum_solo_min': 60.0},
            'crescimento':   {'hum_solo_min': 55.0},
            'florescimento': {'hum_solo_min': 60.0},
            'frutificacao':  {'hum_solo_min': 65.0},
            'maturacao':     {'hum_solo_min': 50.0},
        },
    },

    # ─── Abacaxi ────────────────────────────────────────────────────────────
    'abacaxi': {
        'temp_min': 20.0, 'temp_max': 32.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 55.0,
        'humidade_ar_min':   50.0, 'humidade_ar_max':   80.0,
        'nome_display': 'Abacaxi',
        'ph_min': 4.5, 'ph_max': 6.0,
        'precipitacao_anual_min': 800, 'precipitacao_anual_max': 1500,
        'ciclo_dias': 540,  # 18 meses
        'observacoes': 'Fruticola de boa adaptação às condições do Kwanza Sul. Tolera períodos secos moderados.',
    },

    # ─── Horticultura — Piri-piri ──────────────────────────────────────────
    'piri_piri': {
        'temp_min': 18.0, 'temp_max': 32.0,
        'humidade_solo_min': 30.0, 'humidade_solo_max': 60.0,
        'humidade_ar_min':   45.0, 'humidade_ar_max':   70.0,
        'nome_display': 'Piri-piri',
        'ph_min': 5.5, 'ph_max': 7.0,
        'precipitacao_anual_min': 500, 'precipitacao_anual_max': 1200,
        'ciclo_dias': 120,
        'observacoes': 'Condimento de elevado valor comercial. Angola é um dos maiores produtores mundiais.',
    },

    # ─── Girassol ───────────────────────────────────────────────────────────
    'girassol': {
        'temp_min': 18.0, 'temp_max': 32.0,
        'humidade_solo_min': 25.0, 'humidade_solo_max': 55.0,
        'humidade_ar_min':   40.0, 'humidade_ar_max':   65.0,
        'nome_display': 'Girassol',
        'ph_min': 6.0, 'ph_max': 7.5,
        'precipitacao_anual_min': 400, 'precipitacao_anual_max': 1000,
        'ciclo_dias': 100,
        'observacoes': 'Cultura oleaginosa resistente à seca. Crescente interesse no Kwanza Sul para produção de óleo.',
    },
}

CULTURA_GENERICA = {
    'temp_min': 18.0, 'temp_max': 32.0,
    'humidade_solo_min': 25.0, 'humidade_solo_max': 65.0,
    'humidade_ar_min':   45.0, 'humidade_ar_max':   75.0,
    'nome_display': 'Cultura',
}

# Aliases — normaliza variações ortográficas e sinónimos
CULTURA_ALIASES = {
    'café': 'cafe',
    'coffee': 'cafe',
    'robusta': 'cafe',
    'arabica': 'cafe',
    'corn': 'milho',
    'maize': 'milho',
    'cassava': 'mandioca',
    'manioc': 'mandioca',
    'macamba': 'amendoim',
    'groundnut': 'amendoim',
    'peanut': 'amendoim',
    'rice': 'arroz',
    'soybean': 'soja',
    'feijão': 'feijao',
    'bean': 'feijao',
    'batata doce': 'batata_doce',
    'batata-doce': 'batata_doce',
    'sweet potato': 'batata_doce',
    'tomato': 'tomate',
    'onion': 'cebola',
    'cabbage': 'couve',
    'pineapple': 'abacaxi',
    'banana': 'banana',
    'girasol': 'girassol',
    'sunflower': 'girassol',
    'piri piri': 'piri_piri',
    'malagueta': 'piri_piri',
    'pepper': 'piri_piri',
}


def _resolver_cultura(cultura_str):
    """Normaliza o nome da cultura e devolve a config correspondente."""
    if not cultura_str:
        return CULTURA_GENERICA
    key = cultura_str.strip().lower().replace(' ', '_')
    key = CULTURA_ALIASES.get(key, key)
    return CULTURAS.get(key, CULTURA_GENERICA)


def _cultura_display(cultura_str):
    """Devolve o nome de apresentação de uma cultura."""
    cfg = _resolver_cultura(cultura_str)
    return cfg.get('nome_display', cultura_str or 'Cultura')


# ---------------------------------------------------------------------------
# Recomendacoes por categoria
# ---------------------------------------------------------------------------

def _rec_estresse_hidrico(alerta, dados_sensor, cultura_cfg):
    nivel     = alerta.get('nivel', 'seguro')
    score     = alerta.get('score', 0.0)
    if nivel == 'seguro':
        return None

    temp      = dados_sensor.get('temperatura_ar', 20.0)
    hum_solo  = dados_sensor.get('humidade_solo', 50.0)
    hum_ar    = dados_sensor.get('humidade_ar', 60.0)
    nome      = cultura_cfg.get('nome_display', 'Cultura')
    dias_seca = alerta.get('dias_sem_chuva')
    fase_cafe = dados_sensor.get('fase_cafe', '')

    solo_min = cultura_cfg.get('humidade_solo_min', 25.0)
    if fase_cafe and 'fases' in cultura_cfg:
        solo_min = cultura_cfg['fases'].get(fase_cafe, {}).get('hum_solo_min', solo_min)

    deficit   = max(0.0, solo_min - hum_solo)
    hora      = datetime.now().hour
    if 5 <= hora < 9:
        janela = "agora de manha (hora ideal — menor evaporacao)"
    elif 17 <= hora < 20:
        janela = "hoje ao final da tarde (segunda melhor opcao)"
    else:
        janela = "de manha cedo (5h-9h) ou ao final da tarde"

    seca_nota = f" Ha {dias_seca} dias sem chuva — solo a secar progressivamente." if dias_seca else ""
    fase_nota = f" Fase actual: {fase_cafe}." if fase_cafe and 'fases' in cultura_cfg else ""

    if nivel == 'critico':
        urgencia = "URGENTE"
        accao = (
            f"Activar a irrigacao gota-a-gota {janela}. "
            f"Solo em {hum_solo:.0f}% de humidade — precisa de subir {deficit:.0f} pontos. "
            f"Com {temp:.0f} graus e ar a {hum_ar:.0f}%, a planta esta sob stresse severo "
            f"e pode perder producao.{seca_nota}{fase_nota}"
        )
    elif nivel == 'alto':
        urgencia = "ALTA"
        accao = (
            f"Planear irrigacao para {janela}. "
            f"Solo ({hum_solo:.0f}%) abaixo do ideal para {nome}. "
            f"A temperatura de {temp:.0f} graus acelera a perda de humidade.{seca_nota}{fase_nota}"
        )
    elif nivel == 'moderado':
        urgencia = "MEDIA"
        accao = (
            f"Monitorar o solo ao longo do dia. "
            f"Se a humidade descer abaixo de {solo_min:.0f}%, activar a irrigacao {janela}.{seca_nota}"
        )
    else:
        urgencia = "BAIXA"
        accao = f"Humidade aceitavel por agora. Verificar novamente em 6-8 horas.{seca_nota}"

    return {'categoria': 'Gestao de Agua', 'urgencia': urgencia, 'accao': accao, 'score': score}


def _rec_risco_incendio(alerta, dados_sensor):
    nivel    = alerta.get('nivel', 'baixo')
    score    = alerta.get('score', 0.0)
    if nivel == 'baixo':
        return None

    temp     = dados_sensor.get('temperatura_ar', 20.0)
    hum_ar   = dados_sensor.get('humidade_ar', 60.0)
    vibracao = dados_sensor.get('vibracao', False)
    vib_nota = (" Foi detectado movimento na area do sensor — "
                "verificar quem esta na parcela.") if vibracao else ""

    if nivel == 'critico':
        urgencia = "URGENTE"
        accao = (
            f"Risco de incendio muito elevado: {temp:.0f} graus e ar muito seco ({hum_ar:.0f}%). "
            f"Nao fazer queimadas nem usar fogo aberto.{vib_nota} "
            f"Verificar se os aceiros estao limpos e se ha acesso para intervencao de emergencia."
        )
    elif nivel == 'alto':
        urgencia = "ALTA"
        accao = (
            f"Condicoes propcias a incendio: {temp:.0f} graus e ar seco ({hum_ar:.0f}%). "
            f"Suspender maquinaria que produza faiscas.{vib_nota} "
            f"Manter vigilancia activa na parcela."
        )
    else:
        urgencia = "MEDIA"
        accao = (
            f"Risco moderado de incendio. "
            f"Evitar queimadas hoje. Monitorar temperatura e humidade."
        )

    return {'categoria': 'Seguranca — Incendio', 'urgencia': urgencia, 'accao': accao, 'score': score}


def _rec_pragas_ml(pragas):
    """Recomendacao do classificador ML — complementar as regras locais."""
    if not pragas.get('detectada', False):
        return None

    tipo      = pragas.get('tipo', 'Desconhecida')
    confianca = int(pragas.get('confianca', 0.0) * 100)
    fonte     = pragas.get('fonte', 'ml')
    nota_fusao = pragas.get('nota_fusao', '')

    orientacoes = {
        'Afideos': (
            "Examinar a face inferior das folhas — afideos formam colonias visiveis a olho nu. "
            "Aplicar extracto de nim ou sabao neutro diluido (acessiveis localmente). "
            "Verificar se ha formigas a proteger os afideos — controlar as formigas reduz a infestacao."
        ),
        'Acaros': (
            "Verificar folhas com aspecto de pontilhado amarelo ou bronze — sinal tipico de acaros. "
            "Calor e secura favorecem os acaros: aumentar humidade foliar e aplicar acaricida disponivel localmente. "
            "Alternar produtos para evitar resistencia."
        ),
        'Mildio': (
            "Inspeccionar folhas: manchas amareladas ou cinzentas com po branco na face inferior. "
            "Reduzir humidade foliar: evitar rega por aspersao e melhorar circulacao de ar. "
            "Aplicar fungicida a base de cobre (sulfato de cobre) — acessivel e eficaz."
        ),
        'Desconhecida': (
            "Fazer inspeccao visual detalhada da parcela. "
            "Recolher amostras de folhas ou frutos afectados para identificacao. "
            "Nao aplicar pesticidas sem confirmar o tipo de praga."
        ),
    }

    nota_str = f" NOTA: {nota_fusao}" if nota_fusao else ""
    return {
        'categoria': 'Proteccao de Culturas (ML)',
        'urgencia':  'ALTA',
        'accao': (
            f"{'Condicoes climaticas indicam' if fonte == 'regras_locais' else 'Modelo detectou'}: "
            f"{tipo} (confianca {confianca}%). "
            f"{orientacoes.get(tipo, orientacoes['Desconhecida'])}"
            f"{nota_str}"
        ),
        'score': pragas.get('confianca', 0.0),
    }


def _rec_pragas_locais(alerta_pragas_locais, dados_sensor, cultura_cfg):
    """Recomendacoes para pragas endemicas de Cuanza-Sul. Retorna lista."""
    recs   = []
    riscos = alerta_pragas_locais.get('riscos', [])
    sinal_colheita = alerta_pragas_locais.get('sinal_colheita_cafe', False)
    nome   = cultura_cfg.get('nome_display', 'Cultura')

    orientacoes_locais = {
        'Broca do cafe': (
            "As condicoes de temperatura e humidade indicam risco de broca do cafe "
            "(Hypothenemus hampei) — principal praga do cafe em Angola. "
            "Inspeccionar os frutos: buracos pequenos na casca sao sinal certo. "
            "Recolher e destruir frutos caidos no chao — servem de refugio para a broca. "
            "Se confirmada, aplicar Beauveria bassiana (fungo biologico) "
            "ou inseticida aprovado para cafe, de manha cedo."
        ),
        'Bicho-mineiro': (
            "Condicoes propcias ao bicho-mineiro (Leucoptera coffeella). "
            "Examinar folhas: manchas esbranquicadas ou galerias serpenteantes confirmam a presenca. "
            "Folhas afectadas ficam castanhas e caem. "
            "Retirar e destruir folhas com galerias. "
            "Aumentar a humidade do solo com irrigacao reduz as condicoes favoraveis ao insecto. "
            "Em infestacoes grandes, aplicar inseticida nas horas mais frescas do dia."
        ),
        'Mildio / Ferrugem': (
            "Alta humidade e temperatura amena criam condicoes para mildio e ferrugem do cafe "
            "(Hemileia vastatrix). "
            "Verificar face inferior das folhas: manchas alaranjadas ou amarelas com po. "
            "Melhorar ventilacao cortando ramos internos (poda de arejamento). "
            "Evitar molhar as folhas ao regar. "
            "Aplicar fungicida cuprico (sulfato de cobre + cal) antes da chuva — barato e eficaz."
        ),
    }

    for risco in riscos:
        praga    = risco.get('praga', '')
        nivel    = risco.get('nivel', 'moderado')
        score    = risco.get('score', 0.0)
        via      = risco.get('via', 'sensor')
        orientacao = orientacoes_locais.get(praga)
        if not orientacao:
            continue

        urgencia = 'ALTA' if nivel == 'alto' else 'MEDIA'
        via_nota = " (confirmado por observacao do agricultor)" if 'observacao' in via else ""

        recs.append({
            'categoria': f'Praga Local — {praga}',
            'urgencia':  urgencia,
            'accao':     orientacao + via_nota,
            'score':     score,
        })

    # Sinal de colheita (formigas nos frutos maduros)
    if sinal_colheita:
        recs.append({
            'categoria': 'Colheita do Cafe',
            'urgencia':  'MEDIA',
            'accao': (
                "Formigas ou frutos avermelhados/amarelos observados — sinal tipico de maturacao. "
                "Inspeccionar a plantacao: frutos com coloracao vermelha ou amarela intensa estao prontos. "
                "Iniciar a apanha selectiva dos frutos maduros para evitar perdas por queda. "
                "Nao colher frutos ainda verdes — aguardar coloracao completa."
            ),
            'score': None,
        })

    return recs


def _rec_mudanca_climatica(alerta):
    nivel         = alerta.get('nivel', 'baixo')
    score         = alerta.get('score', 0.0)
    delta_temp    = alerta.get('delta_temperatura', 0.0)
    delta_pressao = alerta.get('delta_pressao', 0.0)
    intervalo     = alerta.get('intervalo_minutos', 60.0)
    if nivel == 'baixo':
        return None

    intervalo_str = f"{intervalo:.0f} minutos"

    if nivel == 'critico':
        urgencia = "ALTA"
        accao = (
            f"Variacao climatica rapida: temperatura variou {delta_temp:.1f} graus "
            f"e pressao {delta_pressao:.1f} hPa em {intervalo_str}. "
            f"Possivelmente uma frente de tempestade. "
            f"Suspender pulverizacoes e adubacoes foliares. "
            f"Proteger plantas jovens se possivel. "
            f"Consultar previsao meteorologica via radio local ou INAMET."
        )
    elif nivel == 'alto':
        urgencia = "MEDIA"
        accao = (
            f"Variacao climatica relevante: temperatura variou {delta_temp:.1f} graus em {intervalo_str}. "
            f"Evitar operacoes sensiveis (transplantacoes, pulverizacoes) nas proximas horas."
        )
    else:
        urgencia = "BAIXA"
        accao = f"Ligeira variacao climatica em curso (variacao de {delta_temp:.1f} graus). Continuar a monitorar."

    return {'categoria': 'Condicoes Meteorologicas', 'urgencia': urgencia, 'accao': accao, 'score': score}


def _rec_saude_solo(alerta, dados_sensor, cultura_cfg):
    """
    Recomendacao de recuperacao de solo degradado.
    So e gerada quando o nivel indica problema estrutural — nao irriga mais,
    recomenda pousio, pastagem de cobertura ou rotacao.
    """
    nivel = alerta.get('nivel', 'normal')
    score = alerta.get('score', 0.0)
    if nivel == 'normal':
        return None

    hum_solo  = dados_sensor.get('humidade_solo', 50.0)
    dias_seca = dados_sensor.get('dias_sem_chuva')
    nome      = cultura_cfg.get('nome_display', 'Cultura')

    # Para o cafe: nao se aplica rotacao, mas aplica-se pousio parcial
    e_cafe = 'cafe' in nome.lower()

    if nivel == 'degradacao_provavel':
        urgencia = "ALTA"
        if e_cafe:
            accao = (
                f"O solo desta parcela de {nome} mostra sinais de degradacao estrutural "
                f"(humidade {hum_solo:.0f}%" +
                (f", {dias_seca} dias sem chuva" if dias_seca else "") +
                f"). "
                f"Irrigar mais nao resolve — o solo pode estar compactado ou com baixa materia organica. "
                f"Accoes recomendadas: (1) contactar tecnico para analise do solo com canaleta; "
                f"(2) considerar pousio da parcela afectada por uma epoca; "
                f"(3) plantar capim de cobertura (10 cm de altura) para ajudar na recuperacao. "
                f"O cafe nao roda culturas, mas as plantas mortas e caidas devem ser deixadas no solo "
                f"para decompor e devolver nutrientes."
            )
        else:
            accao = (
                f"O solo desta parcela de {nome} mostra sinais de degradacao estrutural "
                f"(humidade {hum_solo:.0f}%" +
                (f", {dias_seca} dias sem chuva" if dias_seca else "") +
                f"). "
                f"Irrigar mais nao resolve — o solo pode estar compactado ou empobrecido. "
                f"Accoes recomendadas: (1) fazer analise laboratorial do solo (pH, P, K) com canaleta; "
                f"(2) parar a plantacao nesta zona e iniciar noutra area (rotacao); "
                f"(3) cobrir o solo com capim de cobertura (10 cm) para recuperar a estrutura; "
                f"(4) se o solo for alcalino, adicionar os nutrientes em falta (potassio, fosforo) "
                f"conforme indicado pela analise."
            )
    else:  # atencao_estrutural
        urgencia = "MEDIA"
        accao = (
            f"Solo com sinais de possivel desgaste estrutural (humidade {hum_solo:.0f}%). "
            f"Monitorar nos proximos dias. Se a humidade continuar baixa mesmo apos irrigacao, "
            f"considerar analise laboratorial do solo para verificar composicao e pH. "
            f"Evitar compactacao adicional com maquinaria pesada nesta parcela."
        )

    return {'categoria': 'Saude do Solo', 'urgencia': urgencia, 'accao': accao, 'score': score}


def _rec_clima_futuro(clima_futuro, dados_sensor, cultura_cfg):
    temp_prev = clima_futuro.get('temperatura_prevista')
    hum_prev  = clima_futuro.get('humidade_prevista')
    nome      = cultura_cfg.get('nome_display', 'Cultura')
    if temp_prev is None and hum_prev is None:
        return None

    temp_max = cultura_cfg.get('temp_max', 32.0)
    temp_min = cultura_cfg.get('temp_min', 18.0)
    solo_min = cultura_cfg.get('humidade_solo_min', 25.0)
    avisos   = []

    if temp_prev is not None:
        if temp_prev > temp_max:
            avisos.append(
                f"temperatura prevista de {temp_prev:.1f} graus ultrapassa o limite para {nome} "
                f"({temp_max:.0f} graus) — considerar irrigacao nas horas mais quentes para arrefecer o solo"
            )
        elif temp_prev < temp_min:
            avisos.append(
                f"temperatura prevista de {temp_prev:.1f} graus abaixo do ideal para {nome} "
                f"({temp_min:.0f} graus) — avaliar proteccao contra frio nocturno"
            )

    if hum_prev is not None and hum_prev < solo_min:
        avisos.append(
            f"humidade prevista do solo ({hum_prev:.1f}%) ficara abaixo do minimo "
            f"({solo_min:.0f}%) — programar irrigacao preventiva"
        )

    if not avisos:
        return None

    return {
        'categoria': 'Previsao Climatica',
        'urgencia':  'MEDIA',
        'accao':     "Previsao indica: " + "; ".join(avisos) + ".",
        'score':     None,
    }


# ---------------------------------------------------------------------------
# Funcao principal
# ---------------------------------------------------------------------------

def gerar_recomendacoes(resultado, dados_sensor=None, cultura=None, culturas=None):
    """
    Gera recomendacoes em linguagem natural a partir do resultado do PredictorML.

    Args:
        resultado:    dict devolvido por PredictorML.prever() ou prever_com_agregacao()
        dados_sensor: dict com os dados brutos do sensor (melhora as mensagens).
                      Pode incluir 'fase_cafe': 'florescimento'|'frutificacao'|
                      'maturacao'|'repouso' — facultativo.
        cultura:      str — cultura principal ('cafe' | 'milho' | 'mandioca' | ...)
        culturas:     list[str] — lista de culturas da fazenda (tem precedência sobre cultura)
                      Ex: ['cafe', 'milho', 'feijao']

    Returns:
        dict com:
            'recomendacoes': lista ordenada por urgencia
            'resumo':        frase de sintese para o agricultor
            'nivel_geral':   'seguro' | 'atencao' | 'alerta' | 'critico'
            'num_alertas':   int
            'culturas_ativas': lista de culturas consideradas
    """
    if not resultado.get('sucesso', False):
        return {
            'recomendacoes': [],
            'resumo':        "Nao foi possivel gerar recomendacoes — erro nos dados.",
            'nivel_geral':   'indisponivel',
            'num_alertas':   0,
            'culturas_ativas': [],
        }

    # Resolver lista de culturas — culturas (lista) tem precedência sobre cultura (string)
    if culturas and isinstance(culturas, list) and len(culturas) > 0:
        culturas_ativas = [c for c in culturas if c and c.strip()]
    elif cultura:
        culturas_ativas = [cultura]
    else:
        culturas_ativas = []

    # Cultura principal para alertas gerais (a primeira da lista)
    cultura_principal = culturas_ativas[0] if culturas_ativas else None
    cultura_cfg       = _resolver_cultura(cultura_principal)

    sensor       = dados_sensor or {}
    alertas      = resultado.get('alertas', {})
    pragas_ml    = resultado.get('pragas', {})
    clima_futuro = resultado.get('clima_futuro', {})

    recs_raw = []

    # 1. Gestao de agua (usa cultura principal)
    r = _rec_estresse_hidrico(alertas.get('estresse_hidrico', {}), sensor, cultura_cfg)
    if r: recs_raw.append(r)

    # 2. Incendio
    r = _rec_risco_incendio(alertas.get('risco_incendio', {}), sensor)
    if r: recs_raw.append(r)

    # 3. Pragas locais — gerar para CADA cultura da fazenda
    for cult in culturas_ativas:
        cfg_cult = _resolver_cultura(cult)
        pragas_locais_cult = alertas.get('pragas_locais', {})
        recs_pragas = _rec_pragas_locais(pragas_locais_cult, sensor, cfg_cult)
        for rec in recs_pragas:
            # Etiquetar com a cultura se houver mais de uma
            if len(culturas_ativas) > 1:
                rec['categoria'] = f"{rec['categoria']} [{cfg_cult.get('nome_display', cult)}]"
            recs_raw.append(rec)

    # 4. Pragas ML (modelo — complementar, ja com resultado de fusao)
    r = _rec_pragas_ml(pragas_ml)
    if r: recs_raw.append(r)

    # 5. Saude estrutural do solo (usa cultura principal)
    r = _rec_saude_solo(alertas.get('saude_solo', {}), sensor, cultura_cfg)
    if r: recs_raw.append(r)

    # 6. Mudanca climatica
    r = _rec_mudanca_climatica(alertas.get('mudanca_climatica', {}))
    if r: recs_raw.append(r)

    # 7. Previsao futura — verificar para CADA cultura (aviso por cultura fora de zona conforto)
    for cult in culturas_ativas:
        cfg_cult = _resolver_cultura(cult)
        r = _rec_clima_futuro(clima_futuro, sensor, cfg_cult)
        if r:
            if len(culturas_ativas) > 1:
                r['categoria'] = f"{r['categoria']} [{cfg_cult.get('nome_display', cult)}]"
            recs_raw.append(r)

    # Remover duplicados de categoria (mesmo texto de accao)
    vistos = set()
    recs_uniq = []
    for rec in recs_raw:
        chave = (rec.get('categoria', ''), rec.get('accao', '')[:80])
        if chave not in vistos:
            vistos.add(chave)
            recs_uniq.append(rec)
    recs_raw = recs_uniq

    # Ordenar por urgencia
    _ordem = {'URGENTE': 0, 'ALTA': 1, 'MEDIA': 2, 'BAIXA': 3}
    recs_raw.sort(key=lambda x: _ordem.get(x.get('urgencia', 'BAIXA'), 9))

    # Nivel geral
    urgencias = {r['urgencia'] for r in recs_raw}
    if   'URGENTE' in urgencias: nivel_geral = 'critico'
    elif 'ALTA'    in urgencias: nivel_geral = 'alerta'
    elif urgencias:              nivel_geral = 'atencao'
    else:                        nivel_geral = 'seguro'

    # Resumo
    if culturas_ativas:
        nomes_display = [_cultura_display(c) for c in culturas_ativas]
        nome_culturas = " / ".join(nomes_display)
    else:
        nome_culturas = "Fazenda"

    hora_str = datetime.now().strftime('%H:%M')

    if nivel_geral == 'seguro':
        resumo = f"[{hora_str}] Condicoes estaveis para {nome_culturas}. Nenhuma accao imediata necessaria."
    elif nivel_geral == 'atencao':
        resumo = f"[{hora_str}] {nome_culturas}: monitorar as condicoes. {len(recs_raw)} ponto(s) a acompanhar."
    elif nivel_geral == 'alerta':
        top    = recs_raw[0]
        resumo = f"[{hora_str}] Atencao ({nome_culturas}) — {top['categoria']}: {top['accao'].split('.')[0]}."
    else:
        top    = recs_raw[0]
        resumo = f"[{hora_str}] ACCAO URGENTE ({nome_culturas}) — {top['categoria']}: {top['accao'].split('.')[0]}."

    return {
        'recomendacoes':  recs_raw,
        'resumo':         resumo,
        'nivel_geral':    nivel_geral,
        'num_alertas':    len(recs_raw),
        'culturas_ativas': culturas_ativas,
    }


# ---------------------------------------------------------------------------
# Formatacao para texto (logs / consola)
# ---------------------------------------------------------------------------

def formatar_recomendacoes(recs_dict):
    """Formata o dict de recomendacoes como texto legivel."""
    linhas = []
    nivel  = recs_dict.get('nivel_geral', '').upper()
    num    = recs_dict.get('num_alertas', 0)
    resumo = recs_dict.get('resumo', '')

    linhas.append('=' * 60)
    linhas.append(f"  {resumo}")
    linhas.append(f"  Nivel geral: {nivel}  |  {num} accao(oes)")
    linhas.append('-' * 60)

    for rec in recs_dict.get('recomendacoes', []):
        linhas.append(f"\n[{rec['urgencia']}] {rec['categoria']}")
        palavras = rec['accao'].split()
        linha    = ''
        for p in palavras:
            if len(linha) + len(p) + 1 > 72:
                linhas.append('  ' + linha)
                linha = p
            else:
                linha = (linha + ' ' + p).strip()
        if linha:
            linhas.append('  ' + linha)

    linhas.append('\n' + '=' * 60)
    return '\n'.join(linhas)