"""
Interface para fazer previsoes com os modelos ML.
Carrega modelos treinados e faz previsoes em tempo real.
Usa apenas pickle e numpy (sem dependencias externas).
"""

import pickle
import numpy as np
import os

try:
    from .preprocessor import SensorPreprocessor
    from .ml_models import SimpleLogisticRegression, SimpleLinearRegression
except ImportError:
    from preprocessor import SensorPreprocessor
    from ml_models import SimpleLogisticRegression, SimpleLinearRegression


class PredictorML:
    """Interface unificada para previsoes."""

    def __init__(self, model_dir=None):
        if model_dir is None:
            model_dir = os.path.join(os.path.dirname(__file__), 'models')
        self.model_dir   = model_dir
        self.preprocessor = None
        self.clf_praga    = None
        self.clf_tipo     = None
        self.reg_temp     = None
        self.reg_humidade = None
        self._carrega_modelos()

    # ------------------------------------------------------------------
    # Carregamento de modelos
    # ------------------------------------------------------------------

    def _carrega_modelos(self):
        from io import BytesIO

        def carregar_modelo(caminho):
            with open(caminho, 'rb') as f:
                dados = f.read()
            try:
                return pickle.loads(dados)
            except (AttributeError, ModuleNotFoundError):
                class CustomUnpickler(pickle.Unpickler):
                    def find_class(self, module, name):
                        if name in ('SimpleLogisticRegression', 'SimpleLinearRegression'):
                            return globals().get(name) or SimpleLogisticRegression
                        return super().find_class(module, name)
                return CustomUnpickler(BytesIO(dados)).load()

        try:
            self.preprocessor = SensorPreprocessor.load(
                os.path.join(self.model_dir, 'preprocessor.pkl'))
            print("OK Preprocessor carregado")
        except FileNotFoundError:
            print("AVISO Preprocessor nao encontrado. Execute train.py primeiro")
            raise

        for attr, ficheiro, label in [
            ('clf_praga',    'praga_detector.pkl',        'Detector de pragas'),
            ('clf_tipo',     'tipo_praga_classifier.pkl', 'Classificador de tipos'),
            ('reg_temp',     'temperatura_predictor.pkl', 'Preditor de temperatura'),
            ('reg_humidade', 'humidade_predictor.pkl',    'Preditor de humidade'),
        ]:
            try:
                setattr(self, attr, carregar_modelo(os.path.join(self.model_dir, ficheiro)))
                print(f"OK {label} carregado")
            except FileNotFoundError:
                print(f"AVISO {label} nao encontrado")
            except Exception as e:
                print(f"AVISO Erro ao carregar {label}: {e}")

    # ------------------------------------------------------------------
    # Previsao principal
    # ------------------------------------------------------------------

    def prever(self, dados_sensor, dados_sensor_anterior=None):
        """
        Fazer todas as previsoes para uma leitura de sensor.

        Campos obrigatorios em dados_sensor:
            'temperatura_ar'    float  (graus Celsius)
            'humidade_ar'       float  (%)
            'pressao_ar'        float  (hPa)
            'humidade_solo'     float  (%)

        Campos opcionais (melhoram as recomendacoes sem sensores adicionais):
            'vibracao'          bool   (sensor de vibracao; default False)
            'intervalo_minutos' float  (minutos desde a leitura anterior; default 60)
            'dias_sem_chuva'    int    (dias sem chuva — o agricultor informa)
            'observacao_manual' str    (nota do agricultor: 'formigas', 'manchas', etc.)
            'fase_cafe'         str    ('florescimento'|'frutificacao'|'maturacao'|'repouso')
            'timestamp'         str    (ISO 8601 opcional — para calculo automatico de intervalo)

        dados_sensor_anterior: dict opcional com a leitura anterior do sensor,
            para calcular deltas de mudanca climatica com contexto temporal correcto.
        """
        # Preprocessamento com validacao de sensor
        X = self.preprocessor.prepare_sensor_data(dados_sensor)

        resultado = {
            'sucesso':      True,
            'pragas':       {'detectada': False, 'tipo': None, 'confianca': 0.0},
            'clima_futuro': {'temperatura_prevista': None, 'humidade_prevista': None},
        }

        # ===== PREVISOES ML =====
        try:
            if self.clf_praga:
                y_praga = self.clf_praga.predict(X)[0]
                y_proba = self.clf_praga.predict_proba(X)[0]
                resultado['pragas']['detectada'] = bool(y_praga)
                resultado['pragas']['confianca'] = float(max(y_proba))

                if y_praga and self.clf_tipo:
                    try:
                        y_tipo    = self.clf_tipo.predict(X)[0]
                        tipos_map = {0: 'Nenhuma', 1: 'Afideos', 2: 'Acaros', 3: 'Mildio'}
                        resultado['pragas']['tipo'] = tipos_map.get(y_tipo, 'Desconhecida')
                    except Exception:
                        resultado['pragas']['tipo'] = 'Desconhecida'

            if self.reg_temp:
                resultado['clima_futuro']['temperatura_prevista'] = round(
                    float(self.reg_temp.predict(X)[0]), 1)

            if self.reg_humidade:
                y_hum = np.clip(self.reg_humidade.predict(X)[0], 0, 100)
                resultado['clima_futuro']['humidade_prevista'] = round(float(y_hum), 1)

        except Exception as e:
            resultado['sucesso'] = False
            resultado['erro']    = str(e)
            print(f"Erro ao prever: {e}")

        # ===== ALERTAS POR REGRAS =====
        temp       = dados_sensor.get('temperatura_ar', 20.0)
        hum_ar     = dados_sensor.get('humidade_ar', 60.0)
        hum_solo   = dados_sensor.get('humidade_solo', 50.0)
        vibracao   = bool(dados_sensor.get('vibracao', False))
        pressao    = dados_sensor.get('pressao_ar', 1013.0)
        dias_seca  = dados_sensor.get('dias_sem_chuva')
        obs_manual = dados_sensor.get('observacao_manual', '')
        intervalo  = float(dados_sensor.get('intervalo_minutos', 60.0))

        temp_ant    = dados_sensor_anterior.get('temperatura_ar', temp)   if dados_sensor_anterior else temp
        pressao_ant = dados_sensor_anterior.get('pressao_ar', pressao)    if dados_sensor_anterior else pressao

        pragas_locais = self.calcula_risco_pragas_locais(temp, hum_ar, hum_solo, obs_manual)

        alertas = {
            'estresse_hidrico': self.calcula_alerta_estresse_hidrico(
                temp, hum_ar, hum_solo, dias_seca),
            'risco_incendio':   self.calcula_risco_incendio(
                temp, hum_ar, hum_solo, vibracao),
            'mudanca_climatica': self.calcula_mudanca_climatica(
                temp, temp_ant, pressao, pressao_ant, intervalo),
            'pragas_locais':    pragas_locais,
            'saude_solo':       self.calcula_saude_solo(
                hum_solo, dias_seca, obs_manual),
        }

        # Fusao ML + regras: reconciliar se os dois sistemas discordam
        resultado['alertas']           = alertas
        resultado['pragas']            = self._fusao_pragas(resultado['pragas'], pragas_locais)
        resultado['mensagens_analise'] = self._mensagens_analise(alertas)

        return resultado

    # ------------------------------------------------------------------
    # Agregacao
    # ------------------------------------------------------------------

    def prever_com_agregacao(self, dados_lista):
        """Previsoes a partir de uma lista de leituras de sensores."""
        if not isinstance(dados_lista, list) or len(dados_lista) == 0:
            return {'sucesso': False, 'erro': 'dados_lista deve ser lista nao vazia'}

        def _extrair(campo):
            return [float(d[campo]) for d in dados_lista
                    if d.get(campo) is not None]

        temperaturas  = _extrair('temperatura_ar')
        humidades_ar  = _extrair('humidade_ar')
        pressao       = _extrair('pressao_ar')
        humidade_solo = _extrair('humidade_solo')

        if not all([temperaturas, humidades_ar, pressao, humidade_solo]):
            return {'sucesso': False, 'erro': 'dados_lista incompleto para agregacao'}

        # Calcular intervalo real se houver timestamps
        intervalo = self._calcular_intervalo(dados_lista)

        vibracoes  = [bool(d.get('vibracao', False)) for d in dados_lista]
        dias_seca  = next((d['dias_sem_chuva'] for d in reversed(dados_lista)
                           if d.get('dias_sem_chuva') is not None), None)
        obs_manual = next((d.get('observacao_manual', '') for d in reversed(dados_lista)
                           if d.get('observacao_manual')), '')

        dados_agrupados = {
            'temperatura_ar':    float(np.mean(temperaturas)),
            'humidade_ar':       float(np.mean(humidades_ar)),
            'pressao_ar':        float(np.mean(pressao)),
            'humidade_solo':     float(np.mean(humidade_solo)),
            'vibracao':          any(vibracoes),
            'dias_sem_chuva':    dias_seca,
            'observacao_manual': obs_manual,
            'intervalo_minutos': intervalo,
        }

        dados_anterior = dados_lista[0] if len(dados_lista) > 1 else None
        previsao       = self.prever(dados_agrupados, dados_sensor_anterior=dados_anterior)

        previsao['analise_agregada'] = {
            'num_leituras':         len(dados_lista),
            'temperatura_range':    (min(temperaturas), max(temperaturas)),
            'humidade_range':       (min(humidades_ar), max(humidades_ar)),
            'variacao_temperatura': round(max(temperaturas) - min(temperaturas), 2),
            'variacao_humidade':    round(max(humidades_ar) - min(humidades_ar), 2),
            'intervalo_minutos_usado': intervalo,
        }
        return previsao

    def _calcular_intervalo(self, dados_lista):
        """
        Calcula o intervalo real entre a primeira e ultima leitura
        se os dicts tiverem campo 'timestamp' (ISO 8601).
        Caso contrario devolve 60 minutos como default.
        """
        try:
            from datetime import datetime
            fmt = '%Y-%m-%dT%H:%M:%S'
            t0  = datetime.fromisoformat(dados_lista[0]['timestamp'])
            t1  = datetime.fromisoformat(dados_lista[-1]['timestamp'])
            minutos = abs((t1 - t0).total_seconds()) / 60.0
            return max(1.0, minutos)
        except (KeyError, ValueError, TypeError):
            return 60.0

    # ------------------------------------------------------------------
    # Fusao de alertas ML + regras
    # ------------------------------------------------------------------

    def _fusao_pragas(self, pragas_ml, pragas_locais):
        """
        Reconcilia o classificador ML com as regras climaticas locais.

        Logica:
          - Se ML nao detectou praga mas regras locais detectaram com score alto,
            elevar a deteccao ML para confirmado (as regras conhecem as pragas locais).
          - Se ML detectou uma praga mas as regras locais apontam para outra com
            score superior, adicionar nota de conflito e dar prioridade a regra local.
          - Se ambos concordam, reforcar a confianca.
        """
        resultado = dict(pragas_ml)
        riscos_altos = [r for r in pragas_locais.get('riscos', []) if r['nivel'] == 'alto']

        if not resultado.get('detectada') and riscos_altos:
            # ML nao detectou, mas regras locais indicam risco alto — elevar
            melhor = max(riscos_altos, key=lambda r: r['score'])
            resultado['detectada']      = True
            resultado['tipo']           = melhor['praga']
            resultado['confianca']      = round(melhor['score'], 3)
            resultado['fonte']          = 'regras_locais'
            resultado['nota_fusao']     = (
                f"ML nao detectou praga mas condicoes climaticas indicam risco alto de "
                f"{melhor['praga']} — usando alerta por regras climaticas."
            )

        elif resultado.get('detectada') and riscos_altos:
            # Ambos detectaram — verificar se concordam
            tipos_locais = {r['praga'] for r in riscos_altos}
            tipo_ml      = resultado.get('tipo', '')
            # Verificar sobreposicao (ex: ML disse "Mildio", regras dizem "Mildio/Ferrugem")
            concordam = any(tipo_ml.lower() in t.lower() or t.lower() in tipo_ml.lower()
                            for t in tipos_locais)
            if concordam:
                resultado['confianca'] = min(1.0, resultado['confianca'] * 1.15)
                resultado['fonte']     = 'ml+regras_concordam'
            else:
                melhor_local = max(riscos_altos, key=lambda r: r['score'])
                resultado['fonte']      = 'ml+regras_divergem'
                resultado['nota_fusao'] = (
                    f"ML indica {tipo_ml}, mas condicoes climaticas apontam para "
                    f"{melhor_local['praga']} (score {melhor_local['score']:.2f}). "
                    f"Inspeccionar a parcela para confirmar."
                )

        return resultado

    # ------------------------------------------------------------------
    # Calculos de alertas
    # ------------------------------------------------------------------

    def calcula_alerta_estresse_hidrico(self, temperatura_ar, humidade_ar,
                                        humidade_solo, dias_sem_chuva=None):
        """
        Score de estresse hidrico (0..1).
        dias_sem_chuva (int, opcional): dado facultativo do agricultor.
        Cada dia sem chuva agrava ligeiramente o score (max +0.20).
        """
        temp_norm   = max(0.0, min((temperatura_ar - 20.0) / 20.0, 1.0))
        hum_ar_norm = 1.0 - max(0.0, min(humidade_ar,  100.0)) / 100.0
        solo_norm   = 1.0 - max(0.0, min(humidade_solo, 100.0)) / 100.0
        score       = 0.20 * temp_norm + 0.30 * hum_ar_norm + 0.50 * solo_norm

        if dias_sem_chuva is not None:
            score = min(1.0, score + min(0.20, int(dias_sem_chuva) * 0.01))

        if   score >= 0.75: nivel = 'critico'
        elif score >= 0.50: nivel = 'alto'
        elif score >= 0.30: nivel = 'moderado'
        elif score >= 0.15: nivel = 'baixo'
        else:               nivel = 'seguro'

        return {'nivel': nivel, 'score': round(score, 3), 'dias_sem_chuva': dias_sem_chuva}

    def calcula_risco_incendio(self, temperatura_ar, humidade_ar,
                               humidade_solo, vibracao=False):
        """
        Score de risco de incendio (0..1).
        Pesos: temp 40%, ar 25%, solo 15%, vibracao 20%.
        """
        temp_norm   = max(0.0, min((temperatura_ar - 15.0) / 35.0, 1.0))
        hum_ar_norm = 1.0 - max(0.0, min(humidade_ar,  100.0)) / 100.0
        solo_norm   = 1.0 - max(0.0, min(humidade_solo, 100.0)) / 100.0
        vib_norm    = 1.0 if vibracao else 0.0
        score       = 0.40 * temp_norm + 0.25 * hum_ar_norm + 0.15 * solo_norm + 0.20 * vib_norm

        if   score >= 0.75: nivel = 'critico'
        elif score >= 0.50: nivel = 'alto'
        elif score >= 0.25: nivel = 'moderado'
        else:               nivel = 'baixo'

        return {'nivel': nivel, 'score': round(score, 3)}

    def calcula_mudanca_climatica(self, temp_atual, temp_anterior,
                                  pressao_atual, pressao_anterior,
                                  intervalo_minutos=60.0):
        """
        Score de mudanca climatica normalizado por hora.
        Limiares: >5 graus/hora ou >10 hPa/hora sao variacoes rapidas e preocupantes.
        """
        delta_temp    = abs(temp_atual    - temp_anterior)
        delta_pressao = abs(pressao_atual - pressao_anterior)
        horas         = max(intervalo_minutos / 60.0, 1.0 / 60.0)
        score         = min(1.0,
                            (delta_temp    / horas / 5.0)  * 0.6 +
                            (delta_pressao / horas / 10.0) * 0.4)

        if   score >= 0.70: nivel = 'critico'
        elif score >= 0.40: nivel = 'alto'
        elif score >= 0.20: nivel = 'moderado'
        else:               nivel = 'baixo'

        return {
            'nivel':             nivel,
            'score':             round(score, 3),
            'delta_temperatura': round(delta_temp, 2),
            'delta_pressao':     round(delta_pressao, 2),
            'intervalo_minutos': round(intervalo_minutos, 1),
        }

    def calcula_risco_pragas_locais(self, temperatura_ar, humidade_ar,
                                    humidade_solo, observacao_manual=''):
        """
        Deteccao de pragas endemicas de Cuanza-Sul por condicoes climaticas.

        Pragas monitorizadas (sem sensor adicional):
          Broca do cafe     (Hypothenemus hampei)  — temp>=23 + hum_ar>=70%
          Bicho-mineiro     (Leucoptera coffeella) — temp>=22 + ar seco + solo seco
          Mildio / Ferrugem (Hemileia vastatrix)   — 15-28 graus + hum_ar>=80%

        observacao_manual (str, opcional): texto livre do agricultor —
          'formigas', 'buracos', 'manchas', 'mildio', etc.
        """
        riscos = []
        obs    = observacao_manual.lower() if observacao_manual else ''

        # Broca do cafe
        s = 0.0
        if temperatura_ar >= 23.0:
            s += min(1.0, (temperatura_ar - 23.0) / 7.0) * 0.6
        if humidade_ar >= 70.0:
            s += min(1.0, (humidade_ar - 70.0) / 20.0) * 0.4
        if s >= 0.40 or 'broca' in obs:
            riscos.append({'praga': 'Broca do cafe',
                           'nome_cientifico': 'Hypothenemus hampei',
                           'nivel': 'alto' if s >= 0.65 else 'moderado',
                           'score': round(s, 3),
                           'via': 'observacao+sensor' if 'broca' in obs else 'sensor'})

        # Bicho-mineiro
        s = 0.0
        if temperatura_ar >= 22.0:
            s += min(1.0, (temperatura_ar - 22.0) / 8.0) * 0.5
        if humidade_ar < 60.0:
            s += min(1.0, (60.0 - humidade_ar) / 40.0) * 0.3
        if humidade_solo < 35.0:
            s += min(1.0, (35.0 - humidade_solo) / 35.0) * 0.2
        if s >= 0.35 or any(p in obs for p in ('mineiro', 'buracos', 'galerias')):
            riscos.append({'praga': 'Bicho-mineiro',
                           'nome_cientifico': 'Leucoptera coffeella',
                           'nivel': 'alto' if s >= 0.60 else 'moderado',
                           'score': round(s, 3),
                           'via': 'sensor'})

        # Mildio / Ferrugem
        s = 0.0
        if 15.0 <= temperatura_ar <= 28.0 and humidade_ar >= 80.0:
            s += min(1.0, (humidade_ar - 80.0) / 20.0) * 0.7
            s += (1.0 - abs(temperatura_ar - 21.5) / 13.5) * 0.3
        if s >= 0.30 or any(p in obs for p in ('manchas', 'mildio', 'ferrugem', 'po')):
            riscos.append({'praga': 'Mildio / Ferrugem',
                           'nome_cientifico': 'Hemileia vastatrix',
                           'nivel': 'alto' if s >= 0.55 else 'moderado',
                           'score': round(s, 3),
                           'via': 'sensor'})

        sinal_colheita = any(p in obs for p in
                             ('formigas', 'colheita', 'maduro', 'vermelho', 'amarelo'))

        _ord = {'alto': 2, 'moderado': 1, 'baixo': 0}
        nivel_geral = max((r['nivel'] for r in riscos),
                          key=lambda n: _ord.get(n, 0), default='baixo')

        return {
            'nivel':                 nivel_geral,
            'riscos':                riscos,
            'sinal_colheita_cafe':   sinal_colheita,
            'num_pragas_detectadas': len(riscos),
        }

    def calcula_saude_solo(self, humidade_solo, dias_sem_chuva=None,
                           observacao_manual=''):
        """
        Avalia se o solo pode estar estruturalmente degradado.

        Um solo degradado nao retém agua mesmo com irrigacao regular.
        O sistema nao tem sensor de pH nem de textura, mas pode inferir
        degradacao provavel por:
          - humidade do solo cronicamente baixa mesmo com irrigacao
          - seca prolongada (dias_sem_chuva elevado)
          - observacao manual do agricultor

        Retorna um nivel de alerta e uma recomendacao de accao.
        """
        obs   = observacao_manual.lower() if observacao_manual else ''
        score = 0.0

        # Solo muito seco
        if humidade_solo < 15.0:
            score += 0.5
        elif humidade_solo < 25.0:
            score += 0.3

        # Seca prolongada agrava
        if dias_sem_chuva is not None:
            if dias_sem_chuva >= 30:
                score += 0.4
            elif dias_sem_chuva >= 14:
                score += 0.2

        # Observacao manual
        indicadores_degradacao = ('solo duro', 'solo rachado', 'erosao', 'degradado',
                                  'nao absorve', 'agua escorre', 'compactado')
        if any(p in obs for p in indicadores_degradacao):
            score += 0.4

        score = min(1.0, score)

        if   score >= 0.70: nivel = 'degradacao_provavel'
        elif score >= 0.40: nivel = 'atencao_estrutural'
        else:               nivel = 'normal'

        return {'nivel': nivel, 'score': round(score, 3)}

    # ------------------------------------------------------------------
    # Mensagens de analise (painel tecnico)
    # ------------------------------------------------------------------

    def _mensagens_analise(self, alertas):
        eh  = alertas['estresse_hidrico']
        ri  = alertas['risco_incendio']
        mc  = alertas['mudanca_climatica']
        pl  = alertas['pragas_locais']
        ss  = alertas['saude_solo']

        pragas_str   = ', '.join(r['praga'] for r in pl['riscos']) if pl['riscos'] else 'nenhuma'
        colheita_str = ' | Sinal de maturacao/colheita detectado.' if pl['sinal_colheita_cafe'] else ''
        seca_str     = f"+{eh['dias_sem_chuva']}d seca" if eh.get('dias_sem_chuva') else ''

        return {
            'estresse_hidrico': {
                'simples': f"Solo seco e ar quente -> risco {eh['nivel'].upper()} ({int(eh['score']*100)}%)",
                'tecnico': f"Score estresse hidrico: {eh['score']} (temp+hum_ar+solo{seca_str})",
            },
            'risco_incendio': {
                'simples': f"Condicao propicia a fogo -> risco {ri['nivel'].upper()} ({int(ri['score']*100)}%)",
                'tecnico': f"Score incendio: {ri['score']} (temp 40%+hum_ar 25%+solo 15%+vibracao 20%)",
            },
            'mudanca_climatica': {
                'simples': (f"Variacao climatica -> nivel {mc['nivel'].upper()} "
                            f"(Dtemp {mc['delta_temperatura']}C, Dpressao {mc['delta_pressao']} hPa "
                            f"em {mc['intervalo_minutos']} min)"),
                'tecnico': f"Score mudanca climatica: {mc['score']} normalizado por hora",
            },
            'pragas_locais': {
                'simples': f"Pragas locais detectadas: {pragas_str}{colheita_str}",
                'tecnico': str([r['praga'] + ' (' + r['nivel'] + ')' for r in pl['riscos']]),
            },
            'saude_solo': {
                'simples': f"Saude estrutural do solo: {ss['nivel']} (score {ss['score']})",
                'tecnico': f"Score saude solo: {ss['score']} (hum_solo + dias_seca + observacao)",
            },
        }


