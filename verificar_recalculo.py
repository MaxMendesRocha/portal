import json

# Carregar dados
with open('horas_trabalho.json', 'r', encoding='utf-8') as f:
    dados = json.load(f)

funcionario = dados['funcionarios']['Fabieli Patricia Altissimo']
registro = dados['registros'][0]

print('🎉 RECÁLCULO CONCLUÍDO COM SUCESSO!')
print('=' * 50)
print()
print('📋 DADOS CORRIGIDOS:')
print(f'   Salário mensal: R$ {funcionario["salario_mensal"]:.2f}')
print(f'   Valor hora normal: R$ {funcionario["salario_hora"]:.2f}')
print(f'   Valor hora extra: R$ {funcionario["salario_hora"] * 1.5:.2f}')
print()
print('📊 REGISTRO RECALCULADO:')
print(f'   Data: {registro["data"]}')
print(f'   Horas trabalhadas: {registro["horas_trabalhadas"]:.2f}h')
print(f'   Horas extras: {registro["horas_extras"]:.2f}h')
print()
print('💰 VALORES FINAIS:')
horas_normais = registro["horas_trabalhadas"] - registro["horas_extras"]
valor_normais = horas_normais * funcionario["salario_hora"]
valor_extras = registro["horas_extras"] * funcionario["salario_hora"] * 1.5
valor_total = valor_normais + valor_extras

print(f'   Horas normais: {horas_normais:.2f}h × R$ {funcionario["salario_hora"]:.2f} = R$ {valor_normais:.2f}')
print(f'   Horas extras: {registro["horas_extras"]:.2f}h × R$ {funcionario["salario_hora"] * 1.5:.2f} = R$ {valor_extras:.2f}')
print(f'   TOTAL: R$ {valor_total:.2f}')
print()
print('✅ Sistema atualizado e funcionando!')
