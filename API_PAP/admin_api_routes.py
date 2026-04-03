import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func
from models import db, User, Fazenda, Sensor, Log, DadosIoT, Mensagem, Zona
from auth_routes import add_log
from email_service import (
    send_message_reply, send_critical_alert_to_admin,
    send_contact_form_confirmation, send_contact_form_to_admin,
    send_welcome_email
)

admin_api_bp = Blueprint("admin_api", __name__, url_prefix="/api/admin")


# ─────────────────────────────────────────────
# DECORADOR: exige superadmin ou admin
# ─────────────────────────────────────────────
def admin_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        u = User.query.get(int(get_jwt_identity()))
        if not u or u.role not in ("superadmin", "admin"):
            return jsonify({"erro": "Acesso negado. Apenas administradores."}), 403
        return f(*args, **kwargs)
    return wrapper


def superadmin_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        u = User.query.get(int(get_jwt_identity()))
        if not u or u.role != "superadmin":
            return jsonify({"erro": "Acesso negado. Apenas super administradores."}), 403
        return f(*args, **kwargs)
    return wrapper


def get_current_user():
    return User.query.get(int(get_jwt_identity()))


# ─────────────────────────────────────────────
# STATS — GET /api/admin/stats
# ─────────────────────────────────────────────
@admin_api_bp.route("/stats", methods=["GET"])
@admin_required
def get_stats():
    total_users     = User.query.count()
    total_fazendas  = Fazenda.query.count()
    total_sensores  = Sensor.query.count()
    total_logs      = Log.query.count()
    total_dados_iot = DadosIoT.query.count()
    admins          = User.query.filter(User.role.in_(["admin", "superadmin"])).count()
    agricultores    = User.query.filter_by(role="agricultor").count()
    sensores_online = Sensor.query.filter_by(status="online").count()
    sensores_off    = Sensor.query.filter_by(status="offline").count()

    return jsonify({
        "utilizadores": {"total": total_users, "admins": admins, "agricultores": agricultores},
        "fazendas":     {"total": total_fazendas},
        "sensores":     {"total": total_sensores, "online": sensores_online, "offline": sensores_off},
        "logs":         {"total": total_logs},
        "dados_iot":    {"total": total_dados_iot},
    }), 200


# ─────────────────────────────────────────────
# UTILIZADORES — CRUD
# ─────────────────────────────────────────────
@admin_api_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([u.to_dict() for u in users]), 200


