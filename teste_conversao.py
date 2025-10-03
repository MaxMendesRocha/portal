#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar a conversão de horas decimais para horas:minutos
"""

def horas_para_hm(horas_decimais):
    """Converte horas decimais para formato HH:MM"""
    if horas_decimais == 0:
        return "0h 0min"
    
    horas = int(horas_decimais)
    minutos = int((horas_decimais - horas) * 60)
    
    if horas > 0 and minutos > 0:
        return f"{horas}h {minutos}min"
    elif horas > 0:
        return f"{horas}h"
    else:
        return f"{minutos}min"

print("🧮 TESTE DE CONVERSÃO DE HORAS DECIMAIS")
print("=" * 50)

# Casos de teste
testes = [
    1.42,   # Caso atual
    0.5,    # 30 minutos
    2.0,    # 2 horas exatas
    0.25,   # 15 minutos
    8.5,    # 8h 30min
    0.0,    # Zero
    3.75,   # 3h 45min
    1.0,    # 1 hora exata
    0.17,   # ~10 minutos
    2.33    # 2h ~20min
]

for horas_decimal in testes:
    resultado = horas_para_hm(horas_decimal)
    print(f"{horas_decimal:5.2f}h  →  {resultado}")

print("\n✅ Teste específico do registro atual:")
print(f"1.42h  →  {horas_para_hm(1.42)}")
print("(Deve mostrar: 1h 25min)")

# Verificação manual
horas = int(1.42)
minutos = int((1.42 - horas) * 60)
print(f"\nVerificação: {horas}h + {minutos}min = {horas}h {minutos}min")
