from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Arquivo do banco SQLite
DB_FILE = 'horas_trabalho.db'

class DatabaseManager:
    """Gerenciador de conexões com o banco SQLite"""
    
    @staticmethod
    def get_connection():
        """Obtém conexão com o banco"""
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row  # Permite acesso por nome de coluna
        return conn
    
    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        """Executa uma query no banco"""
        conn = DatabaseManager.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results] if results else []
            else:
                conn.commit()
                return cursor.lastrowid
        finally:
            conn.close()

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

# Registrar filtro personalizado
app.jinja_env.filters['horas_hm'] = horas_para_hm

def calcular_horas_extras(horas_trabalhadas, horas_normais=8):
    """Calcula horas extras baseado nas horas trabalhadas no dia"""
    if horas_trabalhadas > horas_normais:
        return horas_trabalhadas - horas_normais
    return 0

def calcular_total_mensal(funcionario_id, mes, ano):
    """Calcula o total de horas trabalhadas e extras no mês"""
    query = """
        SELECT 
            SUM(horas_trabalhadas) as total_horas,
            SUM(horas_extras) as total_extras,
            COUNT(*) as dias_trabalhados
        FROM registros_ponto 
        WHERE funcionario_id = ? AND mes = ? AND ano = ?
    """
    result = DatabaseManager.execute_query(query, (funcionario_id, mes, ano), fetch_one=True)
    
    return {
        'total_horas': result['total_horas'] or 0,
        'total_extras': result['total_extras'] or 0,
        'dias_trabalhados': result['dias_trabalhados'] or 0
    }

@app.route('/')
def index():
    """Página inicial"""
    query = "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome"
    funcionarios = DatabaseManager.execute_query(query, fetch_all=True)
    return render_template('index.html', funcionarios=funcionarios)

@app.route('/funcionario/<nome>')
def visualizar_funcionario(nome):
    """Visualiza os dados de um funcionário específico"""
    # Buscar funcionário
    query = "SELECT * FROM funcionarios WHERE nome = ? AND ativo = 1"
    funcionario_data = DatabaseManager.execute_query(query, (nome,), fetch_one=True)
    
    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    # Buscar registros do funcionário
    query = """
        SELECT * FROM registros_ponto 
        WHERE funcionario_id = ? 
        ORDER BY ano DESC, mes DESC, dia DESC
    """
    registros = DatabaseManager.execute_query(query, (funcionario_data['id'],), fetch_all=True)
    
    # Calcular totais por mês
    meses_anos = set((r['mes'], r['ano']) for r in registros)
    totais_mensais = []
    
    for mes, ano in meses_anos:
        total_mensal = calcular_total_mensal(funcionario_data['id'], mes, ano)
        totais_mensais.append({
            'mes': mes,
            'ano': ano,
            'total_horas': total_mensal['total_horas'],
            'total_extras': total_mensal['total_extras'],
            'dias_trabalhados': total_mensal['dias_trabalhados']
        })
    
    totais_mensais.sort(key=lambda x: (x['ano'], x['mes']), reverse=True)
    
    return render_template('funcionario.html', 
                         nome=nome, 
                         registros=registros, 
                         totais_mensais=totais_mensais,
                         funcionario_data=funcionario_data)