@admin_api_bp.route("/users", methods=["POST"])
@superadmin_required
def create_user():
    d     = request.get_json(silent=True) or {}
    nome  = (d.get("nome") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    role  = d.get("role", "agricultor")
    fazenda_id = d.get("fazenda_id")

    if not nome or not email or not pw:
        return jsonify({"erro": "Nome, email e senha são obrigatórios"}), 400
    if len(pw) < 6:
        return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres"}), 400
    if role not in ("superadmin", "admin", "agricultor"):
        return jsonify({"erro": "Perfil inválido"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"erro": "Email já registado"}), 409

    if role == "agricultor" and not fazenda_id:
        return jsonify({"erro": "É necessário selecionar a fazenda do agricultor"}), 400
    u = User(nome=nome, email=email, role=role, fazenda_id=fazenda_id if role=="agricultor" else None, is_active=True)
    if role == "agricultor":
        faz = Fazenda.query.get(int(fazenda_id))
        if not faz or not faz.activated_at:
            u.is_active = False
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()

    actor = get_current_user()
    add_log("Utilizador criado", f'Admin criou conta "{nome}" ({role})', actor.nome)
    return jsonify(u.to_dict()), 201


@admin_api_bp.route("/users/<int:uid>", methods=["PUT"])
@superadmin_required
def update_user(uid):
    u = User.query.get(uid)
    if not u:
        return jsonify({"erro": "Utilizador não encontrado"}), 404

    d = request.get_json(silent=True) or {}
    if "nome" in d and d["nome"].strip():
        u.nome = d["nome"].strip()
    if "email" in d and d["email"].strip():
        new_email = d["email"].strip().lower()
        if new_email != u.email and User.query.filter_by(email=new_email).first():
            return jsonify({"erro": "Email já em uso"}), 409
        u.email = new_email
    if "role" in d:
        if d["role"] not in ("superadmin", "admin", "agricultor"):
            return jsonify({"erro": "Perfil inválido"}), 400
        u.role = d["role"]
    # Atualização de fazenda associada (apenas se fornecida)
    if "fazenda_id" in d:
        f_id = d.get("fazenda_id")
        if f_id is not None:
            try:
                f_id = int(f_id)
            except Exception:
                return jsonify({"erro": "fazenda_id inválido"}), 400
            faz = Fazenda.query.get(f_id)
            if not faz:
                return jsonify({"erro": "Fazenda não encontrada"}), 404
            u.fazenda_id = f_id
            # Se é agricultor, sincroniza ativação da conta com ativação da fazenda
            if u.role == "agricultor":
                u.is_active = bool(faz.activated_at)
    if "is_active" in d:
        u.is_active = bool(d["is_active"])
    if "password" in d and d["password"]:
        if len(d["password"]) < 6:
            return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres"}), 400
        u.set_password(d["password"])

    db.session.commit()
    actor = get_current_user()
    add_log("Utilizador atualizado", f'Admin atualizou conta de "{u.nome}"', actor.nome)
    return jsonify(u.to_dict()), 200


@admin_api_bp.route("/users/<int:uid>", methods=["DELETE"])
@superadmin_required
def delete_user(uid):
    actor = get_current_user()
    if actor.id == uid:
        return jsonify({"erro": "Não pode eliminar a sua própria conta aqui"}), 400
    u = User.query.get(uid)
    if not u:
        return jsonify({"erro": "Utilizador não encontrado"}), 404
    nome = u.nome
    db.session.delete(u)
    db.session.commit()
    add_log("Utilizador eliminado", f'Admin eliminou conta de "{nome}"', actor.nome)
    return jsonify({"msg": f'Utilizador "{nome}" eliminado'}), 200


# ─────────────────────────────────────────────
# FAZENDAS — CRUD
# ─────────────────────────────────────────────
@admin_api_bp.route("/fazendas", methods=["GET"])
@admin_required
def list_fazendas():
    fazendas = Fazenda.query.order_by(Fazenda.created_at.desc()).all()
    return jsonify([f.to_dict() for f in fazendas]), 200


@admin_api_bp.route("/fazendas", methods=["POST"])
@admin_required
def create_fazenda():
    d = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    if not nome:
        return jsonify({"erro": "Nome da fazenda é obrigatório"}), 400

    # Suportar 'culturas' (lista) ou 'cultura' (string legada)
    culturas_input = d.get("culturas") or []   # lista: ["cafe", "milho"]
    cultura_str    = (d.get("cultura") or "").strip()

    f = Fazenda(
        nome=nome,
        proprietario=d.get("proprietario", "").strip(),
        localizacao=d.get("localizacao", "").strip(),
        hectares=d.get("hectares"),
        status=d.get("status", "active"),
    )

    # Processar culturas
    if culturas_input and isinstance(culturas_input, list):
        f.set_culturas_list(culturas_input)
    elif cultura_str:
        f.set_culturas_list([cultura_str])
    else:
        f.cultura  = ""
        f.culturas = "[]"

    db.session.add(f)
    db.session.commit()

    try:
        admin_id = int(get_jwt_identity())
        culturas_lista = f.get_culturas_list()

        if culturas_lista:
            # Criar uma zona por cultura registada
            for i, cult in enumerate(culturas_lista):
                area_por_zona = (float(d.get("hectares") or 0) / len(culturas_lista)) if culturas_lista else 0.0
                nome_zona = "Zona Principal" if i == 0 else f"Zona {cult.capitalize()}"
                z = Zona(
                    user_id=admin_id,
                    fazenda_id=f.id,
                    nome=nome_zona,
                    cultura=cult,
                    tipo=cult,
                    area_ha=round(area_por_zona, 2),
                    estagio="Crescimento",
                    saude="Bom",
                    acoes=None
                )
                db.session.add(z)
        else:
            # Zona genérica se não houver cultura definida
            z = Zona(
                user_id=admin_id,
                fazenda_id=f.id,
                nome="Zona Principal",
                cultura="—",
                tipo=None,
                area_ha=float(d.get("hectares") or 0) or 0.0,
                estagio="Crescimento",
                saude="Bom",
                acoes=None
            )
            db.session.add(z)

        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[Fazenda] Aviso ao criar zonas: {e}")

    actor = get_current_user()
    add_log("Fazenda criada", f'Fazenda "{nome}" adicionada com culturas: {f.get_culturas_list()}', actor.nome)
    return jsonify(f.to_dict()), 201


@admin_api_bp.route("/fazendas/<int:fid>", methods=["PUT"])
@admin_required
def update_fazenda(fid):
    f = Fazenda.query.get(fid)
    if not f:
        return jsonify({"erro": "Fazenda não encontrada"}), 404

    d = request.get_json(silent=True) or {}
    if "nome"         in d and d["nome"].strip(): f.nome         = d["nome"].strip()
    if "proprietario" in d: f.proprietario = d["proprietario"]
    if "localizacao"  in d: f.localizacao  = d["localizacao"]
    if "hectares"     in d: f.hectares     = d["hectares"]
    if "status"       in d: f.status       = d["status"]

    # Actualizar culturas (lista tem precedencia sobre string)
    if "culturas" in d and isinstance(d["culturas"], list):
        f.set_culturas_list(d["culturas"])
    elif "cultura" in d and d["cultura"]:
        f.set_culturas_list([d["cultura"]])

    db.session.commit()
    actor = get_current_user()
    add_log("Fazenda atualizada", f'Fazenda "{f.nome}" atualizada', actor.nome)
    return jsonify(f.to_dict()), 200


@admin_api_bp.route("/fazendas/<int:fid>", methods=["DELETE"])
@admin_required
def delete_fazenda(fid):
    f = Fazenda.query.get(fid)
    if not f:
        return jsonify({"erro": "Fazenda não encontrada"}), 404
    nome = f.nome
    db.session.delete(f)
    db.session.commit()
    actor = get_current_user()
    add_log("Fazenda eliminada", f'Fazenda "{nome}" eliminada', actor.nome)
    return jsonify({"msg": f'Fazenda "{nome}" eliminada'}), 200

# ─────────────────────────────────────────────
# ATIVAÇÃO DE FAZENDA — POST /api/admin/fazendas/<id>/ativar
# ─────────────────────────────────────────────
@admin_api_bp.route("/fazendas/<int:fid>/ativar", methods=["POST"])
@admin_required
def ativar_fazenda(fid):
    f = Fazenda.query.get(fid)
    if not f:
        return jsonify({"erro": "Fazenda não encontrada"}), 404
    d = request.get_json(silent=True) or {}
    code = (d.get("unit_code") or "").strip()
    if not code:
        return jsonify({"erro": "Código da unidade é obrigatório"}), 400
    if code != (f.activation_code or "0123"):
        return jsonify({"erro": "Código da unidade inválido"}), 400
    f.activated_at = datetime.utcnow()
    db.session.commit()
    # Ativar contas dos agricultores desta fazenda
    try:
        User.query.filter_by(fazenda_id=f.id, role="agricultor").update({"is_active": True})
        db.session.commit()
    except Exception as e:
        print(f"[Ativar Fazenda] Aviso ao ativar utilizadores: {e}")
    actor = get_current_user()
    add_log("Fazenda ativada", f'Fazenda "{f.nome}" ativada com código correcto', actor.nome)
    return jsonify({"msg": "Fazenda ativada", "activated_at": f.activated_at.isoformat() + 'Z'}), 200


# ─────────────────────────────────────────────
# SENSORES — CRUD
# ─────────────────────────────────────────────
@admin_api_bp.route("/sensores", methods=["GET"])
@admin_required
def list_sensores():
    sensores = Sensor.query.order_by(Sensor.created_at.desc()).all()
    return jsonify([s.to_dict() for s in sensores]), 200


@admin_api_bp.route("/sensores", methods=["POST"])
@admin_required
def create_sensor():
    d    = request.get_json(silent=True) or {}
    nome = (d.get("nome") or "").strip()
    tipo = (d.get("tipo") or "").strip()
    if not nome or not tipo:
        return jsonify({"erro": "Nome e tipo do sensor são obrigatórios"}), 400
    if tipo not in ("Clima", "Solo", "GPS", "Câmara"):
        return jsonify({"erro": "Tipo inválido. Use: Clima, Solo, GPS ou Câmara"}), 400

    s = Sensor(
        nome=nome,
        tipo=tipo,
        fazenda_id=d.get("fazenda_id"),
        status=d.get("status", "online"),
        bateria=d.get("bateria", 100),
    )
    db.session.add(s)
    db.session.commit()

    actor = get_current_user()
    add_log("Sensor criado", f'Sensor "{nome}" ({tipo}) adicionado', actor.nome)
    return jsonify(s.to_dict()), 201


@admin_api_bp.route("/sensores/<int:sid>", methods=["PUT"])
@admin_required
def update_sensor(sid):
    s = Sensor.query.get(sid)
    if not s:
        return jsonify({"erro": "Sensor não encontrado"}), 404

    d = request.get_json(silent=True) or {}
    if "nome"      in d and d["nome"].strip(): s.nome      = d["nome"].strip()
    if "tipo"      in d:
        if d["tipo"] not in ("Clima", "Solo", "GPS", "Câmara"):
            return jsonify({"erro": "Tipo inválido"}), 400
        s.tipo = d["tipo"]
    if "fazenda_id" in d: s.fazenda_id = d["fazenda_id"]
    if "status"     in d: s.status     = d["status"]
    if "bateria"    in d: s.bateria    = d["bateria"]

    db.session.commit()
    actor = get_current_user()
    add_log("Sensor atualizado", f'Sensor "{s.nome}" atualizado', actor.nome)
    return jsonify(s.to_dict()), 200


@admin_api_bp.route("/sensores/<int:sid>", methods=["DELETE"])
@admin_required
def delete_sensor(sid):
    s = Sensor.query.get(sid)
    if not s:
        return jsonify({"erro": "Sensor não encontrado"}), 404
    nome = s.nome
    db.session.delete(s)
    db.session.commit()
    actor = get_current_user()
    add_log("Sensor eliminado", f'Sensor "{nome}" eliminado', actor.nome)
    return jsonify({"msg": f'Sensor "{nome}" eliminado'}), 200


# ─────────────────────────────────────────────
# DEVICE IDs SEM SENSOR — GET /api/admin/sensores/device_ids_desconhecidos
# Mostra device_ids que chegaram na IoT mas não têm Sensor registado
# ─────────────────────────────────────────────
@admin_api_bp.route("/sensores/device_ids_desconhecidos", methods=["GET"])
@admin_required
def device_ids_desconhecidos():
    """Lista device_ids que enviaram dados mas não têm Sensor registado na BD."""
    # Todos os device_ids distintos nos dados IoT
    from sqlalchemy import func as sqlfunc
    rows = db.session.query(
        DadosIoT.device_id,
        sqlfunc.count(DadosIoT.id).label("total"),
        sqlfunc.max(DadosIoT.timestamp).label("ultimo")
    ).group_by(DadosIoT.device_id).all()

    # Todos os nomes de sensores registados (lowercase)
    nomes_registados = {s.nome.strip().lower() for s in Sensor.query.all()}

    resultado = []
    for row in rows:
        did = (row.device_id or "").strip()
        did_lower = did.lower()
        # Variantes de comparação
        variantes = {did_lower, did_lower.replace("-","_"), did_lower.replace("_","-"), did_lower.replace("-","").replace("_","")}
        registado = bool(nomes_registados & variantes)
        resultado.append({
            "device_id":  did,
            "total_envios": row.total,
            "ultimo_envio": row.ultimo.isoformat() + 'Z' if row.ultimo else None,
            "registado":   registado,
            "aviso": None if registado else f'device_id "{did}" não tem Sensor registado. Crie um Sensor com nome="{did}" e associe à fazenda correcta.'
        })

    nao_registados = [r for r in resultado if not r["registado"]]
    return jsonify({
        "total":             len(resultado),
        "nao_registados":    len(nao_registados),
        "device_ids":        resultado,
        "instrucao": "Para ligar um dispositivo IoT a uma fazenda, o Sensor.nome deve ser igual ao device_id enviado pelo hardware."
    }), 200


# ─────────────────────────────────────────────
# LOGS — GET /api/admin/logs
# ─────────────────────────────────────────────
@admin_api_bp.route("/logs", methods=["GET"])
@admin_required
def list_logs():
    limit  = min(int(request.args.get("limit", 200)), 1000)
    offset = int(request.args.get("offset", 0))
    logs   = Log.query.order_by(Log.created_at.desc()).offset(offset).limit(limit).all()
    return jsonify([l.to_dict() for l in logs]), 200


# ─────────────────────────────────────────────
# DETALHES DA FAZENDA — sensores + IoT + culturas
# GET /api/admin/fazendas/<id>/detalhes
# ─────────────────────────────────────────────
@admin_api_bp.route("/fazendas/<int:fid>/detalhes", methods=["GET"])
@admin_required
def get_fazenda_detalhes(fid):
    f = Fazenda.query.get(fid)
    if not f:
        return jsonify({"erro": "Fazenda não encontrada"}), 404

    sensores = Sensor.query.filter_by(fazenda_id=fid).all()
    device_ids = [s.nome for s in sensores]

    # Últimos dados IoT da fazenda (desde ativação, se houver)
    base_q = DadosIoT.query
    if device_ids:
        base_q = base_q.filter(DadosIoT.device_id.in_(device_ids))
    else:
        base_q = base_q.filter(False)
    if f.activated_at:
        base_q = base_q.filter(DadosIoT.timestamp >= f.activated_at)
    latest = base_q.order_by(DadosIoT.timestamp.desc()).first()
    iot = None
    if latest:
        iot = {
            "temperatura_ar": latest.temperatura_ar,
            "humidade_ar": latest.humidade_ar,
            "pressao_ar": latest.pressao_ar,
            "humidade_solo": latest.humidade_solo,
            "detecao_praga": latest.detecao_praga,
            "tipo_praga": latest.tipo_praga,
            "confianca": latest.confianca,
            "timestamp": latest.timestamp.isoformat() + 'Z' if latest.timestamp else None,
        }

    # Calcular saúde do solo com base nos dados IoT
    soil_health = "sem_dados"
    if iot and iot.get("humidade_solo") is not None:
        h = iot["humidade_solo"]
        if h >= 60:
            soil_health = "bom"
        elif h >= 30:
            soil_health = "atencao"
        else:
            soil_health = "critico"

    # Utilizadores associados à fazenda
    users = User.query.filter_by(fazenda_id=f.id).order_by(User.created_at.desc()).all()

    # Pequeno relatório da fazenda (últimos 30 dias)
    from datetime import timedelta
    cutoff = (datetime.utcnow() - timedelta(days=30))
    rq = DadosIoT.query
    if device_ids:
        rq = rq.filter(DadosIoT.device_id.in_(device_ids))
    else:
        rq = rq.filter(False)
    if f.activated_at:
        rq = rq.filter(DadosIoT.timestamp >= f.activated_at)
    rq = rq.filter(DadosIoT.timestamp >= cutoff)
    rows = rq.order_by(DadosIoT.timestamp.asc()).all()
    daily = {}
    for row in rows:
        day = row.timestamp.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"temp": [], "hum_solo": [], "hum_ar": [], "pressao": [], "pragas": 0}
        if row.temperatura_ar is not None: daily[day]["temp"].append(row.temperatura_ar)
        if row.humidade_solo  is not None: daily[day]["hum_solo"].append(row.humidade_solo)
        if row.humidade_ar    is not None: daily[day]["hum_ar"].append(row.humidade_ar)
        if row.pressao_ar     is not None: daily[day]["pressao"].append(row.pressao_ar)
        if row.detecao_praga: daily[day]["pragas"] += 1
    def avg(lst): return round(sum(lst)/len(lst), 1) if lst else None
    chart_diario = [
        {"data": day,
         "temp": avg(v["temp"]),
         "hum_solo": avg(v["hum_solo"]),
         "hum_ar": avg(v["hum_ar"]),
         "pressao": avg(v["pressao"]),
         "pragas": v["pragas"]}
        for day, v in sorted(daily.items())
    ]
    resumo = {
        "total_leituras": len(rows),
        "temp_media": avg([r.temperatura_ar for r in rows if r.temperatura_ar is not None]),
        "hum_solo_media": avg([r.humidade_solo for r in rows if r.humidade_solo is not None]),
        "hum_ar_media": avg([r.humidade_ar for r in rows if r.humidade_ar is not None]),
        "pressao_media": avg([r.pressao_ar for r in rows if r.pressao_ar is not None]),
        "pragas_detectadas": sum(1 for r in rows if r.detecao_praga),
    }

    return jsonify({
        "fazenda": f.to_dict(),
        "sensores": [s.to_dict() for s in sensores],
        "iot_ultimo": iot,
        "saude_solo": soil_health,
        "usuarios": [u.to_dict() for u in users],
        "relatorio": {
            "resumo": resumo,
            "grafico_diario": chart_diario
        },
        "cultura_info": {
            "nome": f.cultura or "—",
            "ph_ideal": 6.5,
            "humidade_ideal": 65,
            "temp_ideal": 22
        }
    }), 200


