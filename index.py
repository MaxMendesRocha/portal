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
    # Usar round() em vez de int() para arredondar corretamente os minutos
    minutos = round((horas_decimais - horas) * 60)
    
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

# Registrar filtro personalizado
app.jinja_env.filters['horas_hm'] = horas_para_hm

def calcular_periodo_fechamento(data_referencia=None):
    """
    Calcula o período de fechamento (dia 26 de um mês até dia 25 do mês seguinte)
    
    Args:
        data_referencia: data de referência (datetime.date). Se None, usa data atual
    
    Returns:
        tuple: (data_inicio, data_fim, mes_fechamento, ano_fechamento)
    """
    from datetime import date, timedelta
    
    if data_referencia is None:
        data_referencia = date.today()
    
    # Se estamos do dia 1 ao 25, o período atual começou no dia 26 do mês anterior
    if data_referencia.day <= 25:
        # Período atual: 26 do mês anterior até 25 do mês atual
        if data_referencia.month == 1:
            # Janeiro: período começou em 26 de dezembro do ano anterior
            data_inicio = date(data_referencia.year - 1, 12, 26)
        else:
            # Outros meses: período começou em 26 do mês anterior
            data_inicio = date(data_referencia.year, data_referencia.month - 1, 26)
        
        data_fim = date(data_referencia.year, data_referencia.month, 25)
        mes_fechamento = data_referencia.month
        ano_fechamento = data_referencia.year
    else:
        # Se estamos do dia 26 em diante, o período atual vai até o dia 25 do mês seguinte
        data_inicio = date(data_referencia.year, data_referencia.month, 26)
        
        if data_referencia.month == 12:
            # Dezembro: período vai até 25 de janeiro do ano seguinte
            data_fim = date(data_referencia.year + 1, 1, 25)
            mes_fechamento = 1
            ano_fechamento = data_referencia.year + 1
        else:
            # Outros meses: período vai até 25 do mês seguinte
            data_fim = date(data_referencia.year, data_referencia.month + 1, 25)
            mes_fechamento = data_referencia.month + 1
            ano_fechamento = data_referencia.year
    
    return data_inicio, data_fim, mes_fechamento, ano_fechamento

def obter_mes_fechamento_de_data(data):
    """
    Retorna o mês e ano de fechamento para uma data específica
    
    Args:
        data: string no formato 'YYYY-MM-DD' ou datetime.date
    
    Returns:
        tuple: (mes_fechamento, ano_fechamento)
    """
    from datetime import datetime, date
    
    if isinstance(data, str):
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
    elif isinstance(data, date):
        data_obj = data
    else:
        data_obj = data.date()
    
    _, _, mes_fechamento, ano_fechamento = calcular_periodo_fechamento(data_obj)
    return mes_fechamento, ano_fechamento

def calcular_horas_extras(horas_trabalhadas, horas_normais=8):
    """Calcula horas extras baseado nas horas trabalhadas no dia"""
    if horas_trabalhadas > horas_normais:
        return horas_trabalhadas - horas_normais
    return 0

def calcular_total_mensal_fechamento(funcionario_id, mes_fechamento, ano_fechamento):
    """
    Calcula o total de horas trabalhadas e extras no período de fechamento
    (do dia 26 do mês anterior até o dia 25 do mês de fechamento)
    """
    # Calcular as datas do período de fechamento
    if mes_fechamento == 1:
        data_inicio = f"{ano_fechamento - 1}-12-26"
        data_fim = f"{ano_fechamento}-01-25"
    else:
        data_inicio = f"{ano_fechamento}-{mes_fechamento-1:02d}-26"
        data_fim = f"{ano_fechamento}-{mes_fechamento:02d}-25"
    
    query = """
        SELECT 
            SUM(horas_trabalhadas) as total_horas,
            SUM(horas_extras) as total_extras,
            COUNT(*) as dias_trabalhados
        FROM registros_ponto 
        WHERE funcionario_id = ? AND data >= ? AND data <= ?
    """
    result = DatabaseManager.execute_query(query, (funcionario_id, data_inicio, data_fim), fetch_one=True)
    
    if result:
        return {
            'total_horas': result['total_horas'] or 0,
            'total_extras': result['total_extras'] or 0,
            'dias_trabalhados': result['dias_trabalhados'] or 0
        }
    return {
        'total_horas': 0,
        'total_extras': 0,
        'dias_trabalhados': 0
    }

