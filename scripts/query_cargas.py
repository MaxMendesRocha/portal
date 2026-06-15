import sqlite3

con = sqlite3.connect('horas_trabalho.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

print('FUNCIONARIOS:')
for r in cur.execute("SELECT id,nome FROM funcionarios"):
    print(r['id'], r['nome'])

print('\nCARGAS (ativas):')
for r in cur.execute("SELECT ch.id, ch.funcionario_id, ch.inicio, ch.fim, ch.dias_semana, ch.intervalo_min, ch.ativo, f.nome as funcionario_nome FROM carga_horaria ch LEFT JOIN funcionarios f ON ch.funcionario_id = f.id WHERE ch.ativo = 1"):
    print(r['id'], r['funcionario_nome'], r['inicio'], r['fim'], r['dias_semana'], r['intervalo_min'])

con.close()