# ─────────────────────────────────────────────
# MENSAGENS — Agricultor envia
# POST /api/mensagens  (agricultor autenticado)
# ─────────────────────────────────────────────
@admin_api_bp.route("/mensagens", methods=["POST"])
@jwt_required()
def criar_mensagem():
    user_id = int(get_jwt_identity())
    d = request.get_json(silent=True) or {}
    assunto   = (d.get("assunto") or "").strip()
    conteudo  = (d.get("conteudo") or "").strip()
    prioridade = d.get("prioridade", "normal")

    if not assunto or not conteudo:
        return jsonify({"erro": "Assunto e conteúdo são obrigatórios"}), 400
    if prioridade not in ("critico", "alto", "normal", "baixo"):
        prioridade = "normal"

    msg = Mensagem(user_id=user_id, assunto=assunto, conteudo=conteudo, prioridade=prioridade)
    db.session.add(msg)
    db.session.commit()

    # Email: se crítico, notificar admin
    if prioridade == "critico":
        sender = User.query.get(user_id)
        admin = User.query.filter_by(role="superadmin").first()
        if admin and sender:
            import threading
            threading.Thread(
                target=send_critical_alert_to_admin,
                args=(admin.email, sender.nome, sender.email, assunto, conteudo),
                daemon=True
            ).start()

    return jsonify(msg.to_dict()), 201


