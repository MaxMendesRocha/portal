#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar e demonstrar a correção no cálculo de horas extras
"""

def horas_para_hm_old(horas_decimais):
    """Versão ANTIGA com problema de truncamento"""
    if horas_decimais == 0:
        return "0h 0min"
    
    horas = int(horas_decimais)
    minutos = int((horas_decimais - horas) * 60)  # PROBLEMA: int() trunca
    
    if horas > 0 and minutos > 0:
        return f"{horas}h {minutos}min"
    elif horas > 0:
        return f"{horas}h"
    else:
        return f"{minutos}min"

def horas_para_hm_new(horas_decimais):
    """Versão NOVA com arredondamento correto"""
    if horas_decimais == 0:
        return "0h 0min"
    
    horas = int(horas_decimais)
    minutos = round((horas_decimais - horas) * 60)  # CORREÇÃO: round() arredonda
    
    # Ajustar quando minutos chegam a 60 devido ao arredondamento
    if minutos >= 60:
        horas += 1
        minutos = 0
    
    if horas > 0 and minutos > 0:
        return f"{horas}h {minutos}min"
    elif horas > 0:
        return f"{horas}h"
    else:
        return f"{minutos}min"

def calcular_horas_extras(horas_trabalhadas, horas_normais=8):
    """Calcula horas extras baseado nas horas trabalhadas no dia"""
    if horas_trabalhadas > horas_normais:
        return horas_trabalhadas - horas_normais
    return 0

if __name__ == "__main__":
    print("🔍 TESTE DE CORREÇÃO - CÁLCULO DE HORAS EXTRAS")
    print("=" * 60)
    
    # Casos de teste problemáticos
    casos_teste = [
        2.9833333333,  # 2h 59min (anteriormente mostrava 2h 58min)
        1.9833333333,  # 1h 59min (anteriormente mostrava 1h 58min)  
        3.0166666667,  # 3h 1min
        2.5,           # 2h 30min
        1.9666666667,  # 1h 58min
        2.9666666667,  # 2h 58min
        9.0166666667,  # 9h 1min = 1h 1min extra
        10.9833333333, # 10h 59min = 2h 59min extra
    ]
    
    print("COMPARAÇÃO - VERSÃO ANTIGA vs NOVA:")
    print("-" * 60)
    
    for horas in casos_teste:
        old_result = horas_para_hm_old(horas)
        new_result = horas_para_hm_new(horas)
        
        # Calcular horas extras
        extras = calcular_horas_extras(horas)
        extras_old = horas_para_hm_old(extras)
        extras_new = horas_para_hm_new(extras)
        
        problema = "⚠️  PROBLEMA!" if old_result != new_result else "✅ OK"
        
        print(f"Horas decimais: {horas:.10f}")
        print(f"  Antiga: {old_result:>12} | Nova: {new_result:>12} {problema}")
        print(f"  Extras antigas: {extras_old:>8} | Extras novas: {extras_new:>8}")
        print()
    
    print("EXPLICAÇÃO DO PROBLEMA:")
    print("-" * 60)
    print("• int(0.98333 * 60) = int(58.9998) = 58 ❌")
    print("• round(0.98333 * 60) = round(58.9998) = 59 ✅")
    print()
    print("RESULTADO: Correção elimina o problema de 1 minuto a menos!")
    print("=" * 60)
