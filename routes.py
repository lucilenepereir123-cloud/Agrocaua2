from flask import Blueprint, request, jsonify, Response, stream_with_context
from datetime import datetime, timezone
from models import db, DadosIoT, Previsao, Fazenda, Sensor
from sqlalchemy.exc import SQLAlchemyError
import sys
import os
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity

# Caminhos para o módulo ML
# Em Railway (e produção), ML/ está na mesma pasta que routes.py
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

# Importar ML
try:
    from ML.predictor import fazer_prevensoes
    from ML.recomendador import gerar_recomendacoes
    ML_DISPONIVEL = True
    print("✓ ML carregado com sucesso (predictor + recomendador)")
except ImportError as e:
    print(f"Aviso: ML não disponível — {e}")
    ML_DISPONIVEL = False

api_routes = Blueprint('api', __name__)


# ─────────────────────────────────────────────────────────────
# Helper: descobrir culturas da fazenda a partir do device_id
# ─────────────────────────────────────────────────────────────
def _get_culturas_by_device(device_id):
    """
    Devolve a lista de culturas da fazenda associada ao sensor com o device_id dado.
    Pesquisa em: Sensor.nome == device_id -> Fazenda.culturas
    Fallback: primeira fazenda activa.
    """
    try:
        sensor = Sensor.query.filter(
            db.func.lower(Sensor.nome) == device_id.strip().lower()
        ).first()
        if sensor and sensor.fazenda_id:
            faz = Fazenda.query.get(sensor.fazenda_id)
            if faz:
                culturas = faz.get_culturas_list()
                if culturas:
                    return culturas
                elif faz.cultura:
                    return [faz.cultura]
        # Fallback: fazenda activa mais recente
        faz = Fazenda.query.filter_by(status='active').order_by(Fazenda.created_at.desc()).first()
        if faz:
            culturas = faz.get_culturas_list()
            return culturas if culturas else ([faz.cultura] if faz.cultura else [])
    except Exception as e:
        print(f"[_get_culturas_by_device] Erro: {e}")
    return []


