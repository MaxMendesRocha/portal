import sqlite3
from datetime import datetime

def criar_tabela_gastos():
    """Cria a tabela de gastos domésticos no banco SQLite"""
    conn = sqlite3.connect('horas_trabalho.db')
    cursor = conn.cursor()
    
    # Criar tabela de gastos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS gastos_domesticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            data_gasto DATE NOT NULL,
            forma_pagamento TEXT NOT NULL,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    print("✅ Tabela 'gastos_domesticos' criada com sucesso!")
    
    # Verificar se a tabela foi criada
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='gastos_domesticos';")
    result = cursor.fetchone()
    
    if result:
        print(f"✅ Tabela confirmada: {result[0]}")
        
        # Mostrar estrutura da tabela
        cursor.execute("PRAGMA table_info(gastos_domesticos);")
        columns = cursor.fetchall()
        print("\n📋 Estrutura da tabela:")
        for col in columns:
            print(f"   {col[1]} ({col[2]})")
    else:
        print("❌ Erro: Tabela não foi criada")
    
    conn.close()

if __name__ == "__main__":
    criar_tabela_gastos()