# ─────────────────────────────────────────────
# MENSAGENS — Agricultor vê as suas mensagens
# GET /api/mensagens/minhas
# ─────────────────────────────────────────────
@admin_api_bp.route("/mensagens/minhas", methods=["GET"])
@jwt_required()
def minhas_mensagens():
    user_id = int(get_jwt_identity())
    msgs = Mensagem.query.filter_by(user_id=user_id).order_by(Mensagem.created_at.desc()).all()
    return jsonify([m.to_dict() for m in msgs]), 200


# ─────────────────────────────────────────────
# MENSAGENS — Admin vê TODAS (dashboard + contacto), com filtros
# GET /api/admin/mensagens?origem=&status=&prioridade=
# ─────────────────────────────────────────────
@admin_api_bp.route("/mensagens", methods=["GET"])
@admin_required
def admin_list_mensagens():
    origem    = request.args.get("origem", "")      # 'dashboard' | 'contacto' | ''
    status    = request.args.get("status", "")      # 'aberto' | 'respondido' | ''
    prioridade = request.args.get("prioridade", "") # 'critico' | 'alto' | 'normal' | 'baixo' | ''

    q = Mensagem.query
    if origem:
        q = q.filter(Mensagem.origem == origem)
    if status:
        q = q.filter(Mensagem.status == status)
    if prioridade:
        q = q.filter(Mensagem.prioridade == prioridade)

    msgs = q.order_by(Mensagem.created_at.desc()).all()

    total       = len(msgs)
    respondidas = sum(1 for m in msgs if m.status == "respondido")
    pendentes   = sum(1 for m in msgs if m.status == "aberto")
    contacto_n  = sum(1 for m in msgs if (m.origem or "dashboard") == "contacto")

    return jsonify({
        "mensagens": [m.to_dict() for m in msgs],
        "stats": {
            "total": total,
            "respondidas": respondidas,
            "pendentes": pendentes,
            "contacto": contacto_n,
            "dashboard": total - contacto_n
        }
    }), 200


