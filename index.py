from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Arquivo do banco SQLite - em ambientes serverless use /tmp
DB_FILE = os.environ.get('DB_FILE', '/tmp/horas_trabalho.db')

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


def obter_horas_normais_esperadas(funcionario_id, data_str):
    """Retorna as horas normais esperadas para um funcionário em uma data.
    Ordem de preferência:
    - `carga_horaria` ativa e aplicável ao dia
    - `funcionarios.horas_mensais / 25` (aproximação de dias úteis no mês)
    - fallback: 8
    """
    from datetime import datetime

    try:
        # checar carga horaria específica
        query = "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1"
        carga = DatabaseManager.execute_query(query, (funcionario_id,), fetch_one=True)
        if carga:
            dias_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
            dia_tag = dias_map[data_obj.weekday()]
            dias_semana = carga['dias_semana'].split(',') if carga.get('dias_semana') else []
            if dia_tag in dias_semana:
                inicio_dt = datetime.strptime(f"{data_str} {carga['inicio']}", "%Y-%m-%d %H:%M")
                fim_dt = datetime.strptime(f"{data_str} {carga['fim']}", "%Y-%m-%d %H:%M")
                intervalo_h = (carga.get('intervalo_min') or 0) / 60.0
                return (fim_dt - inicio_dt).total_seconds() / 3600 - intervalo_h

        # fallback para horas mensais do funcionário (dividir por 25 dias úteis)
        q2 = "SELECT horas_mensais FROM funcionarios WHERE id = ?"
        f = DatabaseManager.execute_query(q2, (funcionario_id,), fetch_one=True)
        if f and f.get('horas_mensais'):
            try:
                horas_mensais = float(f['horas_mensais'])
                return horas_mensais / 25.0
            except Exception:
                pass
    except Exception:
        pass

    return 8


def is_feriado(data_obj):
    """Verifica se a data é um feriado. Procura arquivo 'feriados.json' com lista de 'YYYY-MM-DD'."""
    try:
        if not os.path.exists('feriados.json'):
            return False
        with open('feriados.json', 'r', encoding='utf-8') as f:
            feriados = json.load(f)
        # aceitar lista de strings
        data_str = data_obj.strftime('%Y-%m-%d')
        return data_str in feriados
    except Exception:
        return False

def extra_multiplier_for_date(data_input):
    """Retorna o multiplicador de adicional para a data.
    - Sábado/Domingo ou feriado: 2.0 (100% adicional)
    - Outros dias: 1.5 (50% adicional)
    Aceita `datetime.date` ou string 'YYYY-MM-DD'.
    """
    from datetime import datetime, date

    if isinstance(data_input, str):
        data_obj = datetime.strptime(data_input, '%Y-%m-%d').date()
    elif isinstance(data_input, date):
        data_obj = data_input
    else:
        data_obj = data_input.date()

    # weekday(): 0=Mon .. 6=Sun
    if data_obj.weekday() >= 5 or is_feriado(data_obj):
        return 2.0
    return 1.5

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


