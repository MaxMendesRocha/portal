from datetime import datetime

# Horários do registro
entrada = datetime.strptime('2025-09-22 08:00', '%Y-%m-%d %H:%M')
saida_almoco = datetime.strptime('2025-09-22 12:00', '%Y-%m-%d %H:%M')
volta_almoco = datetime.strptime('2025-09-22 13:00', '%Y-%m-%d %H:%M')
saida = datetime.strptime('2025-09-22 18:25', '%Y-%m-%d %H:%M')

# Cálculo correto
periodo_manha = saida_almoco - entrada
periodo_tarde = saida - volta_almoco

print('ANÁLISE DO REGISTRO:')
print('=' * 30)
print(f'Entrada: 08:00')
print(f'Saída almoço: 12:00')
print(f'Volta almoço: 13:00') 
print(f'Saída: 18:25')
print()
print('CÁLCULOS:')
print(f'Período manhã: {periodo_manha} = {periodo_manha.total_seconds()/3600:.2f}h')
print(f'Período tarde: {periodo_tarde} = {periodo_tarde.total_seconds()/3600:.2f}h')

horas_trabalhadas = periodo_manha.total_seconds()/3600 + periodo_tarde.total_seconds()/3600
horas_extras = max(0, horas_trabalhadas - 8)

print(f'Total trabalhado: {horas_trabalhadas:.2f}h')
print(f'Jornada normal: 8.00h')
print(f'Horas extras: {horas_extras:.2f}h')
print()

# Converter para horas e minutos
horas = int(horas_extras)
minutos = int((horas_extras - horas) * 60)
print(f'Horas extras: {horas}h {minutos}min')

# Verificar o que está no arquivo
import json
with open('horas_trabalho.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

registro = dados['registros'][0]
print()
print('VALORES NO ARQUIVO:')
print(f'Horas trabalhadas: {registro["horas_trabalhadas"]}h')
print(f'Horas extras: {registro["horas_extras"]}h')

# Converter horas extras do arquivo
horas_arquivo = int(registro["horas_extras"])
minutos_arquivo = int((registro["horas_extras"] - horas_arquivo) * 60)
print(f'Horas extras arquivo: {horas_arquivo}h {minutos_arquivo}min')