# ─────────────────────────────────────────────
# ALERTAS DE AGRICULTORES — mensagens críticas
# GET /api/admin/alertas/agricultores
# ─────────────────────────────────────────────
@admin_api_bp.route("/alertas/agricultores", methods=["GET"])
@admin_required
def alertas_agricultores():
    msgs = Mensagem.query.filter_by(prioridade="critico").order_by(Mensagem.created_at.desc()).all()
    return jsonify([m.to_dict() for m in msgs]), 200


# ─────────────────────────────────────────────
# RESPONDER MENSAGEM — Admin responde
# PUT /api/admin/mensagens/<id>/responder
# ─────────────────────────────────────────────
@admin_api_bp.route("/mensagens/<int:mid>/responder", methods=["PUT"])
@admin_required
def responder_mensagem(mid):
    m = Mensagem.query.get(mid)
    if not m:
        return jsonify({"erro": "Mensagem não encontrada"}), 404
    d = request.get_json(silent=True) or {}
    resposta = (d.get("resposta") or "").strip()
    if not resposta:
        return jsonify({"erro": "Resposta é obrigatória"}), 400
    actor = get_current_user()
    m.resposta = resposta
    m.respondido_por = actor.nome
    m.respondido_em = datetime.utcnow()
    m.status = "respondido"
    m.lida_admin = True
    db.session.commit()
    add_log("Mensagem respondida", f'Admin respondeu mensagem #{mid}', actor.nome)

    # Email: notificar agricultor da resposta
    if m.user:
        import threading
        threading.Thread(
            target=send_message_reply,
            args=(m.user.email, m.user.nome, m.assunto, resposta, actor.nome),
            daemon=True
        ).start()

    return jsonify(m.to_dict()), 200


