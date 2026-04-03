from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import json

db = SQLAlchemy()

# =====================================================
# USER
# =====================================================
class User(db.Model):
    __tablename__ = "users"
    id            = db.Column(db.Integer, primary_key=True)
    nome          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(120), unique=True, nullable=False, index=True)
    role          = db.Column(db.String(30), default="agricultor")   # superadmin | admin | agricultor
    password_hash = db.Column(db.String(255), nullable=False)
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    is_active     = db.Column(db.Boolean, default=True)
    fazenda_id    = db.Column(db.Integer, db.ForeignKey("fazendas.id"), nullable=True)

    def set_password(self, pw):   self.password_hash = generate_password_hash(pw)
    def check_password(self, pw): return check_password_hash(self.password_hash, pw)
    def to_dict(self):
        base = {"id": self.id, "nome": self.nome, "email": self.email,
                "role": self.role, "is_active": self.is_active,
                "fazenda_id": self.fazenda_id,
                "created_at": self.created_at.isoformat() + 'Z'}
        # Incluir informações da fazenda no perfil do agricultor
        if self.fazenda_id:
            faz = Fazenda.query.get(self.fazenda_id)
            if faz:
                base["fazenda"] = faz.to_dict()
        return base
    def __repr__(self): return f"<User {self.email}>"

# =====================================================
# FAZENDA
# =====================================================
class Fazenda(db.Model):
    __tablename__ = "fazendas"
    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(120), nullable=False)
    proprietario= db.Column(db.String(120))
    localizacao = db.Column(db.String(120))
    hectares    = db.Column(db.Float)
    cultura     = db.Column(db.String(255))          # Cultura principal (legado, compatibilidade)
    culturas    = db.Column(db.Text, default="[]")   # Lista JSON de culturas: ["cafe","milho",...]
    status      = db.Column(db.String(20), default="active")
    activation_code = db.Column(db.String(10), default="0123")
    activated_at  = db.Column(db.DateTime, nullable=True)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def get_culturas_list(self):
        """Devolve a lista de culturas como Python list."""
        try:
            lst = json.loads(self.culturas or "[]")
            return lst if isinstance(lst, list) else []
        except (json.JSONDecodeError, TypeError):
            # Fallback: se culturas é vazio mas cultura (legado) existe
            return [self.cultura] if self.cultura else []

    def set_culturas_list(self, lst):
        """Guarda a lista de culturas como JSON string."""
        if isinstance(lst, list):
            self.culturas = json.dumps([c.strip().lower() for c in lst if c.strip()])
            # Manter campo legado com a cultura principal
            self.cultura = lst[0].strip() if lst else self.cultura
        elif isinstance(lst, str) and lst.strip():
            culturas_split = [c.strip().lower() for c in lst.split(",") if c.strip()]
            self.culturas = json.dumps(culturas_split)
            self.cultura = culturas_split[0] if culturas_split else self.cultura

    def to_dict(self):
        culturas_list = self.get_culturas_list()
        return {"id": self.id, "nome": self.nome, "proprietario": self.proprietario,
                "localizacao": self.localizacao, "hectares": self.hectares,
                "cultura": self.cultura,
                "culturas": culturas_list,
                "status": self.status,
                "activated_at": self.activated_at.isoformat() + 'Z' if self.activated_at else None,
                "created_at": self.created_at.isoformat() + 'Z'}

# =====================================================
# SENSOR
# =====================================================
class Sensor(db.Model):
    __tablename__ = "sensores"
    id          = db.Column(db.Integer, primary_key=True)
    nome        = db.Column(db.String(80), nullable=False)
    tipo        = db.Column(db.String(50))          # Clima | Solo | GPS | Câmara
    fazenda_id  = db.Column(db.Integer, db.ForeignKey("fazendas.id"))
    fazenda     = db.relationship("Fazenda", backref="sensores")
    status      = db.Column(db.String(20), default="online")  # online | offline | warn
    bateria     = db.Column(db.Integer, default=100)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "nome": self.nome, "tipo": self.tipo,
                "fazenda": self.fazenda.nome if self.fazenda else None,
                "fazenda_id": self.fazenda_id,
                "status": self.status, "bateria": self.bateria,
                "created_at": self.created_at.isoformat() + 'Z'}

# =====================================================
# LOG DE SISTEMA
# =====================================================
class Log(db.Model):
    __tablename__ = "logs"
    id         = db.Column(db.Integer, primary_key=True)
    acao       = db.Column(db.String(120))
    detalhe    = db.Column(db.String(255))
    utilizador = db.Column(db.String(120))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "acao": self.acao, "detalhe": self.detalhe,
                "utilizador": self.utilizador, "created_at": self.created_at.isoformat() + 'Z'}