def calcular_total_mensal(funcionario_id, mes, ano):
    """Calcula o total de horas trabalhadas e extras no mês (função original mantida para compatibilidade)"""
    query = """
        SELECT 
            SUM(horas_trabalhadas) as total_horas,
            SUM(horas_extras) as total_extras,
            COUNT(*) as dias_trabalhados
        FROM registros_ponto 
        WHERE funcionario_id = ? AND mes = ? AND ano = ?
    """
    result = DatabaseManager.execute_query(query, (funcionario_id, mes, ano), fetch_one=True)
    
    if result:
        return {
            'total_horas': result['total_horas'] or 0,
            'total_extras': result['total_extras'] or 0,
            'dias_trabalhados': result['dias_trabalhados'] or 0
        }
    return {
        'total_horas': 0,
        'total_extras': 0,
        'dias_trabalhados': 0
    }

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    """Página inicial com paginação"""
    per_page = 6  # 6 funcionários por página
    offset = (page - 1) * per_page
    
    # Contar total de funcionários ativos
    count_query = "SELECT COUNT(*) as total FROM funcionarios WHERE ativo = 1"
    total_result = DatabaseManager.execute_query(count_query, fetch_one=True)
    total_funcionarios = total_result['total'] if total_result else 0
    
    # Buscar funcionários com limit e offset
    query = "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome LIMIT ? OFFSET ?"
    funcionarios_list = DatabaseManager.execute_query(query, (per_page, offset), fetch_all=True)
    
    # Converter lista para dicionário no formato esperado pelo template
    funcionarios = {f['nome']: f for f in funcionarios_list}
    
    # Calcular informações de paginação
    total_pages = (total_funcionarios + per_page - 1) // per_page  # Ceiling division
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_funcionarios,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page
    }
    
    return render_template('index.html', funcionarios=funcionarios, pagination=pagination_info)

@app.route('/relatorios')
@app.route('/relatorios/page/<int:page>')
def relatorios(page=1):
    """Página de relatórios gerais com paginação"""
    per_page = 6  # 6 funcionários por página
    offset = (page - 1) * per_page
    
    # Contar total de funcionários ativos
    count_query = "SELECT COUNT(*) as total FROM funcionarios WHERE ativo = 1"
    total_result = DatabaseManager.execute_query(count_query, fetch_one=True)
    total_funcionarios = total_result['total'] if total_result else 0
    
    # Buscar funcionários com limit e offset
    query = "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome LIMIT ? OFFSET ?"
    funcionarios_list = DatabaseManager.execute_query(query, (per_page, offset), fetch_all=True)
    
    # Buscar dados resumidos para cada funcionário
    relatorios_data = []
    for funcionario in funcionarios_list:
        # Total de registros
        query_total = "SELECT COUNT(*) as total FROM registros_ponto WHERE funcionario_id = ?"
        total_registros = DatabaseManager.execute_query(query_total, (funcionario['id'],), fetch_one=True)
        
        # Últimos períodos de fechamento (26 a 25)
        query_meses = """
            SELECT DISTINCT data
            FROM registros_ponto 
            WHERE funcionario_id = ? 
            ORDER BY data DESC 
            LIMIT 50
        """
        registros_recentes = DatabaseManager.execute_query(query_meses, (funcionario['id'],), fetch_all=True)
        
        # Calcular períodos únicos de fechamento
        periodos_fechamento = set()
        for registro in registros_recentes:
            data_registro = datetime.strptime(registro['data'], '%Y-%m-%d').date()
            mes_fechamento, ano_fechamento = obter_mes_fechamento_de_data(data_registro)
            periodos_fechamento.add((ano_fechamento, mes_fechamento))
        
        # Converter para lista ordenada e pegar os 6 mais recentes
        periodos_ordenados = sorted(list(periodos_fechamento), reverse=True)[:6]
        
        # Formatar períodos para exibição
        meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                       'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
        meses_trabalhados = []
        for ano, mes in periodos_ordenados:
            meses_trabalhados.append({
                'mes_ano': f"{ano}-{mes:02d}",
                'ano': str(ano),
                'mes': str(mes),
                'nome': meses_nomes[mes-1]
            })
        
        relatorios_data.append({
            'funcionario': funcionario,
            'total_registros': total_registros['total'] if total_registros else 0,
            'meses_trabalhados': meses_trabalhados
        })
    
    # Calcular informações de paginação
    total_pages = (total_funcionarios + per_page - 1) // per_page  # Ceiling division
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_funcionarios,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page
    }
    
    return render_template('relatorios.html', relatorios_data=relatorios_data, pagination=pagination_info)