# ─────────────────────────────────────────────
# MARCAR MENSAGEM COMO LIDA
# PUT /api/admin/mensagens/<id>/ler
# ─────────────────────────────────────────────
@admin_api_bp.route("/mensagens/<int:mid>/ler", methods=["PUT"])
@admin_required
def marcar_mensagem_lida(mid):
    m = Mensagem.query.get(mid)
    if not m:
        return jsonify({"erro": "Mensagem não encontrada"}), 404
    m.lida_admin = True
    db.session.commit()
    return jsonify(m.to_dict()), 200


# ─────────────────────────────────────────────
# RELATÓRIOS BI — dados agregados
# GET /api/admin/relatorios/dados
# ─────────────────────────────────────────────
@admin_api_bp.route("/relatorios/dados", methods=["GET"])
@admin_required
def relatorios_dados():
    periodo    = int(request.args.get("periodo", 30))
    fazenda_id = request.args.get("fazenda_id")
    cutoff     = datetime.utcnow() - timedelta(days=periodo)

    # Build base queryset, optionally filtered by farm via sensor device_ids
    device_ids = None
    fazenda_nome = None
    if fazenda_id:
        faz = Fazenda.query.get(int(fazenda_id))
        if faz:
            fazenda_nome = faz.nome
            sensors = Sensor.query.filter_by(fazenda_id=int(fazenda_id)).all()
            device_ids = [s.nome for s in sensors]

    def iot_q():
        q = DadosIoT.query.filter(DadosIoT.timestamp >= cutoff)
        if device_ids:  # só filtra se houver device_ids; sem sensores → mostra todos
            q = q.filter(db.func.lower(DadosIoT.device_id).in_([d.lower() for d in device_ids]))
        return q

    rows_all          = iot_q().all()
    total_leituras    = len(rows_all)
    def _avg(lst): return round(sum(lst)/len(lst), 1) if lst else None
    avg_temp     = _avg([r.temperatura_ar for r in rows_all if r.temperatura_ar is not None])
    avg_hum_ar   = _avg([r.humidade_ar    for r in rows_all if r.humidade_ar    is not None])
    avg_hum_solo = _avg([r.humidade_solo  for r in rows_all if r.humidade_solo  is not None])
    avg_pressao  = _avg([r.pressao_ar     for r in rows_all if r.pressao_ar     is not None])
    pragas_detectadas = sum(1 for r in rows_all if r.detecao_praga)

    # Dados diários para gráficos
    rows = sorted(rows_all, key=lambda r: r.timestamp)
    daily = {}
    for row in rows:
        day = row.timestamp.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"temp": [], "hum_solo": [], "hum_ar": [], "pressao": []}
        if row.temperatura_ar is not None: daily[day]["temp"].append(row.temperatura_ar)
        if row.humidade_solo  is not None: daily[day]["hum_solo"].append(row.humidade_solo)
        if row.humidade_ar    is not None: daily[day]["hum_ar"].append(row.humidade_ar)
        if row.pressao_ar     is not None: daily[day]["pressao"].append(row.pressao_ar)

    def avg(lst): return round(sum(lst)/len(lst), 1) if lst else None

    chart_diario = [
        {"data": day,
         "temp": avg(v["temp"]),
         "hum_solo": avg(v["hum_solo"]),
         "hum_ar": avg(v["hum_ar"]),
         "pressao": avg(v["pressao"])}
        for day, v in sorted(daily.items())
    ]

    msgs_criticas = Mensagem.query.filter_by(prioridade="critico", lida_admin=False).count()
    msgs_nao_lidas = Mensagem.query.filter_by(lida_admin=False).count()

    return jsonify({
        "periodo_dias": periodo,
        "fazenda_filtro": fazenda_nome,
        "resumo": {
            "total_leituras": total_leituras,
            "temp_media": round(avg_temp, 1) if avg_temp else None,
            "hum_ar_media": round(avg_hum_ar, 1) if avg_hum_ar else None,
            "hum_solo_media": round(avg_hum_solo, 1) if avg_hum_solo else None,
            "pressao_media": round(avg_pressao, 1) if avg_pressao else None,
            "pragas_detectadas": pragas_detectadas,
            "total_fazendas": Fazenda.query.count(),
            "total_sensores": Sensor.query.count(),
            "sensores_online": Sensor.query.filter_by(status="online").count(),
            "total_usuarios": User.query.count(),
            "mensagens_criticas": msgs_criticas,
            "mensagens_nao_lidas": msgs_nao_lidas,
        },
        "grafico_diario": chart_diario,
        "sensores_por_tipo": {
            tipo: Sensor.query.filter_by(tipo=tipo).count()
            for tipo in ["Clima", "Solo", "GPS", "Câmara"]
        },
        "fazendas_status": {
            "active": Fazenda.query.filter_by(status="active").count(),
            "inactive": Fazenda.query.filter_by(status="inactive").count(),
        }
    }), 200


