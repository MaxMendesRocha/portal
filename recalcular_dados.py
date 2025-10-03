#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para recalcular todas as horas e valores já lançados
Corrige dados existentes com o novo valor de salário mensal R$ 1.518,00
"""

import json
import os
from datetime import datetime

# Arquivo de dados
DATA_FILE = 'horas_trabalho.json'

def carregar_dados():
    """Carrega os dados do arquivo JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'funcionarios': {}, 'registros': []}

def salvar_dados(dados):
    """Salva os dados no arquivo JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def backup_dados():
    """Cria backup dos dados antes da modificação"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_horas_trabalho_{timestamp}.json'
    
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f_origem:
            with open(backup_file, 'w', encoding='utf-8') as f_backup:
                f_backup.write(f_origem.read())
        print(f"✅ Backup criado: {backup_file}")
        return backup_file
    return None

def recalcular_funcionarios(dados):
    """Recalcula dados dos funcionários com novo salário padrão"""
    print("\n📋 RECALCULANDO DADOS DOS FUNCIONÁRIOS:")
    print("=" * 50)
    
    # Salário mensal padrão
    SALARIO_MENSAL_PADRAO = 1518.00
    HORAS_MENSAIS = 220
    
    funcionarios_alterados = 0
    
    for nome, funcionario in dados['funcionarios'].items():
        print(f"\n👤 Funcionário: {nome}")
        
        # Valores antigos
        salario_mensal_antigo = funcionario.get('salario_mensal', 0)
        salario_hora_antigo = funcionario.get('salario_hora', 0)
        
        print(f"   Salário mensal antigo: R$ {salario_mensal_antigo:.2f}")
        print(f"   Salário hora antigo: R$ {salario_hora_antigo:.2f}")
        
        # Atualizar com valores corretos
        funcionario['salario_mensal'] = SALARIO_MENSAL_PADRAO
        funcionario['salario_hora'] = SALARIO_MENSAL_PADRAO / HORAS_MENSAIS
        funcionario['horas_mensais'] = HORAS_MENSAIS
        
        print(f"   ✅ Salário mensal novo: R$ {funcionario['salario_mensal']:.2f}")
        print(f"   ✅ Salário hora novo: R$ {funcionario['salario_hora']:.2f}")
        
        funcionarios_alterados += 1
    
    print(f"\n📊 Total de funcionários atualizados: {funcionarios_alterados}")
    return funcionarios_alterados