@app.route('/funcionario/<nome>')
@app.route('/funcionario/<nome>/page/<int:page>')
def visualizar_funcionario(nome, page=1):
    """Visualiza os dados de um funcionário específico com paginação"""
    # Buscar funcionário
    query = "SELECT * FROM funcionarios WHERE nome = ? AND ativo = 1"
    funcionario_data = DatabaseManager.execute_query(query, (nome,), fetch_one=True)
    
    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    # Paginação para registros
    per_page = 10  # 10 registros por página
    offset = (page - 1) * per_page
    
    # Contar total de registros
    count_query = "SELECT COUNT(*) as total FROM registros_ponto WHERE funcionario_id = ?"
    total_result = DatabaseManager.execute_query(count_query, (funcionario_data['id'],), fetch_one=True)
    total_registros = total_result['total'] if total_result else 0
    
    # Buscar registros com paginação
    query = """
        SELECT * FROM registros_ponto 
        WHERE funcionario_id = ? 
        ORDER BY ano DESC, mes DESC, dia DESC
        LIMIT ? OFFSET ?
    """
    registros = DatabaseManager.execute_query(query, (funcionario_data['id'], per_page, offset), fetch_all=True)
    
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
    
    # Calcular informações de paginação
    total_pages = (total_registros + per_page - 1) // per_page  # Ceiling division
    has_prev = page > 1
    has_next = page < total_pages
    prev_page = page - 1 if has_prev else None
    next_page = page + 1 if has_next else None
    
    pagination_info = {
        'page': page,
        'per_page': per_page,
        'total': total_registros,
        'total_pages': total_pages,
        'has_prev': has_prev,
        'has_next': has_next,
        'prev_page': prev_page,
        'next_page': next_page
    }
    
    return render_template('funcionario.html', 
                         nome=nome, 
                         registros=registros, 
                         totais_mensais=totais_mensais,
                         funcionario_data=funcionario_data,
                         pagination=pagination_info)

