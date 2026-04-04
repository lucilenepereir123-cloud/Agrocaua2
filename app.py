import os
import sys
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import db
from routes import api_routes
from config import Config
from auth_routes import auth_bp, blacklist
from dashboard_routes import dashboard_bp, auth_pages_bp
from admin_api_routes import admin_api_bp
from zones_export_routes import zones_export_bp

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db.init_app(app)
jwt = JWTManager(app)

@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    return jwt_payload.get("jti") in blacklist

# Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(api_routes)
app.register_blueprint(auth_pages_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(admin_api_bp)
app.register_blueprint(zones_export_bp)

with app.app_context():
    db.create_all(checkfirst=True)

    # ── Migração: adicionar colunas novas se não existirem ──
    from sqlalchemy import text, inspect as sa_inspect
    try:
        inspector = sa_inspect(db.engine)
        # mensagens
        if inspector.has_table('mensagens'):
            existing_cols = [c['name'] for c in inspector.get_columns('mensagens')]
            migrations = [
                ("origem",         "VARCHAR(30) DEFAULT 'dashboard'"),
                ("telefone",       "VARCHAR(30)"),
                ("nome_contacto",  "VARCHAR(150)"),
                ("email_contacto", "VARCHAR(200)"),
            ]
            for col_name, col_def in migrations:
                if col_name not in existing_cols:
                    try:
                        with db.engine.connect() as conn:
                            conn.execute(text(f"ALTER TABLE mensagens ADD COLUMN {col_name} {col_def}"))
                            conn.commit()
                        print(f"[Migration] Coluna '{col_name}' adicionada a mensagens.")
                    except Exception as e:
                        print(f"[Migration] Aviso ao adicionar coluna {col_name}: {e}")
        # users.fazenda_id
        if inspector.has_table('users'):
            ucols = [c['name'] for c in inspector.get_columns('users')]
            if 'fazenda_id' not in ucols:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE users ADD COLUMN fazenda_id INTEGER"))
                        conn.commit()
                    print("[Migration] Coluna 'fazenda_id' adicionada a users.")
                except Exception as e:
                    print(f"[Migration] Aviso ao adicionar users.fazenda_id: {e}")
        # fazendas.activation_code, activated_at, culturas
        if inspector.has_table('fazendas'):
            fcols = [c['name'] for c in inspector.get_columns('fazendas')]
            if 'activation_code' not in fcols:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE fazendas ADD COLUMN activation_code VARCHAR(10) DEFAULT '0123'"))
                        conn.commit()
                    print("[Migration] Coluna 'activation_code' adicionada a fazendas.")
                except Exception as e:
                    print(f"[Migration] Aviso ao adicionar fazendas.activation_code: {e}")
            if 'activated_at' not in fcols:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE fazendas ADD COLUMN activated_at DATETIME"))
                        conn.commit()
                    print("[Migration] Coluna 'activated_at' adicionada a fazendas.")
                except Exception as e:
                    print(f"[Migration] Aviso ao adicionar fazendas.activated_at: {e}")
            if 'culturas' not in fcols:
                try:
                    with db.engine.connect() as conn:
                        conn.execute(text("ALTER TABLE fazendas ADD COLUMN culturas TEXT DEFAULT '[]'"))
                        conn.commit()
                    print("[Migration] Coluna 'culturas' adicionada a fazendas.")
                    # Popular culturas a partir do campo legado 'cultura'
                    import json
                    with db.engine.connect() as conn:
                        rows = conn.execute(text("SELECT id, cultura FROM fazendas WHERE cultura IS NOT NULL AND cultura != ''")).fetchall()
                        for row in rows:
                            fid, cult = row[0], row[1]
                            culturas_json = json.dumps([c.strip().lower() for c in cult.split(',') if c.strip()])
                            conn.execute(text(f"UPDATE fazendas SET culturas = :c WHERE id = :id"), {"c": culturas_json, "id": fid})
                        conn.commit()
                    print("[Migration] Campo 'culturas' populado a partir de 'cultura'.")
                except Exception as e:
                    print(f"[Migration] Aviso ao adicionar fazendas.culturas: {e}")
    except Exception as e:
        print(f"[Migration] Erro na verificacao de colunas: {e}")

    # Garantir que existe sempre pelo menos um superadmin
    from models import User, Fazenda
    if not User.query.filter_by(email="admin@agrocaua.com").first():
        u = User(nome="Administrador", email="admin@agrocaua.com", role="superadmin")
        u.set_password("admin123")
        db.session.add(u)
        db.session.commit()
    # Garantir que fazendas existentes tenham activation_code definido
    try:
        for f in Fazenda.query.all():
            if not getattr(f, 'activation_code', None):
                f.activation_code = "0123"
        db.session.commit()
    except Exception as e:
        print(f"[Init] Aviso ao definir activation_code nas fazendas: {e}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