def validar_registros(dados):
    """Valida se os registros estão com cálculos corretos"""
    print("\n🔍 VALIDANDO REGISTROS EXISTENTES:")
    print("=" * 50)
    
    registros_validados = 0
    registros_com_problemas = 0
    
    for i, registro in enumerate(dados['registros']):
        registros_validados += 1
        
        # Verificar se tem todos os campos necessários
        campos_obrigatorios = ['hora_entrada', 'hora_saida_almoco', 'hora_volta_almoco', 'hora_saida']
        campos_faltando = [campo for campo in campos_obrigatorios if campo not in registro]
        
        if campos_faltando:
            print(f"⚠️  Registro {i+1} - {registro.get('funcionario', 'N/A')} - {registro.get('data', 'N/A')}")
            print(f"     Campos faltando: {', '.join(campos_faltando)}")
            registros_com_problemas += 1
        else:
            # Recalcular horas para verificar se estão corretas
            try:
                data = registro['data']
                hora_entrada = registro['hora_entrada']
                hora_saida_almoco = registro['hora_saida_almoco']
                hora_volta_almoco = registro['hora_volta_almoco']
                hora_saida = registro['hora_saida']
                
                # Converter para datetime para calcular horas
                entrada = datetime.strptime(f"{data} {hora_entrada}", "%Y-%m-%d %H:%M")
                saida_almoco = datetime.strptime(f"{data} {hora_saida_almoco}", "%Y-%m-%d %H:%M")
                volta_almoco = datetime.strptime(f"{data} {hora_volta_almoco}", "%Y-%m-%d %H:%M")
                saida = datetime.strptime(f"{data} {hora_saida}", "%Y-%m-%d %H:%M")
                
                # Calcular horas trabalhadas (descontando o almoço)
                periodo_manha = saida_almoco - entrada
                periodo_tarde = saida - volta_almoco
                
                horas_manha = periodo_manha.total_seconds() / 3600
                horas_tarde = periodo_tarde.total_seconds() / 3600
                horas_trabalhadas_calculadas = horas_manha + horas_tarde
                
                # Calcular tempo de almoço
                tempo_almoco = volta_almoco - saida_almoco
                tempo_almoco_horas = tempo_almoco.total_seconds() / 3600
                
                # Calcular horas extras
                horas_extras_calculadas = max(0, horas_trabalhadas_calculadas - 8)
                
                # Verificar se os valores estão corretos
                horas_trabalhadas_registro = registro.get('horas_trabalhadas', 0)
                horas_extras_registro = registro.get('horas_extras', 0)
                
                if (abs(horas_trabalhadas_calculadas - horas_trabalhadas_registro) > 0.01 or
                    abs(horas_extras_calculadas - horas_extras_registro) > 0.01):
                    
                    print(f"⚠️  Registro {i+1} - {registro.get('funcionario', 'N/A')} - {data}")
                    print(f"     Horas trabalhadas: {horas_trabalhadas_registro:.2f} → {horas_trabalhadas_calculadas:.2f}")
                    print(f"     Horas extras: {horas_extras_registro:.2f} → {horas_extras_calculadas:.2f}")
                    
                    # Corrigir os valores
                    registro['horas_trabalhadas'] = round(horas_trabalhadas_calculadas, 2)
                    registro['horas_extras'] = round(horas_extras_calculadas, 2)
                    registro['tempo_almoco'] = round(tempo_almoco_horas, 2)
                    
                    # Marcar como recalculado
                    registro['data_recalculo'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    registros_com_problemas += 1
                    print(f"     ✅ Corrigido!")
                    
            except Exception as e:
                print(f"❌ Erro ao validar registro {i+1}: {e}")
                registros_com_problemas += 1
    
    print(f"\n📊 Registros validados: {registros_validados}")
    print(f"📊 Registros corrigidos: {registros_com_problemas}")
    
    return registros_validados, registros_com_problemas

def exibir_resumo_final(dados):
    """Exibe resumo final dos dados recalculados"""
    print("\n🎯 RESUMO FINAL:")
    print("=" * 50)
    
    # Funcionários
    print(f"👥 Funcionários cadastrados: {len(dados['funcionarios'])}")
    for nome, funcionario in dados['funcionarios'].items():
        print(f"   • {nome}")
        print(f"     Cargo: {funcionario.get('cargo', 'N/A')}")
        print(f"     Salário mensal: R$ {funcionario.get('salario_mensal', 0):.2f}")
        print(f"     Valor hora: R$ {funcionario.get('salario_hora', 0):.2f}")
        print(f"     Valor hora extra: R$ {funcionario.get('salario_hora', 0) * 1.5:.2f}")
    
    # Registros
    print(f"\n📅 Total de registros: {len(dados['registros'])}")
    
    # Calcular totais
    total_horas_normais = 0
    total_horas_extras = 0
    
    for registro in dados['registros']:
        horas_trabalhadas = registro.get('horas_trabalhadas', 0)
        horas_extras = registro.get('horas_extras', 0)
        
        horas_normais = horas_trabalhadas - horas_extras
        total_horas_normais += horas_normais
        total_horas_extras += horas_extras
    
    print(f"   📊 Total horas normais: {total_horas_normais:.2f}h")
    print(f"   📊 Total horas extras: {total_horas_extras:.2f}h")
    
    # Calcular valores com novo salário
    if dados['funcionarios']:
        primeiro_funcionario = list(dados['funcionarios'].values())[0]
        valor_hora = primeiro_funcionario.get('salario_hora', 0)
        valor_hora_extra = valor_hora * 1.5
        
        valor_total_normais = total_horas_normais * valor_hora
        valor_total_extras = total_horas_extras * valor_hora_extra
        valor_total_geral = valor_total_normais + valor_total_extras
        
        print(f"   💰 Valor horas normais: R$ {valor_total_normais:.2f}")
        print(f"   💰 Valor horas extras: R$ {valor_total_extras:.2f}")
        print(f"   💰 VALOR TOTAL: R$ {valor_total_geral:.2f}")

def main():
    """Função principal"""
    print("🔄 RECALCULADOR DE HORAS TRABALHADAS")
    print("=" * 50)
    print("📝 Este script irá:")
    print("   1. Criar backup dos dados atuais")
    print("   2. Corrigir salários dos funcionários")
    print("   3. Validar e corrigir cálculos de registros")
    print("   4. Salvar dados corrigidos")
    print()
    
    # Verificar se arquivo existe
    if not os.path.exists(DATA_FILE):
        print(f"❌ Arquivo {DATA_FILE} não encontrado!")
        return
    
    # Fazer backup
    backup_file = backup_dados()
    if not backup_file:
        print("❌ Erro ao criar backup!")
        return
    
    # Carregar dados
    dados = carregar_dados()
    print(f"📂 Dados carregados: {len(dados['funcionarios'])} funcionários, {len(dados['registros'])} registros")
    
    # Recalcular funcionários
    funcionarios_alterados = recalcular_funcionarios(dados)
    
    # Validar registros
    registros_validados, registros_corrigidos = validar_registros(dados)
    
    # Salvar dados atualizados
    salvar_dados(dados)
    print(f"\n💾 Dados salvos em {DATA_FILE}")
    
    # Exibir resumo
    exibir_resumo_final(dados)
    
    print(f"\n✅ RECÁLCULO CONCLUÍDO COM SUCESSO!")
    print(f"📋 Funcionários atualizados: {funcionarios_alterados}")
    print(f"📋 Registros corrigidos: {registros_corrigidos}")
    print(f"🔒 Backup salvo em: {backup_file}")

if __name__ == '__main__':
    main()
