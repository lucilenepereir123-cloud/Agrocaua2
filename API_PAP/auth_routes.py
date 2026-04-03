
from flask import Blueprint, request, jsonify
from models import db, User, Log
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, get_jwt
import threading
try:
    from email_service import send_welcome_email, send_contact_form_confirmation, send_contact_form_to_admin
    _email_ok = True
except Exception:
    _email_ok = False

auth_bp  = Blueprint("auth", __name__, url_prefix="/api")
blacklist = set()

def add_log(acao, detalhe, utilizador="Sistema"):
    try:
        db.session.add(Log(acao=acao, detalhe=detalhe, utilizador=utilizador))
        db.session.commit()
    except Exception:
        db.session.rollback()

# POST /api/register
@auth_bp.route("/register", methods=["POST"])
def register():
    d = request.get_json(silent=True) or {}
    nome  = (d.get("nome") or "").strip()
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    fazenda_id = d.get("fazenda_id")
    if not nome or not email or not pw or not fazenda_id:
        return jsonify({"erro": "Nome, email, senha e fazenda são obrigatórios"}), 400
    if len(pw) < 6:
        return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"erro": "Email já registado"}), 409
    from models import Fazenda
    faz = Fazenda.query.get(int(fazenda_id))
    u = User(nome=nome, email=email, role="agricultor", fazenda_id=int(fazenda_id), is_active=bool(faz and faz.activated_at))
    u.set_password(pw)
    db.session.add(u)
    db.session.commit()
    add_log("Nova conta registada", f'"{nome}" registou-se', nome)
    if _email_ok:
        threading.Thread(target=send_welcome_email, args=(email, nome), daemon=True).start()
    return jsonify({"msg": "Conta criada com sucesso"}), 201

# POST /api/login
@auth_bp.route("/login", methods=["POST"])
def login():
    d = request.get_json(silent=True) or {}
    email = (d.get("email") or "").strip().lower()
    pw    = d.get("password") or ""
    if not email or not pw:
        return jsonify({"erro": "Email e senha são obrigatórios"}), 400
    u = User.query.filter_by(email=email).first()
    if not u or not u.check_password(pw):
        add_log("Tentativa de acesso falhada", f"Password incorreta para {email}")
        return jsonify({"erro": "Credenciais inválidas"}), 401
    if not u.is_active:
        return jsonify({"erro": "Conta desactivada. Contacte o administrador."}), 403
    token = create_access_token(identity=str(u.id))
    add_log("Acesso ao sistema", f"Login bem sucedido via browser", u.nome)
    return jsonify({"token": token, "user": {"id": u.id, "nome": u.nome, "email": u.email, "role": u.role}}), 200

# POST /api/logout
@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    blacklist.add(get_jwt()["jti"])
    return jsonify({"msg": "Logout feito com sucesso"}), 200

# GET /api/profile
@auth_bp.route("/profile", methods=["GET"])
@jwt_required()
def get_profile():
    u = User.query.get(int(get_jwt_identity()))
    if not u: return jsonify({"erro": "Utilizador não encontrado"}), 404
    return jsonify(u.to_dict()), 200

# PUT /api/profile
@auth_bp.route("/profile", methods=["PUT"])
@jwt_required()
def update_profile():
    u = User.query.get(int(get_jwt_identity()))
    if not u: return jsonify({"erro": "Utilizador não encontrado"}), 404
    d = request.get_json(silent=True) or {}
    if "nome"     in d and d["nome"].strip(): u.nome = d["nome"].strip()
    if "password" in d and d["password"]:
        if len(d["password"]) < 6:
            return jsonify({"erro": "A senha deve ter pelo menos 6 caracteres"}), 400
        u.set_password(d["password"])
    # Permitir que o agricultor actualize as culturas da sua fazenda via perfil
    if u.fazenda_id and ("culturas" in d or "cultura" in d):
        from models import Fazenda
        faz = Fazenda.query.get(u.fazenda_id)
        if faz:
            if "culturas" in d and isinstance(d["culturas"], list):
                faz.set_culturas_list(d["culturas"])
            elif "cultura" in d and d["cultura"]:
                faz.set_culturas_list([d["cultura"]])
    db.session.commit()
    add_log("Perfil actualizado", f'"{u.nome}" actualizou o seu perfil', u.nome)
    return jsonify(u.to_dict()), 200

# DELETE /api/delete-account
@auth_bp.route("/delete-account", methods=["DELETE"])
@jwt_required()
def delete_account():
    u = User.query.get(int(get_jwt_identity()))
    if not u: return jsonify({"erro": "Utilizador não encontrado"}), 404
    nome = u.nome
    db.session.delete(u)
    db.session.commit()
    add_log("Conta eliminada", f'"{nome}" eliminou a sua conta', nome)
    return jsonify({"msg": "Conta deletada com sucesso"}), 200


# POST /api/contacto  — formulário de contacto da landing page
@auth_bp.route("/contacto", methods=["POST"])
def contacto():
    from models import Mensagem
    d        = request.get_json(silent=True) or {}
    nome     = (d.get("nome") or "").strip()
    email    = (d.get("email") or "").strip().lower()
    telefone = (d.get("telefone") or "").strip()
    assunto  = (d.get("assunto") or "").strip()
    mensagem = (d.get("mensagem") or "").strip()
    honeypot = (d.get("website") or "").strip()

    # Honeypot (spam) + validações básicas
    if honeypot:
        return jsonify({"erro": "Rejeitado"}), 400
    if not nome or not email or not assunto or not mensagem:
        return jsonify({"erro": "Nome, email, assunto e mensagem são obrigatórios"}), 400
    if "@" not in email or "." not in email.split("@")[-1]:
        return jsonify({"erro": "Email inválido"}), 400
    if len(assunto) < 3 or len(mensagem) < 5:
        return jsonify({"erro": "Assunto/mensagem muito curtos"}), 400

    # Rate limit simples por IP (memória)
    from flask import request as _rq
    ip = _rq.headers.get("X-Forwarded-For", _rq.remote_addr or "")
    try:
        from time import time as _now
        if not hasattr(contacto, "_rl"):
            contacto._rl = {}
        rec = contacto._rl.get(ip, {"t": _now(), "n": 0})
        # janela de 3600s, máx 5 mensagens
        if _now() - rec["t"] > 3600:
            rec = {"t": _now(), "n": 0}
        rec["n"] += 1
        contacto._rl[ip] = rec
        if rec["n"] > 5:
            return jsonify({"erro": "Limite de submissões atingido. Tente mais tarde."}), 429
    except Exception:
        pass

    # Guardar na base de dados
    try:
        msg = Mensagem(
            user_id=None,
            nome_contacto=nome,
            email_contacto=email,
            telefone=telefone,
            origem="contacto",
            assunto=assunto,
            conteudo=mensagem,
            prioridade="normal"
        )
        db.session.add(msg)
        db.session.commit()
    except Exception:
        db.session.rollback()

    add_log("Contacto recebido", f'"{nome}" enviou formulário de contacto: {assunto}', nome)

    if _email_ok:
        import os
        admin_email = os.environ.get("SMTP_USER", "")
        threading.Thread(target=send_contact_form_confirmation, args=(email, nome, assunto), daemon=True).start()
        if admin_email:
            threading.Thread(target=send_contact_form_to_admin, args=(admin_email, nome, email, telefone, assunto, mensagem), daemon=True).start()

    return jsonify({"msg": "Mensagem enviada com sucesso! Entraremos em contacto brevemente."}), 200