# ─────────────────────────────────────────────────────────────
# POST /api/dados  — Recebe dados IoT, corre ML, guarda tudo
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/dados', methods=['POST'])
def receber_dados():
    dados = request.get_json(silent=True)
    if not dados or not isinstance(dados, dict):
        return jsonify({"erro": "JSON inválido ou ausente"}), 400

    erros = []

    device_id = dados.get('device_id')
    if not isinstance(device_id, str) or not device_id.strip():
        erros.append("device_id obrigatório (string)")

    timestamp = dados.get('timestamp')
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    elif isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            erros.append("timestamp deve ser ISO8601 válido")
    else:
        erros.append("timestamp deve ser string ISO8601")

    gps = dados.get('gps')
    latitude = longitude = None
    if not isinstance(gps, dict):
        erros.append("gps obrigatório (objeto com latitude e longitude)")
    else:
        try:
            latitude  = float(gps.get('latitude'))
            longitude = float(gps.get('longitude'))
        except (TypeError, ValueError):
            erros.append("gps.latitude e gps.longitude devem ser numéricos")

    localizacao = dados.get('localizacao')
    if not isinstance(localizacao, dict):
        erros.append("localizacao deve ser objeto")
    else:
        localizacao = localizacao.get("localizacao")
        if not localizacao:
            erros.append("localizacao obrigatória")

    bme = dados.get('bme280') or {}
    temperatura_ar = humidade_ar = pressao_ar = None
    if isinstance(bme, dict):
        for campo, var in [('temperatura', 'temperatura_ar'), ('humidade', 'humidade_ar'), ('pressao', 'pressao_ar')]:
            if campo in bme:
                try:
                    val = float(bme[campo])
                    if campo == 'temperatura': temperatura_ar = val
                    elif campo == 'humidade':  humidade_ar = val
                    else:                      pressao_ar = val
                except (TypeError, ValueError):
                    erros.append(f"bme280.{campo} deve ser numérico")
    elif bme is not None:
        erros.append("bme280 deve ser objeto")

    solo = dados.get('solo') or {}
    humidade_solo = None
    if isinstance(solo, dict):
        if 'humidade' in solo:
            try:
                humidade_solo = float(solo['humidade'])
            except (TypeError, ValueError):
                erros.append("solo.humidade deve ser numérico")
    elif solo is not None:
        erros.append("solo deve ser objeto")

    vib = dados.get('vibracao') or {}
    vibracao = None
    if isinstance(vib, dict):
        if 'detectada'  in vib: vibracao = bool(vib['detectada'])
        elif 'detejctada' in vib: vibracao = bool(vib['detejctada'])
    elif vib is not None:
        erros.append("vibracao deve ser objeto")

    # visao — campos descomentados conforme requisito
    visao = dados.get('visao') or {}
    detecao_praga = tipo_praga = confianca = None
    if isinstance(visao, dict):
        if 'detecao_praga' in visao:
            detecao_praga = bool(visao['detecao_praga'])
        if 'tipo_praga' in visao:
            if visao['tipo_praga'] is not None and not isinstance(visao['tipo_praga'], str):
                erros.append("visao.tipo_praga deve ser string ou null")
            else:
                tipo_praga = visao['tipo_praga']
        if 'confianca' in visao:
            try:
                if visao['confianca'] is not None:
                    confianca = float(visao['confianca'])
            except (TypeError, ValueError):
                erros.append("visao.confianca deve ser numérico ou null")
    elif visao is not None:
        erros.append("visao deve ser objeto")

    if erros:
        return jsonify({"erro": "Validação falhou", "detalhes": erros}), 400

    record = DadosIoT(
        device_id=device_id, timestamp=timestamp,
        latitude=latitude, longitude=longitude, localizacao=localizacao,
        temperatura_ar=temperatura_ar, humidade_ar=humidade_ar, pressao_ar=pressao_ar,
        humidade_solo=humidade_solo, vibracao=vibracao,
        detecao_praga=detecao_praga, tipo_praga=tipo_praga, confianca=confianca
    )

    try:
        db.session.add(record)
        db.session.commit()
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"erro": "Falha ao salvar", "detalhe": str(e)}), 400
    except Exception:
        db.session.rollback()
        return jsonify({"erro": "Erro interno ao salvar"}), 500

    # ── ML: previsões + recomendações ──
    previsoes_resultado   = {}
    recomendacoes_resultado = {}

    if ML_DISPONIVEL:
        try:
            ultimos = DadosIoT.query.order_by(DadosIoT.timestamp.desc()).limit(20).all()
            dados_historico = [{
                'temperatura_ar': r.temperatura_ar or 20.0,
                'humidade_ar':    r.humidade_ar    or 60.0,
                'pressao_ar':     r.pressao_ar     or 1013.0,
                'humidade_solo':  r.humidade_solo  or 50.0,
                'vibracao':       r.vibracao       or False
            } for r in ultimos]

            dados_atuais = {
                'temperatura_ar': temperatura_ar or 20.0,
                'humidade_ar':    humidade_ar    or 60.0,
                'pressao_ar':     pressao_ar     or 1013.0,
                'humidade_solo':  humidade_solo  or 50.0,
                'vibracao':       vibracao       or False
            }
            dados_historico.insert(0, dados_atuais)

            previsoes_resultado = fazer_prevensoes(dados_lista=dados_historico)

            if previsoes_resultado.get('sucesso', False):
                prever = Previsao(
                    dados_iot_id        = record.id,
                    praga_detectada     = previsoes_resultado['pragas']['detectada'],
                    tipo_praga          = previsoes_resultado['pragas']['tipo'],
                    confianca_praga     = previsoes_resultado['pragas']['confianca'],
                    temperatura_prevista= previsoes_resultado['clima_futuro']['temperatura_prevista'],
                    humidade_prevista   = previsoes_resultado['clima_futuro']['humidade_prevista']
                )
                db.session.add(prever)
                db.session.commit()

                # Buscar culturas da fazenda associada ao sensor
                culturas_fazenda = _get_culturas_by_device(device_id)

                # Gerar recomendações em linguagem natural (chamada ao recomendador.py)
                recomendacoes_resultado = gerar_recomendacoes(
                    resultado    = previsoes_resultado,
                    dados_sensor = dados_atuais,
                    culturas     = culturas_fazenda if culturas_fazenda else None,
                    cultura      = culturas_fazenda[0] if culturas_fazenda else None
                )
        except Exception as e:
            print(f"Erro ao processar ML: {e}")
            previsoes_resultado = {"aviso": "Previsões não disponíveis"}

    return jsonify({
        "status":         "sucesso",
        "mensagem":       "Dados recebidos e armazenados",
        "dados_id":       record.id,
        "previsoes":      previsoes_resultado,
        "recomendacoes":  recomendacoes_resultado
    }), 201


# ─────────────────────────────────────────────────────────────
# GET /api/dados_sensores
# Filtra pelos sensores da fazenda do agricultor autenticado.
# Sem token válido devolve todos os dados (compatibilidade).
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/dados_sensores', methods=['GET'])
def listar_dados():
    from models import User
    # None  → sem autenticação → retorna todos os dados
    # []    → fazenda sem sensores registados → retorna todos os dados (fallback)
    # [..] → filtra pelos device_ids dos sensores da fazenda
    fazenda_sensor_nomes = None
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            user = User.query.get(int(uid))
            if user and user.fazenda_id:
                sensores_fazenda = Sensor.query.filter_by(fazenda_id=user.fazenda_id).all()
                if sensores_fazenda:
                    # Incluir variantes do nome: "sensor-002", "sensor_002", "sensor 002"
                    nomes = set()
                    for s in sensores_fazenda:
                        n = s.nome.strip().lower()
                        nomes.add(n)
                        nomes.add(n.replace('-', '_'))
                        nomes.add(n.replace('_', '-'))
                        nomes.add(n.replace('-', '').replace('_', ''))
                    fazenda_sensor_nomes = list(nomes)
                    print(f"[dados_sensores] Filtrar por sensores fazenda {user.fazenda_id}: {fazenda_sensor_nomes}")
                else:
                    # Fazenda existe mas sem sensores na BD → sem filtro (mostra todos)
                    print(f"[dados_sensores] Fazenda {user.fazenda_id} sem sensores registados — retorna todos os dados")
    except Exception as e:
        print(f"[dados_sensores] JWT opcional falhou: {e}")

    query = DadosIoT.query
    # Só filtra se tiver nomes de sensores; lista vazia ou None → sem filtro
    if fazenda_sensor_nomes:
        query = query.filter(
            db.func.lower(DadosIoT.device_id).in_(fazenda_sensor_nomes)
        )

    registros = query.order_by(DadosIoT.id.desc()).all()
    resultado = []
    for r in registros:
        resultado.append({
            "id": r.id, "device_id": r.device_id,
            "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
            "gps":       {"latitude": r.latitude, "longitude": r.longitude},
            "localizacao": r.localizacao,
            "bme280":    {"temperatura": r.temperatura_ar, "humidade": r.humidade_ar, "pressao": r.pressao_ar},
            "solo":      {"humidade": r.humidade_solo},
            "vibracao":  {"detectada": r.vibracao},
            "visao":     {"detecao_praga": r.detecao_praga, "tipo_praga": r.tipo_praga, "confianca": r.confianca}
        })
    return jsonify(resultado), 200


