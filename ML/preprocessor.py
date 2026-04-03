"""
Preprocessor para normalizar dados de sensores.
Normaliza valores para escala 0-1 usando MinMaxScaler manual.

Inclui:
  - Validacao de intervalos fisicos antes de normalizar
  - Aviso quando valores chegam fora do intervalo de treino (extrapolacao)
"""

import numpy as np
import pickle
import os


# ---------------------------------------------------------------------------
# Intervalos fisicos validos — valores fora destes limites sao erros de sensor
# ---------------------------------------------------------------------------
LIMITES_FISICOS = {
    'temperatura_ar': (-10.0,  60.0),   # graus Celsius — campo agricola Angola
    'humidade_ar':    (  0.0, 100.0),   # percentagem
    'pressao_ar':     (870.0, 1080.0),  # hPa (870 = ~1300m altitude, 1080 = extremo global)
    'humidade_solo':  (  0.0, 100.0),   # percentagem
}

# Valores de substituicao quando o sensor envia lixo (media razoavel para Angola)
DEFAULTS_CAMPO = {
    'temperatura_ar': 25.0,
    'humidade_ar':    65.0,
    'pressao_ar':    1013.0,
    'humidade_solo':  40.0,
}


class SensorPreprocessor:

    def __init__(self):
        self.min_vals     = None
        self.max_vals     = None
        self.is_fitted    = False
        self.feature_names = ['temperatura_ar', 'humidade_ar', 'pressao_ar', 'humidade_solo']

    # ------------------------------------------------------------------
    # Fit / Transform
    # ------------------------------------------------------------------

    def fit(self, data):
        """
        Ajustar o scaler com dados de treino.
        data: array 2D (n_samples, n_features) — ordem: temp, hum_ar, pressao, hum_solo
        """
        self.min_vals  = np.min(data, axis=0)
        self.max_vals  = np.max(data, axis=0)
        self.is_fitted = True
        return self

    def transform(self, data):
        """
        Normalizar dados para [0, 1].
        data: array 2D ou 1D
        """
        if not self.is_fitted:
            raise ValueError("Preprocessor nao foi ajustado. Use .fit() primeiro.")
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0] = 1.0          # evitar divisao por zero
        return (data - self.min_vals) / range_vals

    def inverse_transform(self, data):
        """Reverter normalizacao."""
        range_vals = self.max_vals - self.min_vals
        range_vals[range_vals == 0] = 1.0
        return data * range_vals + self.min_vals

    # ------------------------------------------------------------------
    # Validacao de sensor
    # ------------------------------------------------------------------

    def validar_e_limpar(self, sensor_dict):
        """
        Valida os valores do sensor contra limites fisicos.

        - Valores fora dos limites fisicos sao substituidos pelo default de campo
          e registados em 'avisos_sensor'.
        - Valores dentro dos limites fisicos mas fora do intervalo de treino
          sao assinalados em 'avisos_extrapolacao' (modelo pode ser menos preciso).

        Retorna:
            (valores_limpos: dict, avisos: dict)
        """
        limpos            = {}
        avisos_sensor     = []
        avisos_extrapol   = []

        for i, campo in enumerate(self.feature_names):
            valor   = sensor_dict.get(campo)
            lim_min, lim_max = LIMITES_FISICOS[campo]
            default = DEFAULTS_CAMPO[campo]

            # 1. Valor ausente ou nao numerico
            if valor is None:
                limpos[campo] = default
                avisos_sensor.append(
                    f"{campo}: valor ausente — usado default {default}"
                )
                continue

            try:
                valor = float(valor)
            except (TypeError, ValueError):
                limpos[campo] = default
                avisos_sensor.append(
                    f"{campo}: valor invalido ({sensor_dict.get(campo)!r}) — usado default {default}"
                )
                continue

            # 2. Fora dos limites fisicos — erro de sensor
            if not (lim_min <= valor <= lim_max):
                limpos[campo] = default
                avisos_sensor.append(
                    f"{campo}: {valor} fora dos limites fisicos [{lim_min}, {lim_max}] "
                    f"— possivel falha de sensor, usado default {default}"
                )
                continue

            limpos[campo] = valor

            # 3. Dentro dos limites fisicos mas fora do intervalo de treino
            if self.is_fitted:
                treino_min = float(self.min_vals[i])
                treino_max = float(self.max_vals[i])
                if valor < treino_min or valor > treino_max:
                    avisos_extrapol.append(
                        f"{campo}: {valor} fora do intervalo de treino "
                        f"[{treino_min:.1f}, {treino_max:.1f}] — previsao pode ser menos precisa"
                    )

        avisos = {}
        if avisos_sensor:
            avisos['erros_sensor']    = avisos_sensor
        if avisos_extrapol:
            avisos['extrapolacao']    = avisos_extrapol

        return limpos, avisos

    # ------------------------------------------------------------------
    # Preparar dados para o modelo
    # ------------------------------------------------------------------

    def prepare_sensor_data(self, sensor_dict):
        """
        Converter dict de sensor em array normalizado [1, 4].

        Valida os valores antes de normalizar. Se houver erros de sensor,
        usa defaults de campo e continua — nunca lanca excepcao por dados sujos.

        Args:
            sensor_dict: {
                'temperatura_ar': float,
                'humidade_ar':    float,
                'pressao_ar':     float,
                'humidade_solo':  float
            }

        Returns:
            array normalizado shape (1, 4)
        """
        limpos, avisos = self.validar_e_limpar(sensor_dict)

        if avisos.get('erros_sensor'):
            for aviso in avisos['erros_sensor']:
                print(f"[SENSOR] {aviso}")
        if avisos.get('extrapolacao'):
            for aviso in avisos['extrapolacao']:
                print(f"[EXTRAPOL] {aviso}")

        valores = np.array([[
            limpos['temperatura_ar'],
            limpos['humidade_ar'],
            limpos['pressao_ar'],
            limpos['humidade_solo'],
        ]])

        return self.transform(valores)

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def save(self, path='ML/models/preprocessor.pkl'):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            pickle.dump(self, f)
        print(f"Preprocessor guardado em {path}")

    @staticmethod
    def load(path='ML/models/preprocessor.pkl'):
        if not os.path.exists(path):
            raise FileNotFoundError(f"Preprocessor nao encontrado em {path}")
        with open(path, 'rb') as f:
            try:
                return pickle.load(f)
            except ModuleNotFoundError:
                class CompatUnpickler(pickle.Unpickler):
                    def find_class(self, module, name):
                        if module == 'preprocessor':
                            from ML.preprocessor import SensorPreprocessor
                            return SensorPreprocessor
                        return super().find_class(module, name)
                f.seek(0)
                return CompatUnpickler(f).load()