# ─────────────────────────────────────────────
# RELATÓRIOS DO AGRICULTOR
# GET /api/relatorios/agricultor
# ─────────────────────────────────────────────
@admin_api_bp.route("/relatorios/agricultor", methods=["GET"])
@jwt_required()
def relatorios_agricultor():
    periodo = request.args.get("periodo", "mensal")
    # Map period to days
    dias_map = {"semanal": 7, "mensal": 30, "anual": 365}
    dias = dias_map.get(periodo, 30)
    cutoff = datetime.utcnow() - timedelta(days=dias)

    # Filtra por fazenda do utilizador autenticado e por activation time
    user = User.query.get(int(get_jwt_identity()))
    device_ids = []
    farm_activated_at = None
    if user and getattr(user, 'fazenda_id', None):
        faz = Fazenda.query.get(int(user.fazenda_id))
        if faz:
            farm_activated_at = faz.activated_at
            device_ids = [s.nome for s in Sensor.query.filter_by(fazenda_id=faz.id).all()]

    q = DadosIoT.query.filter(DadosIoT.timestamp >= cutoff)
    if device_ids:
        q = q.filter(DadosIoT.device_id.in_(device_ids))
    # Se não houver sensores associados, retorna todos os dados (sem filtro por device_id)
    # para que o utilizador veja dados mesmo antes de registar sensores
    if farm_activated_at:
        q = q.filter(DadosIoT.timestamp >= farm_activated_at)
    rows = q.order_by(DadosIoT.timestamp.asc()).all()

    daily = {}
    for row in rows:
        day = row.timestamp.strftime("%Y-%m-%d")
        if day not in daily:
            daily[day] = {"temp": [], "hum_solo": [], "hum_ar": [], "pressao": [], "pragas": 0}
        if row.temperatura_ar is not None: daily[day]["temp"].append(row.temperatura_ar)
        if row.humidade_solo  is not None: daily[day]["hum_solo"].append(row.humidade_solo)
        if row.humidade_ar    is not None: daily[day]["hum_ar"].append(row.humidade_ar)
        if row.pressao_ar     is not None: daily[day]["pressao"].append(row.pressao_ar)
        if row.detecao_praga: daily[day]["pragas"] += 1

    def avg(lst): return round(sum(lst)/len(lst), 1) if lst else None

    chart_diario = [
        {"data": day,
         "temp": avg(v["temp"]),
         "hum_solo": avg(v["hum_solo"]),
         "hum_ar": avg(v["hum_ar"]),
         "pressao": avg(v["pressao"]),
         "pragas": v["pragas"]}
        for day, v in sorted(daily.items())
    ]

    all_temps  = [r.temperatura_ar for r in rows if r.temperatura_ar is not None]
    all_humid  = [r.humidade_solo  for r in rows if r.humidade_solo  is not None]
    all_hum_ar = [r.humidade_ar    for r in rows if r.humidade_ar    is not None]

    return jsonify({
        "periodo": periodo,
        "dias": dias,
        "resumo": {
            "total_leituras": len(rows),
            "temp_media": avg(all_temps),
            "hum_solo_media": avg(all_humid),
            "hum_ar_media": avg(all_hum_ar),
            "pragas_detectadas": sum(1 for r in rows if r.detecao_praga),
            "temp_max": round(max(all_temps), 1) if all_temps else None,
            "temp_min": round(min(all_temps), 1) if all_temps else None,
            "hum_solo_max": round(max(all_humid), 1) if all_humid else None,
            "hum_solo_min": round(min(all_humid), 1) if all_humid else None,
        },
        "grafico_diario": chart_diario,
    }), 200


# ─────────────────────────────────────────────
# CONFIGURAÇÕES DA PLATAFORMA
# GET/POST /api/admin/configuracoes
# ─────────────────────────────────────────────
import json as _json

_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), 'instance', 'settings.json')

def _load_settings():
    try:
        with open(_SETTINGS_FILE, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except Exception:
        return {}

def _save_settings(data):
    os.makedirs(os.path.dirname(_SETTINGS_FILE), exist_ok=True)
    with open(_SETTINGS_FILE, 'w', encoding='utf-8') as f:
        _json.dump(data, f, ensure_ascii=False, indent=2)

@admin_api_bp.route("/configuracoes", methods=["GET"])
@admin_required
def get_configuracoes():
    return jsonify(_load_settings()), 200

@admin_api_bp.route("/configuracoes", methods=["POST"])
@admin_required
def save_configuracoes():
    data = request.get_json(silent=True) or {}
    existing = _load_settings()
    existing.update(data)
    _save_settings(existing)
    actor = get_current_user()
    add_log("Configurações actualizadas", "Admin guardou configurações da plataforma", actor.nome)
    return jsonify({"msg": "Configurações guardadas", "settings": existing}), 200