@app.route('/funcionario/id/<int:funcionario_id>')
@app.route('/funcionario/id/<int:funcionario_id>/page/<int:page>')
def visualizar_funcionario_por_id(funcionario_id, page=1):
    """Visualiza funcionário por ID — evita problemas de encoding em nomes na URL"""
    query = "SELECT * FROM funcionarios WHERE id = ? AND ativo = 1"
    funcionario_data = DatabaseManager.execute_query(query, (funcionario_id,), fetch_one=True)

    if not funcionario_data:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))

    # Reuse the existing view logic by calling the name-based view function directly
    return visualizar_funcionario(funcionario_data['nome'], page)

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
        hora_entrada = request.form.get('hora_entrada')
        hora_saida_almoco = request.form.get('hora_saida_almoco')
        hora_volta_almoco = request.form.get('hora_volta_almoco')
        hora_saida = request.form.get('hora_saida')
        
        # Buscar funcionário
        query = "SELECT id FROM funcionarios WHERE nome = ?"
        funcionario = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
        
        if not funcionario:
            flash('Funcionário não encontrado!', 'error')
            return redirect(url_for('registrar_horas'))
        
        # Converter para datetime e determinar se existe configuração de carga
        entrada = datetime.strptime(f"{data} {hora_entrada}", "%Y-%m-%d %H:%M")
        saida = datetime.strptime(f"{data} {hora_saida}", "%Y-%m-%d %H:%M")

        # Buscar configuração de carga horária do funcionário (se houver)
        query_carga = "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1"
        carga = DatabaseManager.execute_query(query_carga, (funcionario['id'],), fetch_one=True)

        # Determinar horas normais esperadas para o dia
        horas_normais_esperadas = 8
        carga_aplicavel = False
        if carga:
            # verificar se a data pertence aos dias configurados
            dias_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            data_obj = datetime.strptime(data, '%Y-%m-%d').date()
            dia_tag = dias_map[data_obj.weekday()]
            dias_semana = carga['dias_semana'].split(',') if carga.get('dias_semana') else []
            if dia_tag in dias_semana:
                carga_aplicavel = True
                inicio_dt = datetime.strptime(f"{data} {carga['inicio']}", "%Y-%m-%d %H:%M")
                fim_dt = datetime.strptime(f"{data} {carga['fim']}", "%Y-%m-%d %H:%M")
                intervalo_h = (carga.get('intervalo_min') or 0) / 60.0
                horas_normais_esperadas = (fim_dt - inicio_dt).total_seconds() / 3600 - intervalo_h

        # Calcular horas trabalhadas e tempo de almoço dependendo se há intervalo cadastrado
        if carga_aplicavel and (carga.get('intervalo_min') or 0) == 0:
            # Sem intervalo cadastrado: considerar apenas entrada->saída
            horas_trabalhadas = (saida - entrada).total_seconds() / 3600
            tempo_almoco_horas = 0
            # garantir valores para campos opcionais
            hora_saida_almoco = hora_saida_almoco or ''
            hora_volta_almoco = hora_volta_almoco or ''
        else:
            # Espera-se campos de almoço; se estiverem ausentes, tratar como 0
            try:
                saida_almoco = datetime.strptime(f"{data} {hora_saida_almoco}", "%Y-%m-%d %H:%M") if hora_saida_almoco else None
                volta_almoco = datetime.strptime(f"{data} {hora_volta_almoco}", "%Y-%m-%d %H:%M") if hora_volta_almoco else None
            except Exception:
                flash('Formato de horário inválido para intervalo.', 'error')
                return redirect(url_for('registrar_horas'))

            if saida_almoco and volta_almoco:
                periodo_manha = saida_almoco - entrada
                periodo_tarde = saida - volta_almoco
                horas_manha = periodo_manha.total_seconds() / 3600
                horas_tarde = periodo_tarde.total_seconds() / 3600
                horas_trabalhadas = horas_manha + horas_tarde
                tempo_almoco_horas = (volta_almoco - saida_almoco).total_seconds() / 3600
            else:
                # Falha segura: considerar entrada->saída sem desconto de almoço
                horas_trabalhadas = (saida - entrada).total_seconds() / 3600
                tempo_almoco_horas = 0

        # Calcular horas extras seguindo as regras:
        # - Se for sábado, domingo ou feriado: todas as horas são consideradas extras (100% adicional)
        # - Caso contrário: apenas o excedente sobre a carga esperada (ou 8h) é extra
        data_obj = datetime.strptime(data, '%Y-%m-%d').date()
        # Se for fim de semana ou feriado, todas as horas são extras.
        # Caso contrário, calcular extras sobre a carga esperada (ou 8h padrão).
        if data_obj.weekday() >= 5 or is_feriado(data_obj):
            horas_extras = horas_trabalhadas
        else:
            horas_extras = calcular_horas_extras(horas_trabalhadas, horas_normais_esperadas)
        
        # VALIDAÇÃO: Verificar se já existe lançamento para esta data e funcionário
        query_verificacao = """
            SELECT id, hora_entrada, hora_saida, horas_trabalhadas 
            FROM registros_ponto 
            WHERE funcionario_id = ? AND data = ?
        """
        registro_existente = DatabaseManager.execute_query(query_verificacao, (funcionario['id'], data), fetch_one=True)
        
        if registro_existente:
            flash(f'❌ ERRO: Já existe lançamento de horas para {funcionario_nome} na data {data}!', 'error')
            flash(f'📋 Registro existente: {registro_existente["hora_entrada"]} às {registro_existente["hora_saida"]} ({registro_existente["horas_trabalhadas"]:.2f}h)', 'warning')
            flash(f'💡 Para corrigir: Vá em "Funcionários" → "{funcionario_nome}" → Editar o registro da data {data}', 'info')
            return redirect(url_for('registrar_horas'))
        
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
            
            flash(f'✅ Horas registradas com sucesso para {funcionario_nome}! Total: {horas_trabalhadas:.2f}h, Extras: {horas_extras:.2f}h, Almoço: {tempo_almoco_horas:.2f}h', 'success')
            return redirect(url_for('visualizar_funcionario_por_id', funcionario_id=funcionario['id']))
            
        except sqlite3.IntegrityError:
            flash(f'❌ Erro de integridade: Já existe registro para {funcionario_nome} na data {data}!', 'error')
            return redirect(url_for('registrar_horas'))
    
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

    # Calcular valores monetários por registro, usando multiplicador correto por data
    valor_horas_normais = 0
    valor_horas_extras = 0

    salario_hora = funcionario_data.get('salario_hora') or 0
    # Ensure registros_mes is a list of dicts we can modify
    registros_preparados = []
    for registro in registros_mes:
        # Determinar multiplicador para a data (1.5 em dia útil, 2.0 em final de semana/feriado)
        mult = extra_multiplier_for_date(registro['data'])

        horas_trabalhadas_reg = float(registro.get('horas_trabalhadas') or 0)
        horas_extras_reg = float(registro.get('horas_extras') or 0)

        # Se for fim de semana/feriado (multiplicador 2.0), considerar todas as horas como adicionais
        # e não somar horas normais para evitar dupla contagem.
        if mult == 2.0:
            valor_horas_extras += horas_trabalhadas_reg * salario_hora * mult
        else:
            horas_esperadas = obter_horas_normais_esperadas(funcionario_data['id'], registro['data'])
            horas_normais = min(horas_trabalhadas_reg, horas_esperadas)
            valor_horas_normais += horas_normais * salario_hora
            # Horas extras registradas são pagas com o multiplicador apropriado (ex.: 1.5)
            valor_horas_extras += horas_extras_reg * salario_hora * mult

        # Anexar metadados para o template: percentual e multiplicador
        reg = dict(registro)
        reg['multiplier'] = mult
        reg['percentual'] = '100%' if mult == 2.0 else '50%'
        registros_preparados.append(reg)

    # Substituir registros_mes por versão preparada
    registros_mes = registros_preparados
    
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    # Informações adicionais sobre o período
    periodo_info = {
        'data_inicio': data_inicio.strftime('%d/%m/%Y'),
        'data_fim': data_fim.strftime('%d/%m/%Y'),
        'descricao': f"Período: {data_inicio.strftime('%d/%m/%Y')} a {data_fim.strftime('%d/%m/%Y')}"
    }

    # Achados automatizados sobre a lógica de cálculo de horas extras
    confirmados = [
        'Horas extras calculadas como max(0, horas_trabalhadas - horas_normais) via calcular_horas_extras()',
        'Adicional padrão: 50% em dias úteis; 100% em finais de semana/feriados via extra_multiplier_for_date()',
        'Em finais de semana/feriados todas as horas do registro são tratadas como extras (multiplicador 2.0)'
    ]

    incertos = [
        'Horas normais por dia usam valor padrão 8h — pode variar por funcionário (horas_mensais)',
        'Arredondamento de horas para 2 casas decimais pode causar pequenas diferenças de minutos',
        'Detecção de feriados depende de feriados.json — formato/ausência pode impactar o resultado',
        'Registros sem intervalo de almoço explícito podem gerar interpretação ambígua do cálculo'
    ]

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
                         periodo=periodo_info,
                         achados_confirmados=confirmados,
                         achados_incertos=incertos)

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


