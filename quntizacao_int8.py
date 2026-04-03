'''# criar_banco_simples.py
import os
import sqlite3
from flask import Flask
from models import db

# Criar app
app = Flask(__name__)

# Configurar banco DIRETAMENTE (sem usar config.py por enquanto)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

print("=== CRIANDO BANCO ===\n")

with app.app_context():
    # Criar todas as tabelas
    db.create_all()
    print("Tabelas criadas!")
    
    # Verificar se o arquivo existe
    if os.path.exists('database.db'):
        print(f"✅ Banco criado: {os.path.abspath('database.db')}")
        print(f"Tamanho: {os.path.getsize('database.db')} bytes")
    else:
        print("❌ Banco não encontrado")
        
        # Tentar criar manualmente com sqlite3
        conn = sqlite3.connect('database.db')
        conn.close()
        if os.path.exists('database.db'):
            print(f"✅ Banco criado manualmente: {os.path.abspath('database.db')}")
    
    # Listar tabelas
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    tables = inspector.get_table_names()
    
    if tables:
        print(f"\nTabelas criadas ({len(tables)}):")
        for table in tables:
            print(f"  - {table}")
    else:
        print("\n⚠️ Nenhuma tabela foi criada!")
        
        # Tentar criar tabelas uma por uma
        print("\nTentando criar tabelas manualmente...")
        from models import User, Fazenda, Sensor, Log, DadosIoT, DispositivoIoT
        
        db.create_all()
        tables = inspector.get_table_names()
        if tables:
            print(f"✅ Agora foram criadas: {', '.join(tables)}")

print("\n=== FIM ===")'''