@app.route('/adicionar_funcionario', methods=['GET', 'POST'])
def adicionar_funcionario():
    """Adiciona um novo funcionário"""
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        
        # Calcular valor da hora baseado no salário mensal
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        
        try:
            query = """
                INSERT INTO funcionarios 
                (nome, cargo, salario_mensal, salario_hora, horas_mensais, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            DatabaseManager.execute_query(query, (
                nome, cargo, salario_mensal, salario_hora, horas_mensais,
                datetime.now().strftime('%Y-%m-%d')
            ))
            
            flash(f'Funcionário {nome} adicionado com sucesso! Salário: R$ {salario_mensal:.2f}/mês - R$ {salario_hora:.2f}/hora', 'success')
            return redirect(url_for('index'))
            
        except sqlite3.IntegrityError:
            flash(f'Funcionário {nome} já existe no sistema!', 'error')
    
    return render_template('adicionar_funcionario.html')

@app.route('/registrar_horas', methods=['GET', 'POST'])
def registrar_horas():
    """Registra horas trabalhadas"""
    if request.method == 'POST':
        funcionario_nome = request.form['funcionario']
        data = request.form['data']
        hora_entrada = request.form['hora_entrada']
        hora_saida_almoco = request.form['hora_saida_almoco']
        hora_volta_almoco = request.form['hora_volta_almoco']
        hora_saida = request.form['hora_saida']
        
        # Buscar funcionário
        query = "SELECT id FROM funcionarios WHERE nome = ?"
        funcionario = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
        
        if not funcionario:
            flash('Funcionário não encontrado!', 'error')
            return redirect(url_for('registrar_horas'))
        
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
        horas_trabalhadas = horas_manha + horas_tarde
        
        # Calcular tempo de almoço
        tempo_almoco = volta_almoco - saida_almoco
        tempo_almoco_horas = tempo_almoco.total_seconds() / 3600
        
        # Calcular horas extras
        horas_extras = calcular_horas_extras(horas_trabalhadas)
        
        try:
            # Inserir registro
            query = """
                INSERT INTO registros_ponto 
                (funcionario_id, data, dia, mes, ano, hora_entrada, hora_saida_almoco, 
                 hora_volta_almoco, hora_saida, tempo_almoco, horas_trabalhadas, 
                 horas_extras, data_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            DatabaseManager.execute_query(query, (
                funcionario['id'], data, entrada.day, entrada.month, entrada.year,
                hora_entrada, hora_saida_almoco, hora_volta_almoco, hora_saida,
                round(tempo_almoco_horas, 2), round(horas_trabalhadas, 2), 
                round(horas_extras, 2), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            flash(f'Horas registradas para {funcionario_nome}! Total: {horas_trabalhadas:.2f}h, Extras: {horas_extras:.2f}h, Almoço: {tempo_almoco_horas:.2f}h', 'success')
            return redirect(url_for('visualizar_funcionario', nome=funcionario_nome))
            
        except sqlite3.IntegrityError:
            flash(f'Já existe registro para {funcionario_nome} na data {data}!', 'error')
    
    # Buscar funcionários para o formulário
    query = "SELECT nome FROM funcionarios WHERE ativo = 1 ORDER BY nome"
    funcionarios_list = DatabaseManager.execute_query(query, fetch_all=True)
    funcionarios = {f['nome']: f for f in funcionarios_list}
    
    return render_template('registrar_horas.html', funcionarios=funcionarios)

@app.route('/relatorio_mensal/<funcionario_nome>/<int:mes>/<int:ano>')
def relatorio_mensal(funcionario_nome, mes, ano):
    """Gera relatório mensal detalhado"""
    # Buscar funcionário
    query = "SELECT * FROM funcionarios WHERE nome = ?"
    funcionario_data = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
    
    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    # Buscar registros do mês
    query = """
        SELECT * FROM registros_ponto 
        WHERE funcionario_id = ? AND mes = ? AND ano = ?
        ORDER BY dia
    """
    registros_mes = DatabaseManager.execute_query(query, (funcionario_data['id'], mes, ano), fetch_all=True)
    
    # Calcular totais do mês
    total_mensal = calcular_total_mensal(funcionario_data['id'], mes, ano)
    
    # Calcular valores monetários
    valor_horas_normais = 0
    valor_horas_extras = 0
    
    salario_hora = funcionario_data['salario_hora']
    for registro in registros_mes:
        horas_normais = min(registro['horas_trabalhadas'], 8)
        valor_horas_normais += horas_normais * salario_hora
        valor_horas_extras += registro['horas_extras'] * salario_hora * 1.5  # 50% adicional
    
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    return render_template('relatorio_mensal.html',
                         funcionario=funcionario_nome,
                         mes=mes,
                         ano=ano,
                         mes_nome=meses_nomes[mes-1],
                         registros=registros_mes,
                         total=total_mensal,
                         funcionario_data=funcionario_data,
                         valor_horas_normais=valor_horas_normais,
                         valor_horas_extras=valor_horas_extras)

@app.route('/editar_funcionario/<nome>', methods=['GET', 'POST'])
def editar_funcionario(nome):
    """Edita dados de um funcionário"""
    # Buscar funcionário
    query = "SELECT * FROM funcionarios WHERE nome = ?"
    funcionario_data = DatabaseManager.execute_query(query, (nome,), fetch_one=True)
    
    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        novo_nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        
        try:
            query = """
                UPDATE funcionarios 
                SET nome = ?, cargo = ?, salario_mensal = ?, salario_hora = ?, horas_mensais = ?
                WHERE id = ?
            """
            DatabaseManager.execute_query(query, (
                novo_nome, cargo, salario_mensal, salario_hora, horas_mensais, funcionario_data['id']
            ))
            
            flash(f'Funcionário {novo_nome} atualizado com sucesso!', 'success')
            return redirect(url_for('visualizar_funcionario', nome=novo_nome))
            
        except sqlite3.IntegrityError:
            flash(f'Nome {novo_nome} já existe no sistema!', 'error')
    
    return render_template('editar_funcionario.html', funcionario=funcionario_data)

@app.route('/editar_registro/<int:registro_id>', methods=['GET', 'POST'])
def editar_registro(registro_id):
    """Edita um registro de ponto"""
    # Buscar registro
    query = """
        SELECT r.*, f.nome as funcionario_nome 
        FROM registros_ponto r 
        JOIN funcionarios f ON r.funcionario_id = f.id 
        WHERE r.id = ?
    """
    registro = DatabaseManager.execute_query(query, (registro_id,), fetch_one=True)
    
    if not registro:
        flash('Registro não encontrado!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        hora_entrada = request.form['hora_entrada']
        hora_saida_almoco = request.form['hora_saida_almoco']
        hora_volta_almoco = request.form['hora_volta_almoco']
        hora_saida = request.form['hora_saida']
        
        data = registro['data']
        
        # Recalcular horas
        entrada = datetime.strptime(f"{data} {hora_entrada}", "%Y-%m-%d %H:%M")
        saida_almoco = datetime.strptime(f"{data} {hora_saida_almoco}", "%Y-%m-%d %H:%M")
        volta_almoco = datetime.strptime(f"{data} {hora_volta_almoco}", "%Y-%m-%d %H:%M")
        saida = datetime.strptime(f"{data} {hora_saida}", "%Y-%m-%d %H:%M")
        
        periodo_manha = saida_almoco - entrada
        periodo_tarde = saida - volta_almoco
        
        horas_manha = periodo_manha.total_seconds() / 3600
        horas_tarde = periodo_tarde.total_seconds() / 3600
        horas_trabalhadas = horas_manha + horas_tarde
        
        tempo_almoco = volta_almoco - saida_almoco
        tempo_almoco_horas = tempo_almoco.total_seconds() / 3600
        
        horas_extras = calcular_horas_extras(horas_trabalhadas)
        
        # Atualizar registro
        query = """
            UPDATE registros_ponto 
            SET hora_entrada = ?, hora_saida_almoco = ?, hora_volta_almoco = ?, hora_saida = ?,
                tempo_almoco = ?, horas_trabalhadas = ?, horas_extras = ?, data_edicao = ?
            WHERE id = ?
        """
        DatabaseManager.execute_query(query, (
            hora_entrada, hora_saida_almoco, hora_volta_almoco, hora_saida,
            round(tempo_almoco_horas, 2), round(horas_trabalhadas, 2), round(horas_extras, 2),
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), registro_id
        ))
        
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('visualizar_funcionario', nome=registro['funcionario_nome']))
    
    return render_template('editar_registro.html', registro=registro)

@app.route('/excluir_registro/<int:registro_id>', methods=['POST'])
def excluir_registro(registro_id):
    """Exclui um registro de ponto"""
    # Buscar registro para obter nome do funcionário
    query = """
        SELECT f.nome as funcionario_nome 
        FROM registros_ponto r 
        JOIN funcionarios f ON r.funcionario_id = f.id 
        WHERE r.id = ?
    """
    registro = DatabaseManager.execute_query(query, (registro_id,), fetch_one=True)
    
    if registro:
        # Excluir registro
        query = "DELETE FROM registros_ponto WHERE id = ?"
        DatabaseManager.execute_query(query, (registro_id,))
        
        flash('Registro excluído com sucesso!', 'success')
        return redirect(url_for('visualizar_funcionario', nome=registro['funcionario_nome']))
    
    flash('Registro não encontrado!', 'error')
    return redirect(url_for('index'))

if __name__ == '__main__':
    # Verificar se o banco existe
    if not os.path.exists(DB_FILE):
        print("⚠️  Banco SQLite não encontrado!")
        print("   Execute: python migrar_para_sqlite.py")
        exit(1)
    
    print("🗄️  Usando banco SQLite: " + DB_FILE)
    app.run(debug=True, host='0.0.0.0', port=5000)