@app.route('/excluir_funcionario/<int:funcionario_id>', methods=['POST'])
def excluir_funcionario(funcionario_id):
    """Marca um funcionário como inativo (soft delete)."""
    # Buscar funcionário para mensagem
    query_buscar = "SELECT nome FROM funcionarios WHERE id = ? AND ativo = 1"
    funcionario = DatabaseManager.execute_query(query_buscar, (funcionario_id,), fetch_one=True)

    if not funcionario:
        flash('Funcionário não encontrado ou já excluído!', 'error')
        return redirect(url_for('index'))

    try:
        query = "UPDATE carga_horaria SET ativo = 0 WHERE id = ?"
        DatabaseManager.execute_query(query, (funcionario_id,))
        flash('Configuração removida', 'success')
        return redirect(url_for('config_carga'))
    except Exception as e:
        flash(f'Erro ao excluir funcionário: {str(e)}', 'error')
        return redirect(url_for('visualizar_funcionario', nome=funcionario['nome']))

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

@app.route('/calculo_avulso', methods=['GET', 'POST'])
def calculo_avulso():
    """Página para cálculo avulso de horas trabalhadas"""
    resultado = None
    
    if request.method == 'POST':
        funcionario_nome = request.form.get('funcionario')
        quantidade_horas = float(request.form.get('quantidade_horas', 0))
        percentual = request.form.get('percentual')  # '50' ou '100'
        
        # Buscar funcionário e valor da hora
        query = "SELECT nome, salario_hora FROM funcionarios WHERE nome = ? AND ativo = 1"
        funcionario = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
        
        if funcionario:
            valor_hora = funcionario['salario_hora']
            
            # Calcular valor baseado no percentual
            # ACRÉSCIMO sobre o valor base (hora extra)
            if percentual == '50':
                # Valor base + 50% de acréscimo
                valor_hora_calculado = valor_hora * 1.5
                tipo_calculo = '50% (hora extra)'
            else:  # 100%
                # Valor base + 100% de acréscimo (dobro)
                valor_hora_calculado = valor_hora * 2.0
                tipo_calculo = '100% (hora extra)'
            
            valor_total = quantidade_horas * valor_hora_calculado
            
            resultado = {
                'funcionario': funcionario['nome'],
                'quantidade_horas': quantidade_horas,
                'valor_hora_base': valor_hora,
                'percentual': tipo_calculo,
                'valor_hora_calculado': valor_hora_calculado,
                'valor_total': valor_total
            }
        else:
            flash('Funcionário não encontrado!', 'error')
    
    # Buscar funcionários ativos para o formulário
    query = "SELECT nome, salario_hora FROM funcionarios WHERE ativo = 1 ORDER BY nome"
    funcionarios_list = DatabaseManager.execute_query(query, fetch_all=True)
    funcionarios = {f['nome']: {'nome': f['nome'], 'valor_hora': f['salario_hora']} for f in funcionarios_list}
    
    return render_template('calculo_avulso.html', funcionarios=funcionarios, resultado=resultado)