def _get_last_iot_for_user():
    """Helper: devolve o último registo IoT filtrado pelos sensores da fazenda do user autenticado.
    Fallback para todos os dados se a fazenda não tiver sensores registados ou nenhum match.
    """
    from models import User
    try:
        verify_jwt_in_request(optional=True)
        uid = get_jwt_identity()
        if uid:
            user = User.query.get(int(uid))
            if user and user.fazenda_id:
                sensores_fazenda = Sensor.query.filter_by(fazenda_id=user.fazenda_id).all()
                if sensores_fazenda:
                    # Variantes de nome para tolerância de formato (sensor-002, sensor_002, etc.)
                    nomes = set()
                    for s in sensores_fazenda:
                        n = s.nome.strip().lower()
                        nomes.add(n)
                        nomes.add(n.replace("-", "_"))
                        nomes.add(n.replace("_", "-"))
                        nomes.add(n.replace("-", "").replace("_", ""))
                    r = (DadosIoT.query
                         .filter(db.func.lower(DadosIoT.device_id).in_(list(nomes)))
                         .order_by(DadosIoT.id.desc())
                         .first())
                    if r:
                        return r
                    # Sem match — fallback para último registo global
                    print("[_get_last_iot] Sem match nos sensores da fazenda — usando fallback global")
    except Exception:
        pass
    return DadosIoT.query.order_by(DadosIoT.id.desc()).first()