# ------------------------------------------------------------------
# Instancia global
# ------------------------------------------------------------------

_predictor = None


def obter_predictor():
    global _predictor
    if _predictor is None:
        _predictor = PredictorML()
    return _predictor


def fazer_prevensoes(dados_sensor=None, dados_lista=None, dados_sensor_anterior=None):
    """
    Funcao de conveniencia para fazer previsoes.

    Args:
        dados_sensor:          dict com dados de um unico sensor
        dados_lista:           lista de dicts com dados de multiplos sensores (preferido)
        dados_sensor_anterior: dict opcional com a leitura anterior (para delta climatico)

    Campos opcionais que melhoram as recomendacoes sem sensores adicionais:
        'dias_sem_chuva'    int    dias consecutivos sem chuva — o agricultor informa
        'observacao_manual' str    nota livre: 'formigas', 'manchas amarelas', etc.
        'intervalo_minutos' float  minutos decorridos desde a leitura anterior
        'fase_cafe'         str    florescimento | frutificacao | maturacao | repouso
        'timestamp'         str    ISO 8601 — permite calcular intervalo automaticamente
    """
    predictor = obter_predictor()
    if dados_lista:
        return predictor.prever_com_agregacao(dados_lista)
    elif dados_sensor:
        return predictor.prever(dados_sensor, dados_sensor_anterior=dados_sensor_anterior)
    else:
        return {'sucesso': False, 'erro': 'Nenhum dado fornecido'}