@app.route('/adicionar_funcionario', methods=['GET', 'POST'])
def adicionar_funcionario():
    """Adiciona um novo funcionário"""
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        desconto = float(request.form.get('desconto', 0.00))
        
        # Calcular valor da hora baseado no salário mensal
        horas_mensais = 200
        salario_hora = salario_mensal / horas_mensais
        
        try:
            query = """
                INSERT INTO funcionarios 
                (nome, cargo, salario_mensal, salario_hora, horas_mensais, desconto, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """
            DatabaseManager.execute_query(query, (
                nome, cargo, salario_mensal, salario_hora, horas_mensais, desconto,
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
        
        # Calcular horas extras (manter precisão máxima antes do arredondamento final)
        horas_extras = calcular_horas_extras(horas_trabalhadas)
        
        try:
            # Inserir registro (arredondar apenas no final para manter precisão)
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
                round(tempo_almoco_horas, 4), round(horas_trabalhadas, 4), 
                round(horas_extras, 4), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            
            flash(f'Horas registradas para {funcionario_nome}! Total: {horas_trabalhadas:.2f}h, Extras: {horas_extras:.2f}h, Almoço: {tempo_almoco_horas:.2f}h', 'success')
            return redirect(url_for('visualizar_funcionario', nome=funcionario_nome))
            
        except sqlite3.IntegrityError:
            flash(f'Já existe registro para {funcionario_nome} na data {data}!', 'error')
    
    # Buscar funcionários para o formulário
    query = "SELECT nome FROM funcionarios WHERE ativo = 1 ORDER BY nome"
    funcionarios_list = DatabaseManager.execute_query(query, fetch_all=True)
    funcionarios = {f['nome']: {'nome': f['nome']} for f in funcionarios_list}
    
    return render_template('registrar_horas.html', funcionarios=funcionarios)

@app.route('/relatorio_mensal/<funcionario_nome>/<int:mes>/<int:ano>')
def relatorio_mensal(funcionario_nome, mes, ano):
    """Gera relatório mensal detalhado usando período de fechamento customizado (26 a 25)"""
    # Buscar funcionário
    query = "SELECT * FROM funcionarios WHERE nome = ?"
    funcionario_data = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
    
    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    # Calcular período de fechamento (26 do mês anterior até 25 do mês atual)
    from datetime import date
    data_referencia = date(ano, mes, 25)  # Usar o dia 25 do mês solicitado
    data_inicio, data_fim, _, _ = calcular_periodo_fechamento(data_referencia)
    
    # Buscar registros do período de fechamento
    query = """
        SELECT * FROM registros_ponto 
        WHERE funcionario_id = ? AND data >= ? AND data <= ?
        ORDER BY data
    """
    registros_mes = DatabaseManager.execute_query(query, (funcionario_data['id'], data_inicio.strftime('%Y-%m-%d'), data_fim.strftime('%Y-%m-%d')), fetch_all=True)
    
    # Calcular totais usando a nova função de fechamento
    total_mensal = calcular_total_mensal_fechamento(funcionario_data['id'], mes, ano)
    
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
    
    # Informações adicionais sobre o período
    periodo_info = {
        'data_inicio': data_inicio.strftime('%d/%m/%Y'),
        'data_fim': data_fim.strftime('%d/%m/%Y'),
        'descricao': f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    }
    
    return render_template('relatorio_mensal.html',
                         funcionario=funcionario_nome,
                         mes=mes,
                         ano=ano,
                         mes_nome=meses_nomes[mes-1],
                         registros=registros_mes,
                         total=total_mensal,
                         funcionario_data=funcionario_data,
                         valor_horas_normais=valor_horas_normais,
                         valor_horas_extras=valor_horas_extras,
                         periodo=periodo_info)

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
        desconto = float(request.form.get('desconto', 0.00))
        
        horas_mensais = 200
        salario_hora = salario_mensal / horas_mensais
        
        try:
            query = """
                UPDATE funcionarios 
                SET nome = ?, cargo = ?, salario_mensal = ?, salario_hora = ?, horas_mensais = ?, desconto = ?
                WHERE id = ?
            """
            DatabaseManager.execute_query(query, (
                novo_nome, cargo, salario_mensal, salario_hora, horas_mensais, desconto, funcionario_data['id']
            ))
            
            flash(f'Funcionário {novo_nome} atualizado com sucesso!', 'success')
            return redirect(url_for('visualizar_funcionario', nome=novo_nome))
            
        except sqlite3.IntegrityError:
            flash(f'Nome {novo_nome} já existe no sistema!', 'error')
    
    return render_template('editar_funcionario.html', funcionario_data=funcionario_data)

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
    
    # Buscar funcionários para o formulário
    query_funcionarios = "SELECT nome FROM funcionarios WHERE ativo = 1 ORDER BY nome"
    funcionarios_list = DatabaseManager.execute_query(query_funcionarios, fetch_all=True)
    funcionarios = {f['nome']: {'nome': f['nome']} for f in funcionarios_list}
    
    return render_template('editar_registro.html', registro=registro, funcionarios=funcionarios, registro_id=registro_id)

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

@app.route('/controle_financeiro')
def controle_financeiro():
    """Página de controle financeiro - versão com dados reais"""
    try:
        # Buscar resumo do mês atual
        data_atual = datetime.now()
        inicio_mes = data_atual.replace(day=1).strftime('%Y-%m-%d')
        
        # Query para gastos do mês
        query_resumo = """
            SELECT SUM(valor) as gastos_mes, COUNT(*) as num_transacoes
            FROM gastos_domesticos 
            WHERE data_gasto >= ?
        """
        resultado = DatabaseManager.execute_query(query_resumo, (inicio_mes,), fetch_one=True)
        
        gastos_mes = resultado['gastos_mes'] if resultado and resultado['gastos_mes'] else 0
        num_transacoes = resultado['num_transacoes'] if resultado else 0
        
        # Orçamento fictício para demonstração (pode ser configurável no futuro)
        orcamento_mensal = 5000.00
        orcamento_restante = orcamento_mensal - gastos_mes
        
        # Query para categorias do mês
        query_categorias = """
            SELECT categoria, SUM(valor) as total
            FROM gastos_domesticos 
            WHERE data_gasto >= ?
            GROUP BY categoria
        """
        categorias_db = DatabaseManager.execute_query(query_categorias, (inicio_mes,), fetch_all=True)
        
        # Mapear ícones por categoria
        icones_categoria = {
            'Alimentação': 'shopping-cart',
            'Moradia': 'home',
            'Transporte': 'car',
            'Saúde': 'heartbeat',
            'Lazer': 'gamepad',
            'Outros': 'ellipsis-h'
        }
        
        # Preparar categorias para exibição
        categorias_todas = ['Alimentação', 'Moradia', 'Transporte', 'Saúde', 'Lazer', 'Outros']
        categorias_resumo = []
        
        for categoria in categorias_todas:
            total = 0
            for cat_db in categorias_db:
                if cat_db['categoria'] == categoria:
                    total = cat_db['total']
                    break
            
            categorias_resumo.append({
                'nome': categoria,
                'total': total,
                'icon': icones_categoria.get(categoria, 'circle')
            })
        
        resumo = {
            'gastos_mes': gastos_mes,
            'orcamento_restante': orcamento_restante,
            'num_transacoes': num_transacoes,
            'categorias': categorias_resumo
        }
        
        return render_template('controle_financeiro.html', resumo=resumo)
        
    except Exception as e:
        flash(f'Erro ao carregar dados financeiros: {str(e)}', 'error')
        # Fallback para dados vazios em caso de erro
        resumo = {
            'gastos_mes': 0.00,
            'orcamento_restante': 0.00,
            'num_transacoes': 0,
            'categorias': [
                {'nome': 'Alimentação', 'total': 0.00, 'icon': 'shopping-cart'},
                {'nome': 'Moradia', 'total': 0.00, 'icon': 'home'},
                {'nome': 'Transporte', 'total': 0.00, 'icon': 'car'},
                {'nome': 'Saúde', 'total': 0.00, 'icon': 'heartbeat'},
                {'nome': 'Lazer', 'total': 0.00, 'icon': 'gamepad'},
                {'nome': 'Outros', 'total': 0.00, 'icon': 'ellipsis-h'},
            ]
        }
        return render_template('controle_financeiro.html', resumo=resumo)

@app.route('/gastos/adicionar', methods=['GET', 'POST'])
def adicionar_gasto():
    """Adicionar novo gasto doméstico"""
    if request.method == 'POST':
        try:
            # Obter dados do formulário
            descricao = request.form.get('descricao')
            categoria = request.form.get('categoria')
            valor = float(request.form.get('valor'))
            data_gasto = request.form.get('data')
            forma_pagamento = request.form.get('forma_pagamento')
            observacoes = request.form.get('observacoes') or ''
            
            # Salvar no banco de dados
            query = """
                INSERT INTO gastos_domesticos 
                (descricao, categoria, valor, data_gasto, forma_pagamento, observacoes)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            DatabaseManager.execute_query(
                query, 
                (descricao, categoria, valor, data_gasto, forma_pagamento, observacoes)
            )
            
            flash(f'Gasto "{descricao}" de R$ {valor:.2f} adicionado com sucesso!', 'success')
            return redirect(url_for('controle_financeiro'))
            
        except Exception as e:
            flash(f'Erro ao adicionar gasto: {str(e)}', 'error')
            return redirect(url_for('adicionar_gasto'))
    
    # Retorna formulário para adicionar gasto
    categorias = ['Alimentação', 'Moradia', 'Transporte', 'Saúde', 'Lazer', 'Outros']
    return render_template('adicionar_gasto.html', categorias=categorias)

@app.route('/gastos/excluir/<int:gasto_id>', methods=['POST'])
def excluir_gasto(gasto_id):
    """Excluir um gasto específico"""
    try:
        # Primeiro, buscar o gasto para mostrar na mensagem
        query_buscar = "SELECT descricao, valor FROM gastos_domesticos WHERE id = ?"
        gasto_info = DatabaseManager.execute_query(query_buscar, (gasto_id,), fetch_one=True)
        
        if not gasto_info:
            flash('Gasto não encontrado!', 'error')
            return redirect(url_for('listar_gastos'))
        
        # Excluir o gasto
        query_excluir = "DELETE FROM gastos_domesticos WHERE id = ?"
        DatabaseManager.execute_query(query_excluir, (gasto_id,))
        
        flash(f'Gasto "{gasto_info["descricao"]}" de R$ {gasto_info["valor"]:.2f} excluído com sucesso!', 'success')
        return redirect(url_for('listar_gastos'))
        
    except Exception as e:
        flash(f'Erro ao excluir gasto: {str(e)}', 'error')
        return redirect(url_for('listar_gastos'))

@app.route('/gastos/listar')
def listar_gastos():
    """Listar todos os gastos"""
    try:
        # Buscar gastos no banco ordenados por data (mais recentes primeiro)
        query = """
            SELECT id, descricao, categoria, valor, data_gasto, forma_pagamento, observacoes, data_criacao
            FROM gastos_domesticos 
            ORDER BY data_gasto DESC, data_criacao DESC
        """
        gastos_db = DatabaseManager.execute_query(query, fetch_all=True)
        
        # Formatar dados para o template
        gastos = []
        total_gastos = 0
        
        for gasto in gastos_db:
            # Formatar data para exibição
            data_obj = datetime.strptime(gasto['data_gasto'], '%Y-%m-%d')
            data_formatada = data_obj.strftime('%d/%m/%Y')
            
            gasto_formatado = {
                'id': gasto['id'],
                'descricao': gasto['descricao'],
                'categoria': gasto['categoria'],
                'valor': gasto['valor'],
                'data_formatada': data_formatada,
                'forma_pagamento': gasto['forma_pagamento'],
                'observacoes': gasto['observacoes']
            }
            gastos.append(gasto_formatado)
            total_gastos += gasto['valor']
        
        return render_template('listar_gastos.html', gastos=gastos, total_gastos=total_gastos)
        
    except Exception as e:
        flash(f'Erro ao carregar gastos: {str(e)}', 'error')
        return render_template('listar_gastos.html', gastos=[], total_gastos=0)

@app.route('/gastos/relatorio')
def relatorio_gastos():
    """Relatório de gastos por categoria"""
    try:
        # Buscar gastos do mês atual
        data_atual = datetime.now()
        inicio_mes = data_atual.replace(day=1).strftime('%Y-%m-%d')
        
        # Query para gastos por categoria do mês atual
        query = """
            SELECT categoria, SUM(valor) as total, COUNT(*) as quantidade
            FROM gastos_domesticos 
            WHERE data_gasto >= ?
            GROUP BY categoria
            ORDER BY total DESC
        """
        gastos_categoria = DatabaseManager.execute_query(query, (inicio_mes,), fetch_all=True)
        
        # Query para total geral do mês
        query_total = """
            SELECT SUM(valor) as total_geral, COUNT(*) as total_transacoes
            FROM gastos_domesticos 
            WHERE data_gasto >= ?
        """
        total_resultado = DatabaseManager.execute_query(query_total, (inicio_mes,), fetch_one=True)
        
        total_geral = total_resultado['total_geral'] if total_resultado and total_resultado['total_geral'] else 0
        total_transacoes = total_resultado['total_transacoes'] if total_resultado else 0
        
        # Mapear ícones e cores por categoria
        icones_categoria = {
            'Alimentação': {'icon': 'shopping-cart', 'cor': 'primary'},
            'Moradia': {'icon': 'home', 'cor': 'success'},
            'Transporte': {'icon': 'car', 'cor': 'info'},
            'Saúde': {'icon': 'heartbeat', 'cor': 'danger'},
            'Lazer': {'icon': 'gamepad', 'cor': 'warning'},
            'Outros': {'icon': 'ellipsis-h', 'cor': 'secondary'}
        }
        
        # Formatar dados para o template
        gastos_formatados = []
        for categoria in gastos_categoria:
            percentual = (categoria['total'] / total_geral * 100) if total_geral > 0 else 0
            categoria_info = icones_categoria.get(categoria['categoria'], {'icon': 'circle', 'cor': 'secondary'})
            
            gastos_formatados.append({
                'nome': categoria['categoria'],
                'total': categoria['total'],
                'quantidade': categoria['quantidade'],
                'percentual': percentual,
                'icon': categoria_info['icon'],
                'cor': categoria_info['cor']
            })
        
        dados_relatorio = {
            'gastos_por_categoria': gastos_formatados,
            'total_geral': total_geral,
            'total_transacoes': total_transacoes,
            'mes_referencia': data_atual.strftime('%B de %Y')
        }
        
        return render_template('relatorio_gastos.html', dados=dados_relatorio)
        
    except Exception as e:
        flash(f'Erro ao gerar relatório: {str(e)}', 'error')
        dados_relatorio = {
            'gastos_por_categoria': [],
            'total_geral': 0,
            'total_transacoes': 0,
            'mes_referencia': datetime.now().strftime('%B de %Y')
        }
        return render_template('relatorio_gastos.html', dados=dados_relatorio)

if __name__ == '__main__':
    # Verificar se o banco existe
    if not os.path.exists(DB_FILE):
        print("⚠️  Banco SQLite não encontrado!")
        print("   Execute: python migrar_para_sqlite.py")
        exit(1)
    
    print("🗄️  Usando banco SQLite: " + DB_FILE)
    app.run(debug=True, host='0.0.0.0', port=8000)