# =====================================================
# DADOS IOT
# =====================================================
class DadosIoT(db.Model):
    __tablename__ = "dados_iot"
    id            = db.Column(db.Integer, primary_key=True)
    device_id     = db.Column(db.String(50), nullable=False, index=True)
    timestamp     = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    latitude      = db.Column(db.Float, nullable=False)
    longitude     = db.Column(db.Float, nullable=False)
    localizacao   = db.Column(db.String(100))
    temperatura_ar= db.Column(db.Float)
    humidade_ar   = db.Column(db.Float)
    pressao_ar    = db.Column(db.Float)
    humidade_solo = db.Column(db.Float)
    vibracao      = db.Column(db.Boolean)
    detecao_praga = db.Column(db.Boolean)
    tipo_praga    = db.Column(db.String(50))
    confianca     = db.Column(db.Float)

    def __repr__(self): return f"<DadosIoT {self.device_id} {self.timestamp}>"

# =====================================================
# MENSAGEM (Apoio e Reclamações)
# =====================================================
class Mensagem(db.Model):
    __tablename__ = "mensagens"
    id             = db.Column(db.Integer, primary_key=True)
    user_id        = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    user           = db.relationship("User", backref="mensagens")
    # Campos para mensagens do formulário de contacto (sem user_id)
    nome_contacto  = db.Column(db.String(150))   # nome preenchido no form
    email_contacto = db.Column(db.String(200))   # email preenchido no form
    telefone       = db.Column(db.String(30))    # telefone
    origem         = db.Column(db.String(30), default="dashboard")  # 'dashboard' | 'contacto'
    assunto        = db.Column(db.String(200), nullable=False)
    conteudo       = db.Column(db.Text, nullable=False)
    prioridade     = db.Column(db.String(20), default="normal")  # critico | alto | normal | baixo
    status         = db.Column(db.String(20), default="aberto")  # aberto | respondido | fechado
    resposta       = db.Column(db.Text)
    respondido_por = db.Column(db.String(120))
    respondido_em  = db.Column(db.DateTime)
    lida_admin     = db.Column(db.Boolean, default=False)
    created_at     = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        # Nome e email: preferir dados do utilizador registado; fallback para campos livres
        nome  = (self.user.nome  if self.user else None) or getattr(self, 'nome_contacto',  None) or "—"
        email = (self.user.email if self.user else None) or getattr(self, 'email_contacto', None) or "—"
        return {
            "id": self.id,
            "user_id": self.user_id,
            "nome": nome,
            "email": email,
            "telefone": getattr(self, 'telefone', None),
            "origem": getattr(self, 'origem', None) or "dashboard",
            "assunto": self.assunto,
            "conteudo": self.conteudo,
            "prioridade": self.prioridade,
            "status": self.status,
            "resposta": self.resposta,
            "respondido_por": self.respondido_por,
            "respondido_em": self.respondido_em.isoformat() + 'Z' if self.respondido_em else None,
            "lida_admin": self.lida_admin,
            "created_at": self.created_at.isoformat() + 'Z'
        }

    def __repr__(self): return f"<Mensagem {self.id} de {self.user_id}>"

# =====================================================
# PREVISÕES ML
# =====================================================
class Previsao(db.Model):
    __tablename__ = "previsoes"
    id                  = db.Column(db.Integer, primary_key=True)
    dados_iot_id        = db.Column(db.Integer, db.ForeignKey("dados_iot.id"), nullable=False)
    praga_detectada     = db.Column(db.Boolean, default=False)
    tipo_praga          = db.Column(db.String(100))
    confianca_praga     = db.Column(db.Float)
    temperatura_prevista= db.Column(db.Float)
    humidade_prevista   = db.Column(db.Float)
    data_criacao        = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def __repr__(self): return f"<Previsao {self.id} - Praga: {self.praga_detectada}>"

# =====================================================
# ZONAS DE CULTIVO
# =====================================================
class Zona(db.Model):
    __tablename__ = "zonas"
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    fazenda_id  = db.Column(db.Integer, db.ForeignKey("fazendas.id"), nullable=True)
    nome        = db.Column(db.String(120), nullable=False)
    cultura     = db.Column(db.String(120), nullable=False)
    tipo        = db.Column(db.String(80))
    area_ha     = db.Column(db.Float, default=0.0)
    estagio     = db.Column(db.String(50))
    saude       = db.Column(db.String(30))
    acoes       = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at  = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "fazenda_id": self.fazenda_id,
            "nome": self.nome,
            "cultura": self.cultura,
            "tipo": self.tipo,
            "area": self.area_ha,
            "estagio": self.estagio,
            "saude": self.saude,
            "acoes": self.acoes,
            "created_at": self.created_at.isoformat() + 'Z' if self.created_at else None,
            "updated_at": self.updated_at.isoformat() + 'Z' if self.updated_at else None
        }