@app.route('/api/verificar_lancamento', methods=['POST'])
def verificar_lancamento():
    """API para verificar se já existe lançamento para funcionário e data"""
    try:
        data = request.get_json()
        funcionario_nome = data.get('funcionario')
        data_registro = data.get('data')
        
        if not funcionario_nome or not data_registro:
            return jsonify({'erro': 'Funcionário e data são obrigatórios'}), 400
            
        # Buscar funcionário
        query = "SELECT id FROM funcionarios WHERE nome = ?"
        funcionario = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
        
        if not funcionario:
            return jsonify({'erro': 'Funcionário não encontrado'}), 404
            
        # Verificar se já existe lançamento
        query_verificacao = """
            SELECT id, hora_entrada, hora_saida, horas_trabalhadas, data_registro
            FROM registros_ponto 
            WHERE funcionario_id = ? AND data = ?
        """
        registro_existente = DatabaseManager.execute_query(query_verificacao, (funcionario['id'], data_registro), fetch_one=True)
        
        if registro_existente:
            return jsonify({
                'existe': True,
                'registro': {
                    'hora_entrada': registro_existente['hora_entrada'],
                    'hora_saida': registro_existente['hora_saida'],
                    'horas_trabalhadas': registro_existente['horas_trabalhadas'],
                    'data_registro': registro_existente['data_registro']
                }
            })
        else:
            return jsonify({'existe': False})
            
    except Exception as e:
        return jsonify({'erro': str(e)}), 500


@app.route('/config_carga', methods=['GET', 'POST'])
def config_carga():
    """Página para configurar carga horária de funcionários"""
    if request.method == 'POST':
        funcionario_id = request.form.get('funcionario_id')
        inicio = request.form.get('inicio')  # formato HH:MM
        fim = request.form.get('fim')
        dias = request.form.getlist('dias') or request.form.getlist('dias[]')  # lista de dias (ex: Mon,Tue,...)
        intervalo = request.form.get('intervalo') or 0

        if not funcionario_id or not inicio or not fim or not dias:
            flash('Todos os campos são obrigatórios', 'warning')
            return redirect(url_for('config_carga'))

        dias_str = ','.join(dias)
        query = """
            INSERT INTO carga_horaria (funcionario_id, inicio, fim, dias_semana, intervalo_min, ativo)
            VALUES (?, ?, ?, ?, ?, 1)
        """
        DatabaseManager.execute_query(query, (funcionario_id, inicio, fim, dias_str, int(intervalo)))
        flash('Configuração de carga horária salva', 'success')
        return redirect(url_for('config_carga'))

    # GET
    funcionarios = DatabaseManager.execute_query("SELECT id, nome FROM funcionarios WHERE ativo = 1 ORDER BY nome", fetch_all=True)
    cargas = DatabaseManager.execute_query(
        "SELECT ch.*, f.nome as funcionario_nome "
        "FROM carga_horaria ch "
        "LEFT JOIN funcionarios f ON ch.funcionario_id = f.id "
        "WHERE ch.ativo = 1 "
        "ORDER BY f.nome",
        fetch_all=True
    )
    return render_template('config_carga.html', funcionarios=funcionarios, cargas=cargas)