@api_routes.route('/api/gps', methods=['GET'])
def listar_gps():
    r = _get_last_iot_for_user()
    if not r: return jsonify({"erro": "Nenhum registro encontrado"}), 404
    return jsonify({"id": r.id, "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    "gps": {"latitude": r.latitude, "longitude": r.longitude}}), 200


@api_routes.route('/api/bme280', methods=['GET'])
def listar_bme280():
    r = _get_last_iot_for_user()
    if not r: return jsonify({"erro": "Nenhum registro encontrado"}), 404
    return jsonify({"id": r.id, "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    "bme280": {"temperatura": r.temperatura_ar, "humidade": r.humidade_ar, "pressao": r.pressao_ar}}), 200


@api_routes.route('/api/solo', methods=['GET'])
def listar_solo():
    r = _get_last_iot_for_user()
    if not r: return jsonify({"erro": "Nenhum registro encontrado"}), 404
    return jsonify({"id": r.id, "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    "solo": {"humidade": r.humidade_solo}}), 200


@api_routes.route('/api/vibracao', methods=['GET'])
def listar_vibracao():
    r = _get_last_iot_for_user()
    if not r: return jsonify({"erro": "Nenhum registro encontrado"}), 404
    return jsonify({"id": r.id, "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    "vibracao": {"detectada": r.vibracao}}), 200


@api_routes.route('/api/visao', methods=['GET'])
def listar_visao():
    r = _get_last_iot_for_user()
    if not r: return jsonify({"erro": "Nenhum registro encontrado"}), 404
    return jsonify({"id": r.id, "device_id": r.device_id,
                    "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else None,
                    "visao": {"detecao_praga": r.detecao_praga, "tipo_praga": r.tipo_praga, "confianca": r.confianca}}), 200


# ─────────────────────────────────────────────────────────────
# GET /api/alertas  — Alertas baseados em regras de negócio
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/alertas', methods=['GET'])
def listar_alertas():
    registros = DadosIoT.query.order_by(DadosIoT.id.desc()).limit(100).all()
    resultado = []
    for r in registros:
        if r.detecao_praga:
            resultado.append({"id": f"ALT-{r.id}-praga", "tipo": "Praga",
                "mensagem": f"Detecção de praga: {r.tipo_praga or 'desconhecida'}",
                "severidade": "crítico" if r.confianca and r.confianca > 0.8 else "aviso",
                "timestamp": r.timestamp, "status": "ativo"})
        if r.humidade_solo is not None and r.humidade_solo < 30:
            resultado.append({"id": f"ALT-{r.id}-solo", "tipo": "Solo",
                "mensagem": f"Humidade do solo baixa: {r.humidade_solo:.1f}%",
                "severidade": "crítico", "timestamp": r.timestamp, "status": "ativo"})
        if r.temperatura_ar is not None and (r.temperatura_ar < 15 or r.temperatura_ar > 35):
            resultado.append({"id": f"ALT-{r.id}-temp", "tipo": "Clima",
                "mensagem": f"Temperatura fora dos limites: {r.temperatura_ar:.1f}°C",
                "severidade": "aviso", "timestamp": r.timestamp, "status": "ativo"})
        if r.vibracao:
            resultado.append({"id": f"ALT-{r.id}-vib", "tipo": "Sensor",
                "mensagem": "Vibração detectada no equipamento",
                "severidade": "aviso", "timestamp": r.timestamp, "status": "ativo"})
    return jsonify(resultado), 200


# ─────────────────────────────────────────────────────────────
# GET /api/previsoes/recentes  — Últimas previsões ML da BD
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/previsoes/recentes', methods=['GET'])
def previsoes_recentes():
    """Devolve as últimas previsões ML guardadas na tabela previsoes."""
    limit = request.args.get('limit', 10, type=int)
    previsoes = (Previsao.query
                 .order_by(Previsao.data_criacao.desc())
                 .limit(limit)
                 .all())
    resultado = []
    for p in previsoes:
        resultado.append({
            "id":                  p.id,
            "dados_iot_id":        p.dados_iot_id,
            "praga_detectada":     p.praga_detectada,
            "tipo_praga":          p.tipo_praga,
            "confianca_praga":     p.confianca_praga,
            "temperatura_prevista":p.temperatura_prevista,
            "humidade_prevista":   p.humidade_prevista,
            "data_criacao":        p.data_criacao.isoformat() + 'Z' if p.data_criacao else None
        })
    return jsonify(resultado), 200


# ─────────────────────────────────────────────────────────────
# GET /api/ml/alertas  — Alertas ML agregados + recomendações
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/ml/alertas', methods=['GET'])
def ml_alertas():
    """Corre o predictor nos últimos dados IoT e devolve alertas + recomendações."""
    if not ML_DISPONIVEL:
        return jsonify({"erro": "ML não disponível no servidor"}), 503

    try:
        ultimos = DadosIoT.query.order_by(DadosIoT.timestamp.desc()).limit(20).all()
        if not ultimos:
            return jsonify({
                "alertas": [], "recomendacoes": {},
                "nivel_geral": "seguro", "num_alertas": 0,
                "timestamp": datetime.now(timezone.utc).isoformat() + 'Z'
            }), 200

        dados_historico = []
        dados_recente   = None
        for i, reg in enumerate(ultimos):
            d = {
                'temperatura_ar': reg.temperatura_ar or 20.0,
                'humidade_ar':    reg.humidade_ar    or 60.0,
                'pressao_ar':     reg.pressao_ar     or 1013.0,
                'humidade_solo':  reg.humidade_solo  or 50.0,
                'vibracao':       reg.vibracao       or False
            }
            dados_historico.append(d)
            if i == 0:
                dados_recente = d

        resultado_ml = fazer_prevensoes(dados_lista=dados_historico)

        alertas_fmt = []
        if resultado_ml.get('sucesso'):
            alertas_raw = resultado_ml.get('alertas', {})

            eh = alertas_raw.get('estresse_hidrico', {})
            if eh.get('nivel', 'seguro') != 'seguro':
                alertas_fmt.append({
                    "tipo": "ML-Hidrico", "categoria": "Gestão de Água",
                    "nivel": eh['nivel'],
                    "score": round(eh.get('score', 0) * 100),
                    "mensagem": f"Estresse hídrico {eh['nivel']} — score {round(eh.get('score',0)*100)}%",
                    "severidade": "crítico" if eh['nivel'] == 'crítico' else "aviso",
                    "timestamp": datetime.now(timezone.utc).isoformat() + 'Z', "status": "ativo"
                })

            ri = alertas_raw.get('risco_incendio', {})
            if ri.get('nivel', 'baixo') != 'baixo':
                alertas_fmt.append({
                    "tipo": "ML-Incendio", "categoria": "Segurança — Incêndio",
                    "nivel": ri['nivel'],
                    "score": round(ri.get('score', 0) * 100),
                    "mensagem": f"Risco de incêndio {ri['nivel']} — score {round(ri.get('score',0)*100)}%",
                    "severidade": "crítico" if ri['nivel'] == 'crítico' else "aviso",
                    "timestamp": datetime.now(timezone.utc).isoformat() + 'Z', "status": "ativo"
                })

            pragas = resultado_ml.get('pragas', {})
            if pragas.get('detectada'):
                alertas_fmt.append({
                    "tipo": "ML-Praga", "categoria": "Proteção de Culturas",
                    "nivel": "alto",
                    "score": round((pragas.get('confianca') or 0) * 100),
                    "mensagem": f"Praga detectada: {pragas.get('tipo','Desconhecida')} — {round((pragas.get('confianca') or 0)*100)}% confiança",
                    "severidade": "crítico",
                    "timestamp": datetime.now(timezone.utc).isoformat() + 'Z', "status": "ativo"
                })

            mc = alertas_raw.get('mudanca_climatica', {})
            if mc.get('nivel', 'baixo') != 'baixo':
                alertas_fmt.append({
                    "tipo": "ML-Clima", "categoria": "Meteorologia",
                    "nivel": mc['nivel'],
                    "score": round(mc.get('score', 0) * 100),
                    "mensagem": f"Variação climática detectada — Δtemp {mc.get('delta_temperatura',0):.1f}°C",
                    "severidade": "aviso",
                    "timestamp": datetime.now(timezone.utc).isoformat() + 'Z', "status": "ativo"
                })

        recomendacoes = {}
        if resultado_ml.get('sucesso') and dados_recente:
            # Buscar culturas da fazenda activa mais recente
            culturas_fazenda = []
            try:
                faz = Fazenda.query.filter_by(status='active').order_by(Fazenda.created_at.desc()).first()
                if faz:
                    culturas_fazenda = faz.get_culturas_list()
                    if not culturas_fazenda and faz.cultura:
                        culturas_fazenda = [faz.cultura]
            except Exception:
                pass

            recomendacoes = gerar_recomendacoes(
                resultado    = resultado_ml,
                dados_sensor = dados_recente,
                culturas     = culturas_fazenda if culturas_fazenda else None,
                cultura      = culturas_fazenda[0] if culturas_fazenda else None
            )

        return jsonify({
            "alertas":      alertas_fmt,
            "recomendacoes":recomendacoes,
            "nivel_geral":  recomendacoes.get('nivel_geral', 'seguro'),
            "num_alertas":  len(alertas_fmt),
            "timestamp":    datetime.now(timezone.utc).isoformat() + 'Z'
        }), 200

    except Exception as e:
        import traceback
        print(f"Erro em /api/ml/alertas: {e}")
        print(traceback.format_exc())
        return jsonify({"erro": f"Erro interno: {str(e)}", "detalhe": traceback.format_exc()}), 500


# ─────────────────────────────────────────────────────────────
# POST /api/ml/analisar  — Análise ML a pedido do frontend
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/ml/analisar', methods=['POST'])
def ml_analisar():
    """Recebe dados do frontend, corre o ML e devolve alertas + recomendações."""
    if not ML_DISPONIVEL:
        return jsonify({"erro": "ML não disponível no servidor"}), 503

    corpo = request.get_json(silent=True) or {}
    dados_sensor = corpo.get('dados_sensor') or corpo.get('dados') or None
    dados_lista  = corpo.get('dados_lista')  or None
    cultura      = corpo.get('cultura')      or None
    culturas     = corpo.get('culturas')     or None   # lista de culturas da fazenda
    fazenda_id   = corpo.get('fazenda_id')   or None   # id da fazenda (alternativa)

    # Se veio fazenda_id mas não culturas, buscar na BD
    if not culturas and fazenda_id:
        try:
            faz = Fazenda.query.get(int(fazenda_id))
            if faz:
                culturas = faz.get_culturas_list()
                if not culturas and faz.cultura:
                    culturas = [faz.cultura]
        except Exception:
            pass

    # Se frontend não enviou dados, usar os últimos da BD
    if not dados_sensor and not dados_lista:
        ultimos = DadosIoT.query.order_by(DadosIoT.timestamp.desc()).limit(20).all()
        if not ultimos:
            return jsonify({"erro": "Sem dados disponíveis para análise"}), 422
        dados_lista = [{
            'temperatura_ar': r.temperatura_ar or 20.0,
            'humidade_ar':    r.humidade_ar    or 60.0,
            'pressao_ar':     r.pressao_ar     or 1013.0,
            'humidade_solo':  r.humidade_solo  or 50.0,
            'vibracao':       r.vibracao       or False
        } for r in ultimos]
        dados_sensor = dados_lista[0]

    try:
        if dados_lista:
            resultado_ml = fazer_prevensoes(dados_lista=dados_lista)
        else:
            resultado_ml = fazer_prevensoes(dados_sensor=dados_sensor)

        recomendacoes = {}
        if resultado_ml.get('sucesso'):
            culturas_efetivas = culturas or ([cultura] if cultura else [])
            recomendacoes = gerar_recomendacoes(
                resultado    = resultado_ml,
                dados_sensor = dados_sensor or (dados_lista[0] if dados_lista else {}),
                culturas     = culturas_efetivas if culturas_efetivas else None,
                cultura      = culturas_efetivas[0] if culturas_efetivas else None
            )

        return jsonify({
            "sucesso":       resultado_ml.get('sucesso', False),
            "previsoes":     resultado_ml,
            "recomendacoes": recomendacoes,
            "timestamp":     datetime.now(timezone.utc).isoformat() + 'Z'
        }), 200

    except Exception as e:
        print(f"Erro em /api/ml/analisar: {e}")
        return jsonify({"erro": f"Erro ao analisar dados: {str(e)}"}), 500

# ─────────────────────────────────────────────────────────────
# GET /api/alertas/stream  — SSE: envia alertas em tempo real
# ─────────────────────────────────────────────────────────────
import time

@api_routes.route('/api/alertas/stream', methods=['GET'])
def alertas_stream():
    """Server-Sent Events: envia novos alertas ao cliente em tempo real."""

    def gerar_eventos():
        import json as _json
        ultimo_id  = None
        ultimo_ml  = None   # controlo para não repetir alertas ML idênticos

        while True:
            try:
                r = DadosIoT.query.order_by(DadosIoT.id.desc()).first()
                now_iso = datetime.now(timezone.utc).isoformat() + 'Z'

                if r and r.id != ultimo_id:
                    ultimo_id = r.id
                    alertas = []

                    # ── Alertas de regras simples (sensor directo) ──
                    if r.detecao_praga:
                        alertas.append({
                            "id": f"ALT-{r.id}-praga",
                            "tipo": "Praga",
                            "categoria": "Deteção por Câmara",
                            "mensagem": f"Detecção de praga: {r.tipo_praga or 'desconhecida'}",
                            "severidade": "crítico" if r.confianca and r.confianca > 0.8 else "aviso",
                            "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else now_iso,
                            "status": "ativo"
                        })
                    if r.humidade_solo is not None and r.humidade_solo < 30:
                        alertas.append({
                            "id": f"ALT-{r.id}-solo",
                            "tipo": "Solo",
                            "categoria": "Humidade do Solo",
                            "mensagem": f"Humidade do solo baixa: {r.humidade_solo:.1f}%",
                            "severidade": "crítico",
                            "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else now_iso,
                            "status": "ativo"
                        })
                    if r.temperatura_ar is not None and (r.temperatura_ar < 15 or r.temperatura_ar > 35):
                        alertas.append({
                            "id": f"ALT-{r.id}-temp",
                            "tipo": "Clima",
                            "categoria": "Temperatura",
                            "mensagem": f"Temperatura fora dos limites: {r.temperatura_ar:.1f}°C",
                            "severidade": "aviso",
                            "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else now_iso,
                            "status": "ativo"
                        })
                    if r.vibracao:
                        alertas.append({
                            "id": f"ALT-{r.id}-vib",
                            "tipo": "Sensor",
                            "categoria": "Vibração",
                            "mensagem": "Vibração detectada no equipamento",
                            "severidade": "aviso",
                            "timestamp": r.timestamp.isoformat() + 'Z' if r.timestamp else now_iso,
                            "status": "ativo"
                        })

                    # ── Alertas ML (predictor) ──
                    if ML_DISPONIVEL:
                        try:
                            ultimos = DadosIoT.query.order_by(DadosIoT.timestamp.desc()).limit(10).all()
                            dados_hist = [{
                                'temperatura_ar': x.temperatura_ar or 20.0,
                                'humidade_ar':    x.humidade_ar    or 60.0,
                                'pressao_ar':     x.pressao_ar     or 1013.0,
                                'humidade_solo':  x.humidade_solo  or 50.0,
                                'vibracao':       x.vibracao       or False,
                            } for x in ultimos]

                            res_ml = fazer_prevensoes(dados_lista=dados_hist)
                            if res_ml.get('sucesso'):
                                al = res_ml.get('alertas', {})

                                eh = al.get('estresse_hidrico', {})
                                if eh.get('nivel', 'seguro') not in ('seguro', 'baixo'):
                                    alertas.append({
                                        "id": f"ML-{r.id}-hidrico",
                                        "tipo": "ML-Hidrico",
                                        "categoria": "Gestão de Água (ML)",
                                        "mensagem": f"Estresse hídrico {eh['nivel']} — score {round(eh.get('score',0)*100)}%",
                                        "severidade": "crítico" if eh['nivel'] == 'critico' else "aviso",
                                        "score": round(eh.get('score', 0) * 100),
                                        "timestamp": now_iso, "status": "ativo"
                                    })

                                ri = al.get('risco_incendio', {})
                                if ri.get('nivel', 'baixo') not in ('baixo',):
                                    alertas.append({
                                        "id": f"ML-{r.id}-incendio",
                                        "tipo": "ML-Incendio",
                                        "categoria": "Segurança — Incêndio (ML)",
                                        "mensagem": f"Risco de incêndio {ri['nivel']} — score {round(ri.get('score',0)*100)}%",
                                        "severidade": "crítico" if ri['nivel'] == 'critico' else "aviso",
                                        "score": round(ri.get('score', 0) * 100),
                                        "timestamp": now_iso, "status": "ativo"
                                    })

                                pragas_ml = res_ml.get('pragas', {})
                                if pragas_ml.get('detectada'):
                                    alertas.append({
                                        "id": f"ML-{r.id}-praga",
                                        "tipo": "ML-Praga",
                                        "categoria": "Proteção de Culturas (ML)",
                                        "mensagem": f"Praga: {pragas_ml.get('tipo','Desconhecida')} — {round((pragas_ml.get('confianca') or 0)*100)}% confiança",
                                        "severidade": "crítico",
                                        "score": round((pragas_ml.get('confianca') or 0) * 100),
                                        "timestamp": now_iso, "status": "ativo"
                                    })

                                mc = al.get('mudanca_climatica', {})
                                if mc.get('nivel', 'baixo') not in ('baixo',):
                                    alertas.append({
                                        "id": f"ML-{r.id}-clima",
                                        "tipo": "ML-Clima",
                                        "categoria": "Mudança Climática (ML)",
                                        "mensagem": f"Variação climática {mc['nivel']} — Δtemp {mc.get('delta_temperatura',0):.1f}°C",
                                        "severidade": "aviso",
                                        "score": round(mc.get('score', 0) * 100),
                                        "timestamp": now_iso, "status": "ativo"
                                    })

                                pl = al.get('pragas_locais', {})
                                for risco in pl.get('riscos', []):
                                    if risco.get('nivel') == 'alto':
                                        alertas.append({
                                            "id": f"ML-{r.id}-local-{risco.get('praga','').replace(' ','')}",
                                            "tipo": "ML-PragaLocal",
                                            "categoria": f"Praga Local: {risco.get('praga','')}",
                                            "mensagem": f"Condições climáticas indicam risco alto de {risco.get('praga','')}",
                                            "severidade": "aviso",
                                            "score": round((risco.get('score') or 0) * 100),
                                            "timestamp": now_iso, "status": "ativo"
                                        })
                        except Exception as ml_err:
                            print(f"[SSE] Erro ML: {ml_err}")

                    for alerta in alertas:
                        yield f"data: {_json.dumps(alerta, ensure_ascii=False)}\n\n"

                # Heartbeat a cada 30s
                yield ": heartbeat\n\n"
                time.sleep(30)

            except GeneratorExit:
                break
            except Exception as e:
                print(f"[SSE] Erro: {e}")
                yield f"data: {{}}\n\n"
                time.sleep(30)

    return Response(
        stream_with_context(gerar_eventos()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive'
        }
    )

# ─────────────────────────────────────────────────────────────
# GET /api/culturas  — Lista cultivos suportados + dados agronómicos
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/culturas', methods=['GET'])
def listar_culturas():
    """
    Devolve todos os cultivos suportados pela plataforma com os seus
    parâmetros agronómicos. Útil para o frontend preencher selects
    ao criar/editar fazendas.
    """
    if not ML_DISPONIVEL:
        # Mesmo sem ML, podemos devolver a lista (está no recomendador)
        pass
    try:
        from ML.recomendador import CULTURAS, CULTURA_ALIASES
    except ImportError:
        return jsonify({"erro": "Módulo de culturas não disponível"}), 503

    culturas_out = []
    for key, cfg in CULTURAS.items():
        culturas_out.append({
            "id":            key,
            "nome_display":  cfg.get("nome_display", key.capitalize()),
            "temp_min":      cfg.get("temp_min"),
            "temp_max":      cfg.get("temp_max"),
            "humidade_solo_min": cfg.get("humidade_solo_min"),
            "humidade_solo_max": cfg.get("humidade_solo_max"),
            "humidade_ar_min":   cfg.get("humidade_ar_min"),
            "humidade_ar_max":   cfg.get("humidade_ar_max"),
            "ph_min":        cfg.get("ph_min"),
            "ph_max":        cfg.get("ph_max"),
            "ciclo_dias":    cfg.get("ciclo_dias"),
            "precipitacao_anual_min": cfg.get("precipitacao_anual_min"),
            "precipitacao_anual_max": cfg.get("precipitacao_anual_max"),
            "altitude_min":  cfg.get("altitude_min"),
            "altitude_max":  cfg.get("altitude_max"),
            "observacoes":   cfg.get("observacoes", ""),
            "fases":         list(cfg["fases"].keys()) if "fases" in cfg else [],
        })

    return jsonify({
        "culturas": culturas_out,
        "total":    len(culturas_out),
        "aliases":  CULTURA_ALIASES,
    }), 200


# ─────────────────────────────────────────────────────────────
# GET /api/fazenda/perfil  — Perfil completo da fazenda do agricultor autenticado
# ─────────────────────────────────────────────────────────────
from flask_jwt_extended import jwt_required, get_jwt_identity

@api_routes.route('/api/fazenda/perfil', methods=['GET'])
@jwt_required()
def perfil_fazenda():
    """
    Devolve dados completos da fazenda do agricultor autenticado:
    - Info da fazenda (nome, localização, hectares, culturas)
    - Parâmetros agronómicos de cada cultura
    - Sensores associados
    - Último dado IoT
    - Resumo ML (nível geral + recomendações)
    """
    from models import User, Zona
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or not user.fazenda_id:
        return jsonify({"erro": "Utilizador sem fazenda associada"}), 404

    faz = Fazenda.query.get(user.fazenda_id)
    if not faz:
        return jsonify({"erro": "Fazenda não encontrada"}), 404

    # Culturas com dados agronómicos
    try:
        from ML.recomendador import CULTURAS, _resolver_cultura
    except ImportError:
        CULTURAS = {}
        def _resolver_cultura(c): return {}

    culturas_lista = faz.get_culturas_list()
    culturas_info  = []
    for cult in culturas_lista:
        cfg = _resolver_cultura(cult)
        culturas_info.append({
            "id":           cult,
            "nome_display": cfg.get("nome_display", cult.capitalize()),
            "temp_min":     cfg.get("temp_min"),
            "temp_max":     cfg.get("temp_max"),
            "humidade_solo_min": cfg.get("humidade_solo_min"),
            "humidade_solo_max": cfg.get("humidade_solo_max"),
            "humidade_ar_min":   cfg.get("humidade_ar_min"),
            "humidade_ar_max":   cfg.get("humidade_ar_max"),
            "ph_min":       cfg.get("ph_min"),
            "ph_max":       cfg.get("ph_max"),
            "ciclo_dias":   cfg.get("ciclo_dias"),
            "observacoes":  cfg.get("observacoes", ""),
            "fases":        list(cfg["fases"].keys()) if "fases" in cfg else [],
        })

    # Sensores da fazenda
    sensores = Sensor.query.filter_by(fazenda_id=faz.id).all()

    # Último dado IoT de qualquer sensor desta fazenda
    ultimo_dado = None
    sensor_nomes = [s.nome.lower() for s in sensores]
    if sensor_nomes:
        reg = (DadosIoT.query
               .filter(db.func.lower(DadosIoT.device_id).in_(sensor_nomes))
               .order_by(DadosIoT.timestamp.desc())
               .first())
        if reg:
            ultimo_dado = {
                "device_id":      reg.device_id,
                "timestamp":      reg.timestamp.isoformat() + 'Z',
                "temperatura_ar": reg.temperatura_ar,
                "humidade_ar":    reg.humidade_ar,
                "pressao_ar":     reg.pressao_ar,
                "humidade_solo":  reg.humidade_solo,
                "vibracao":       reg.vibracao,
                "detecao_praga":  reg.detecao_praga,
                "tipo_praga":     reg.tipo_praga,
                "latitude":       reg.latitude,
                "longitude":      reg.longitude,
            }

    # Zonas de cultivo
    zonas = Zona.query.filter_by(fazenda_id=faz.id).all()

    # Resumo ML rápido com o último dado
    resumo_ml = None
    if ML_DISPONIVEL and ultimo_dado:
        try:
            res = fazer_prevensoes(dados_sensor=ultimo_dado)
            from ML.recomendador import gerar_recomendacoes
            recs = gerar_recomendacoes(
                resultado    = res,
                dados_sensor = ultimo_dado,
                culturas     = culturas_lista if culturas_lista else None,
                cultura      = culturas_lista[0] if culturas_lista else None,
            )
            resumo_ml = {
                "nivel_geral": recs.get("nivel_geral", "seguro"),
                "resumo":      recs.get("resumo", ""),
                "num_alertas": recs.get("num_alertas", 0),
            }
        except Exception as e:
            resumo_ml = {"erro": str(e)}

    return jsonify({
        "fazenda":        faz.to_dict(),
        "culturas_info":  culturas_info,
        "sensores":       [s.to_dict() for s in sensores],
        "zonas":          [z.to_dict() for z in zonas],
        "ultimo_dado":    ultimo_dado,
        "resumo_ml":      resumo_ml,
    }), 200

# ─────────────────────────────────────────────────────────────
# GET /api/fazenda/sensores  — Sensores registados na fazenda do agricultor
# Rota leve (sem ML) usada pela página de sensores do dashboard
# ─────────────────────────────────────────────────────────────
@api_routes.route('/api/fazenda/sensores', methods=['GET'])
@jwt_required()
def fazenda_sensores():
    from models import User
    uid  = int(get_jwt_identity())
    user = User.query.get(uid)
    if not user or not user.fazenda_id:
        return jsonify({"erro": "Utilizador sem fazenda associada"}), 404

    faz = Fazenda.query.get(user.fazenda_id)
    if not faz:
        return jsonify({"erro": "Fazenda não encontrada"}), 404

    sensores = Sensor.query.filter_by(fazenda_id=faz.id).all()

    # ── Último dado IoT POR SENSOR (não um único global) ──────────────
    # Permite mostrar na tabela: quando cada sensor comunicou pela última vez
    # e se tem dados reais (vs. nunca comunicou)
    sensores_out = []
    ultimo_dado_global = None  # o mais recente de todos, para compatibilidade

    for s in sensores:
        nome_lower = s.nome.strip().lower()
        # Variantes de nome para tolerância (sensor-002 / sensor_002 / sensor002)
        variantes = {nome_lower,
                     nome_lower.replace('-', '_'),
                     nome_lower.replace('_', '-'),
                     nome_lower.replace('-', '').replace('_', '')}

        reg = (DadosIoT.query
               .filter(db.func.lower(DadosIoT.device_id).in_(list(variantes)))
               .order_by(DadosIoT.timestamp.desc())
               .first())

        sensor_dict = s.to_dict()
        if reg:
            sensor_dict['ultimo_dado'] = {
                "device_id":      reg.device_id,
                "timestamp":      reg.timestamp.isoformat() + 'Z' if reg.timestamp else None,
                "temperatura_ar": reg.temperatura_ar,
                "humidade_ar":    reg.humidade_ar,
                "humidade_solo":  reg.humidade_solo,
                "detecao_praga":  reg.detecao_praga,
            }
            # Manter o mais recente como global
            if (ultimo_dado_global is None or
                    (reg.timestamp and (ultimo_dado_global['_ts'] is None or
                     reg.timestamp.isoformat() + 'Z' > ultimo_dado_global['_ts']))):
                ultimo_dado_global = {**sensor_dict['ultimo_dado'], '_ts': reg.timestamp.isoformat() + 'Z' if reg.timestamp else None}
        else:
            # Sensor nunca comunicou dados IoT
            sensor_dict['ultimo_dado'] = None

        sensores_out.append(sensor_dict)

    # Limpar campo interno _ts do objeto global antes de enviar
    if ultimo_dado_global:
        ultimo_dado_global.pop('_ts', None)

    return jsonify({
        "fazenda_id":   faz.id,
        "fazenda_nome": faz.nome,
        "sensores":     sensores_out,
        "ultimo_dado":  ultimo_dado_global,
    }), 200