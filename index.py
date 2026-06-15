from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Arquivo do banco SQLite
DB_FILE = os.environ.get('DB_FILE', 'horas_trabalho.db')

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
    minutos = round((horas_decimais - horas) * 60)
    
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
    from datetime import date
    
    if data_referencia is None:
        data_referencia = date.today()
    
    if data_referencia.day <= 25:
        if data_referencia.month == 1:
            data_inicio = date(data_referencia.year - 1, 12, 26)
        else:
            data_inicio = date(data_referencia.year, data_referencia.month - 1, 26)
        
        data_fim = date(data_referencia.year, data_referencia.month, 25)
        mes_fechamento = data_referencia.month
        ano_fechamento = data_referencia.year
    else:
        data_inicio = date(data_referencia.year, data_referencia.month, 26)
        
        if data_referencia.month == 12:
            data_fim = date(data_referencia.year + 1, 1, 25)
            mes_fechamento = 1
            ano_fechamento = data_referencia.year + 1
        else:
            data_fim = date(data_referencia.year, data_referencia.month + 1, 25)
            mes_fechamento = data_referencia.month + 1
            ano_fechamento = data_referencia.year
    
    return data_inicio, data_fim, mes_fechamento, ano_fechamento

def obter_mes_fechamento_de_data(data):
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
    if horas_trabalhadas > horas_normais:
        return horas_trabalhadas - horas_normais
    return 0


def obter_horas_normais_esperadas(funcionario_id, data_str):
    from datetime import datetime

    try:
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
    try:
        if not os.path.exists('feriados.json'):
            return False
        with open('feriados.json', 'r', encoding='utf-8') as f:
            feriados = json.load(f)
        data_str = data_obj.strftime('%Y-%m-%d')
        return data_str in feriados
    except Exception:
        return False

def extra_multiplier_for_date(data_input):
    from datetime import datetime, date

    if isinstance(data_input, str):
        data_obj = datetime.strptime(data_input, '%Y-%m-%d').date()
    elif isinstance(data_input, date):
        data_obj = data_input
    else:
        data_obj = data_input.date()

    if data_obj.weekday() >= 5 or is_feriado(data_obj):
        return 2.0
    return 1.5

def calcular_total_mensal_fechamento(funcionario_id, mes_fechamento, ano_fechamento):
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
    per_page = 6
    offset = (page - 1) * per_page
    
    count_query = "SELECT COUNT(*) as total FROM funcionarios WHERE ativo = 1"
    total_result = DatabaseManager.execute_query(count_query, fetch_one=True)
    total_funcionarios = total_result['total'] if total_result else 0
    
    query = "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome LIMIT ? OFFSET ?"
    funcionarios_list = DatabaseManager.execute_query(query, (per_page, offset), fetch_all=True)
    
    funcionarios = {f['nome']: f for f in funcionarios_list}
    
    total_pages = (total_funcionarios + per_page - 1) // per_page
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

# ... rest of the routes unchanged (omitted here for brevity) ...


def initialize_carga_table():
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


# Inicialização segura do DB em ambientes serverless:
# - Evita operações de escrita durante o import
# - Executa a inicialização apenas no primeiro request da instância
@app.before_request
def ensure_db_on_first_request():
    # Permite pular inicialização via env var (útil durante build)
    if os.environ.get('SKIP_DB_INIT') == '1':
        return

    # Executar apenas uma vez por processo/instância
    if getattr(app, '_db_initialized', False):
        return

    # Garantir diretório do DB (se DB_FILE tiver caminho)
    db_dir = os.path.dirname(DB_FILE)
    if db_dir and not os.path.exists(db_dir):
        try:
            os.makedirs(db_dir, exist_ok=True)
        except Exception:
            pass

    # Rodar inicializações necessárias sem quebrar o request
    try:
        initialize_carga_table()
        # adicionar outras inicializações necessárias aqui, se houver
    except Exception:
        # não interromper o request por erro de inicialização
        pass
    finally:
        app._db_initialized = True


if __name__ == '__main__':
    # Verificar se o banco existe
    if not os.path.exists(DB_FILE):
        print("[AVISO] Banco SQLite não encontrado!")
        print("        Execute: python migrar_para_sqlite.py")
        exit(1)

    initialize_carga_table()
    
    print("[INFO] Usando banco SQLite: " + DB_FILE)
    app.run(debug=True, host='0.0.0.0', port=5001)