@app.route('/config_carga/delete/<int:carga_id>', methods=['POST'])
def config_carga_delete(carga_id):
    DatabaseManager.execute_query("UPDATE carga_horaria SET ativo = 0 WHERE id = ?", (carga_id,))
    flash('Configuração removida', 'success')
    return redirect(url_for('config_carga'))


@app.route('/api/get_carga', methods=['POST'])
def api_get_carga():
    """Retorna configuração de carga aplicável para um funcionário em uma data específica"""
    try:
        data = request.get_json()
        funcionario_nome = data.get('funcionario')
        data_str = data.get('data')
        if not funcionario_nome or not data_str:
            return jsonify({'error': 'Parâmetros ausentes'}), 400

        # Buscar funcionário
        query = "SELECT id FROM funcionarios WHERE nome = ?"
        funcionario = DatabaseManager.execute_query(query, (funcionario_nome,), fetch_one=True)
        if not funcionario:
            return jsonify({'error': 'Funcionario não encontrado'}), 404

        # Buscar carga ativa
        query2 = "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1"
        carga = DatabaseManager.execute_query(query2, (funcionario['id'],), fetch_one=True)

        if not carga:
            return jsonify({'aplicavel': False})

        # Determinar se a carga é aplicável ao dia
        from datetime import datetime
        dias_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        dia_tag = dias_map[data_obj.weekday()]
        dias_semana = carga['dias_semana'].split(',') if carga.get('dias_semana') else []
        aplicavel = dia_tag in dias_semana

        # Calcular horas esperadas
        horas_esperadas = None
        if aplicavel:
            inicio_dt = datetime.strptime(f"{data_str} {carga['inicio']}", "%Y-%m-%d %H:%M")
            fim_dt = datetime.strptime(f"{data_str} {carga['fim']}", "%Y-%m-%d %H:%M")
            intervalo_h = (carga.get('intervalo_min') or 0) / 60.0
            horas_esperadas = (fim_dt - inicio_dt).total_seconds() / 3600 - intervalo_h

        return jsonify({
            'aplicavel': aplicavel,
            'intervalo_min': carga.get('intervalo_min', 0),
            'horas_esperadas': horas_esperadas
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def initialize_carga_table():
    """Cria a tabela `carga_horaria` se não existir"""
    query = """
    CREATE TABLE IF NOT EXISTS carga_horaria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        funcionario_id INTEGER NOT NULL,
        inicio TEXT NOT NULL,
        fim TEXT NOT NULL,
        dias_semana TEXT NOT NULL,
        intervalo_min INTEGER DEFAULT 0,
        ativo INTEGER DEFAULT 1,
        FOREIGN KEY(funcionario_id) REFERENCES funcionarios(id)
    );
    """
    DatabaseManager.execute_query(query)

# Evitar operações de escrita durante o import em ambientes serverless.
# Em vez disso, inicializar o DB no primeiro request quando apropriado.
@app.before_first_request
def ensure_db():
    # Se SKIP_DB_INIT estiver definido como '1', não execute inicializações (útil durante build)
    if os.environ.get('SKIP_DB_INIT') == '1':
        return

    # Garantir que o diretório do DB exista (por exemplo /tmp)
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass

    # Criar tabelas básicas se necessário
    try:
        initialize_carga_table()
        # Aqui você pode chamar outras rotinas de migração/criação de tabela, se necessário
    except Exception:
        # Não falhar no startup por causa de problemas de criação de tabela
        pass

if __name__ == '__main__':
    # Verificar se o banco existe (modo local)
    if not os.path.exists(DB_FILE):
        print("[AVISO] Banco SQLite não encontrado!")
        print("        Execute: python migrar_para_sqlite.py")
        # Não exit here to allow local auto-creation if desired

    # Garantir que a tabela de configuração de carga horária exista em modo local
    initialize_carga_table()
    
    print("[INFO] Usando banco SQLite: " + DB_FILE)
    app.run(debug=True, host='0.0.0.0', port=5001)
