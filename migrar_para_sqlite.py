#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para criar banco SQLite e migrar dados do JSON
"""

import sqlite3
import json
import os
from datetime import datetime

# Arquivos
JSON_FILE = 'horas_trabalho.json'
DB_FILE = 'horas_trabalho.db'

def criar_banco():
    """Cria o banco SQLite com as tabelas necessárias"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Criar tabela de funcionários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS funcionarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL UNIQUE,
            cargo TEXT NOT NULL,
            salario_mensal REAL NOT NULL,
            salario_hora REAL NOT NULL,
            horas_mensais INTEGER NOT NULL DEFAULT 220,
            data_cadastro DATE NOT NULL,
            ativo BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Criar tabela de registros de ponto
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registros_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario_id INTEGER NOT NULL,
            data DATE NOT NULL,
            dia INTEGER NOT NULL,
            mes INTEGER NOT NULL,
            ano INTEGER NOT NULL,
            hora_entrada TIME NOT NULL,
            hora_saida_almoco TIME NOT NULL,
            hora_volta_almoco TIME NOT NULL,
            hora_saida TIME NOT NULL,
            tempo_almoco REAL NOT NULL,
            horas_trabalhadas REAL NOT NULL,
            horas_extras REAL NOT NULL,
            data_registro TIMESTAMP NOT NULL,
            data_edicao TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (funcionario_id) REFERENCES funcionarios (id),
            UNIQUE(funcionario_id, data)
        )
    ''')
    
    # Criar índices para melhor performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_funcionarios_nome ON funcionarios(nome)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registros_funcionario ON registros_ponto(funcionario_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registros_data ON registros_ponto(data)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_registros_mes_ano ON registros_ponto(mes, ano)')
    
    # Criar trigger para atualizar updated_at automaticamente
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_funcionarios_updated_at 
        AFTER UPDATE ON funcionarios
        BEGIN
            UPDATE funcionarios SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
    ''')
    
    cursor.execute('''
        CREATE TRIGGER IF NOT EXISTS update_registros_updated_at 
        AFTER UPDATE ON registros_ponto
        BEGIN
            UPDATE registros_ponto SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
        END
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ Banco SQLite criado com sucesso!")
    print(f"   Arquivo: {DB_FILE}")
    print("   Tabelas: funcionarios, registros_ponto")
    print("   Índices e triggers configurados")

def migrar_dados():
    """Migra dados do JSON para o SQLite"""
    if not os.path.exists(JSON_FILE):
        print(f"❌ Arquivo {JSON_FILE} não encontrado!")
        return
    
    # Carregar dados do JSON
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        dados = json.load(f)
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    try:
        # Migrar funcionários
        print("\n📋 MIGRANDO FUNCIONÁRIOS:")
        print("-" * 40)
        
        funcionarios_migrados = 0
        funcionario_ids = {}
        
        for nome, funcionario in dados.get('funcionarios', {}).items():
            cursor.execute('''
                INSERT OR REPLACE INTO funcionarios 
                (nome, cargo, salario_mensal, salario_hora, horas_mensais, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                nome,
                funcionario.get('cargo', ''),
                funcionario.get('salario_mensal', 1518.00),
                funcionario.get('salario_hora', 6.90),
                funcionario.get('horas_mensais', 220),
                funcionario.get('data_cadastro', datetime.now().strftime('%Y-%m-%d'))
            ))
            
            # Obter o ID do funcionário
            cursor.execute('SELECT id FROM funcionarios WHERE nome = ?', (nome,))
            funcionario_id = cursor.fetchone()[0]
            funcionario_ids[nome] = funcionario_id
            
            funcionarios_migrados += 1
            print(f"   ✅ {nome} (ID: {funcionario_id})")
        
        print(f"   📊 Total: {funcionarios_migrados} funcionários")
        
        # Migrar registros de ponto
        print("\n📅 MIGRANDO REGISTROS DE PONTO:")
        print("-" * 40)
        
        registros_migrados = 0
        
        for registro in dados.get('registros', []):
            funcionario_nome = registro.get('funcionario')
            funcionario_id = funcionario_ids.get(funcionario_nome)
            
            if not funcionario_id:
                print(f"   ⚠️  Funcionário não encontrado: {funcionario_nome}")
                continue
            
            cursor.execute('''
                INSERT OR REPLACE INTO registros_ponto 
                (funcionario_id, data, dia, mes, ano, hora_entrada, hora_saida_almoco, 
                 hora_volta_almoco, hora_saida, tempo_almoco, horas_trabalhadas, 
                 horas_extras, data_registro, data_edicao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                funcionario_id,
                registro.get('data'),
                registro.get('dia'),
                registro.get('mes'),
                registro.get('ano'),
                registro.get('hora_entrada'),
                registro.get('hora_saida_almoco'),
                registro.get('hora_volta_almoco'),
                registro.get('hora_saida'),
                registro.get('tempo_almoco', 0.0),
                registro.get('horas_trabalhadas', 0.0),
                registro.get('horas_extras', 0.0),
                registro.get('data_registro'),
                registro.get('data_edicao')
            ))
            
            registros_migrados += 1
            data_reg = registro.get('data', 'N/A')
            horas_trab = registro.get('horas_trabalhadas', 0)
            print(f"   ✅ {funcionario_nome} - {data_reg} ({horas_trab:.2f}h)")
        
        print(f"   📊 Total: {registros_migrados} registros")
        
        conn.commit()
        print(f"\n✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
        
    except Exception as e:
        print(f"❌ Erro durante migração: {e}")
        conn.rollback()
        
    finally:
        conn.close()

def verificar_migracao():
    """Verifica se a migração foi bem-sucedida"""
    if not os.path.exists(DB_FILE):
        print("❌ Banco não encontrado!")
        return
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    print("\n🔍 VERIFICAÇÃO DA MIGRAÇÃO:")
    print("=" * 50)
    
    # Contar funcionários
    cursor.execute('SELECT COUNT(*) FROM funcionarios')
    total_funcionarios = cursor.fetchone()[0]
    print(f"👥 Funcionários no banco: {total_funcionarios}")
    
    # Listar funcionários
    cursor.execute('SELECT id, nome, cargo, salario_mensal FROM funcionarios')
    funcionarios = cursor.fetchall()
    
    for func_id, nome, cargo, salario in funcionarios:
        print(f"   • ID: {func_id} | {nome} ({cargo}) | R$ {salario:.2f}/mês")
    
    # Contar registros
    cursor.execute('SELECT COUNT(*) FROM registros_ponto')
    total_registros = cursor.fetchone()[0]
    print(f"\n📅 Registros no banco: {total_registros}")
    
    # Listar registros recentes
    cursor.execute('''
        SELECT r.data, f.nome, r.horas_trabalhadas, r.horas_extras
        FROM registros_ponto r
        JOIN funcionarios f ON r.funcionario_id = f.id
        ORDER BY r.data DESC
        LIMIT 5
    ''')
    registros = cursor.fetchall()
    
    for data, nome, horas_trab, horas_extras in registros:
        print(f"   • {data} | {nome} | {horas_trab:.2f}h (extras: {horas_extras:.2f}h)")
    
    # Estatísticas
    cursor.execute('''
        SELECT SUM(r.horas_trabalhadas), SUM(r.horas_extras)
        FROM registros_ponto r
    ''')
    total_horas, total_extras = cursor.fetchone()
    
    print(f"\n📊 ESTATÍSTICAS:")
    print(f"   Total horas trabalhadas: {total_horas:.2f}h")
    print(f"   Total horas extras: {total_extras:.2f}h")
    
    conn.close()

def backup_json():
    """Cria backup do arquivo JSON antes da migração"""
    if os.path.exists(JSON_FILE):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'backup_json_{timestamp}.json'
        
        import shutil
        shutil.copy2(JSON_FILE, backup_file)
        
        print(f"🔒 Backup JSON criado: {backup_file}")
        return backup_file
    return None

def main():
    """Função principal"""
    print("🗄️  MIGRAÇÃO PARA BANCO SQLITE")
    print("=" * 50)
    print("📝 Este script irá:")
    print("   1. Criar backup do JSON atual")
    print("   2. Criar banco SQLite")
    print("   3. Migrar todos os dados")
    print("   4. Verificar integridade")
    print()
    
    # Criar backup
    backup_file = backup_json()
    
    # Criar banco
    criar_banco()
    
    # Migrar dados
    migrar_dados()
    
    # Verificar migração
    verificar_migracao()
    
    print(f"\n🎉 MIGRAÇÃO CONCLUÍDA!")
    print(f"📁 Banco SQLite: {DB_FILE}")
    if backup_file:
        print(f"🔒 Backup JSON: {backup_file}")

if __name__ == '__main__':
    main()
