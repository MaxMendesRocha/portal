from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, date
import sqlite3
import os
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sua_chave_secreta_aqui')

DB_FILE = os.environ.get('DB_FILE', 'horas_trabalho.db')


class DatabaseManager:
    @staticmethod
    def get_connection():
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn

    @staticmethod
    def execute_query(query, params=None, fetch_one=False, fetch_all=False):
        conn = DatabaseManager.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            if fetch_all:
                results = cursor.fetchall()
                return [dict(row) for row in results]
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()


def horas_para_hm(horas_decimais):
    if not horas_decimais:
        return "0h 0min"
    horas = int(horas_decimais)
    minutos = round((horas_decimais - horas) * 60)
    if minutos >= 60:
        horas += 1
        minutos = 0
    if horas > 0 and minutos > 0:
        return f"{horas}h {minutos}min"
    if horas > 0:
        return f"{horas}h"
    return f"{minutos}min"


app.jinja_env.filters['horas_hm'] = horas_para_hm


def calcular_periodo_fechamento(data_referencia=None):
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


def calcular_horas_extras(horas_trabalhadas, horas_normais=8):
    return max(0, horas_trabalhadas - horas_normais)


def is_feriado(data_obj):
    try:
        if not os.path.exists('feriados.json'):
            return False
        with open('feriados.json', 'r', encoding='utf-8') as file:
            feriados = json.load(file)
        return data_obj.strftime('%Y-%m-%d') in feriados
    except Exception:
        return False


def extra_multiplier_for_date(data_input):
    # Mantém compatibilidade: retorna multiplicador (1.5 = +50%, 2.0 = +100%)
    if isinstance(data_input, str):
        data_obj = datetime.strptime(data_input, '%Y-%m-%d').date()
    elif isinstance(data_input, date):
        data_obj = data_input
    else:
        data_obj = data_input.date()
    percent = extra_percentage_for_date(data_obj)
    return 1.0 + (percent / 100.0)


def extra_percentage_for_date(data_input):
    """Retorna o percentual de acréscimo para hora extra na data informada.

    - 100 para finais de semana ou feriados
    - 50 para dias de semana normais
    """
    if isinstance(data_input, str):
        data_obj = datetime.strptime(data_input, '%Y-%m-%d').date()
    elif isinstance(data_input, date):
        data_obj = data_input
    else:
        data_obj = data_input.date()
    try:
        if data_obj.weekday() >= 5 or is_feriado(data_obj):
            return 100
    except Exception:
        pass
    return 50


def obter_horas_normais_esperadas(funcionario_id, data_str):
    try:
        carga = DatabaseManager.execute_query(
            "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1",
            (funcionario_id,),
            fetch_one=True
        )
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

        funcionario = DatabaseManager.execute_query(
            "SELECT horas_mensais FROM funcionarios WHERE id = ?",
            (funcionario_id,),
            fetch_one=True
        )
        if funcionario and funcionario.get('horas_mensais'):
            return float(funcionario['horas_mensais']) / 25.0
    except Exception:
        pass
    return 8


def calcular_total_mensal(funcionario_id, mes, ano):
    result = DatabaseManager.execute_query(
        """
        SELECT
            SUM(horas_trabalhadas) as total_horas,
            SUM(horas_extras) as total_extras,
            COUNT(*) as dias_trabalhados
        FROM registros_ponto
        WHERE funcionario_id = ? AND mes = ? AND ano = ?
        """,
        (funcionario_id, mes, ano),
        fetch_one=True
    )
    return {
        'total_horas': (result or {}).get('total_horas') or 0,
        'total_extras': (result or {}).get('total_extras') or 0,
        'dias_trabalhados': (result or {}).get('dias_trabalhados') or 0
    }


def initialize_carga_table():
    DatabaseManager.execute_query(
        """
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
    )


def ensure_gastos_table():
    DatabaseManager.execute_query(
        """
        CREATE TABLE IF NOT EXISTS gastos_domesticos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descricao TEXT NOT NULL,
            categoria TEXT NOT NULL,
            valor REAL NOT NULL,
            data_gasto DATE NOT NULL,
            forma_pagamento TEXT NOT NULL,
            observacoes TEXT,
            data_criacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
    )


def pagination_info(page, per_page, total):
    total_pages = (total + per_page - 1) // per_page
    return {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_page': page - 1 if page > 1 else None,
        'next_page': page + 1 if page < total_pages else None
    }


@app.before_request
def ensure_db_on_first_request():
    if os.environ.get('SKIP_DB_INIT') == '1' or getattr(app, '_db_initialized', False):
        return
    try:
        db_dir = os.path.dirname(DB_FILE)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
        initialize_carga_table()
        ensure_gastos_table()
    finally:
        app._db_initialized = True


@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    per_page = 6
    offset = (page - 1) * per_page
    total_result = DatabaseManager.execute_query(
        "SELECT COUNT(*) as total FROM funcionarios WHERE ativo = 1",
        fetch_one=True
    )
    total = total_result['total'] if total_result else 0
    funcionarios_list = DatabaseManager.execute_query(
        "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome LIMIT ? OFFSET ?",
        (per_page, offset),
        fetch_all=True
    )
    funcionarios = {funcionario['nome']: funcionario for funcionario in funcionarios_list}
    return render_template(
        'index.html',
        funcionarios=funcionarios,
        pagination=pagination_info(page, per_page, total)
    )


@app.route('/funcionario/id/<int:funcionario_id>')
def visualizar_funcionario_por_id(funcionario_id):
    funcionario = DatabaseManager.execute_query(
        "SELECT nome FROM funcionarios WHERE id = ? AND ativo = 1",
        (funcionario_id,),
        fetch_one=True
    )
    if not funcionario:
        flash('Funcionario nao encontrado!', 'error')
        return redirect(url_for('index'))
    return redirect(url_for('visualizar_funcionario', nome=funcionario['nome']))


@app.route('/funcionario/<nome>')
def visualizar_funcionario(nome):
    funcionario_data = DatabaseManager.execute_query(
        "SELECT * FROM funcionarios WHERE nome = ? AND ativo = 1",
        (nome,),
        fetch_one=True
    )
    if not funcionario_data:
        flash('Funcionario nao encontrado!', 'error')
        return redirect(url_for('index'))

    page = request.args.get('page', 1, type=int)
    per_page = 10
    offset = (page - 1) * per_page
    total_result = DatabaseManager.execute_query(
        "SELECT COUNT(*) as total FROM registros_ponto WHERE funcionario_id = ?",
        (funcionario_data['id'],),
        fetch_one=True
    )
    total = total_result['total'] if total_result else 0
    registros = DatabaseManager.execute_query(
        """
        SELECT * FROM registros_ponto
        WHERE funcionario_id = ?
        ORDER BY ano DESC, mes DESC, dia DESC
        LIMIT ? OFFSET ?
        """,
        (funcionario_data['id'], per_page, offset),
        fetch_all=True
    )
    meses = DatabaseManager.execute_query(
        """
        SELECT DISTINCT mes, ano FROM registros_ponto
        WHERE funcionario_id = ?
        ORDER BY ano DESC, mes DESC
        """,
        (funcionario_data['id'],),
        fetch_all=True
    )
    totais_mensais = []
    for item in meses:
        total_mensal = calcular_total_mensal(funcionario_data['id'], item['mes'], item['ano'])
        totais_mensais.append({
            'mes': item['mes'],
            'ano': item['ano'],
            **total_mensal
        })

    return render_template(
        'funcionario.html',
        nome=nome,
        registros=registros,
        totais_mensais=totais_mensais,
        funcionario_data=funcionario_data,
        pagination=pagination_info(page, per_page, total)
    )


@app.route('/adicionar_funcionario', methods=['GET', 'POST'])
def adicionar_funcionario():
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        try:
            DatabaseManager.execute_query(
                """
                INSERT INTO funcionarios
                (nome, cargo, salario_mensal, salario_hora, horas_mensais, data_cadastro)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (nome, cargo, salario_mensal, salario_hora, horas_mensais, datetime.now().strftime('%Y-%m-%d'))
            )
            flash(f'Funcionario {nome} adicionado com sucesso!', 'success')
            return redirect(url_for('index'))
        except sqlite3.IntegrityError:
            flash(f'Funcionario {nome} ja existe no sistema!', 'error')
    return render_template('adicionar_funcionario.html')


@app.route('/registrar_horas', methods=['GET', 'POST'])
def registrar_horas():
    if request.method == 'POST':
        funcionario_nome = request.form['funcionario']
        data_str = request.form['data']
        hora_entrada = request.form.get('hora_entrada', '').strip()
        hora_saida_almoco = request.form.get('hora_saida_almoco', '').strip()
        hora_volta_almoco = request.form.get('hora_volta_almoco', '').strip()
        hora_saida = request.form.get('hora_saida', '').strip()
        funcionario = DatabaseManager.execute_query(
            "SELECT id FROM funcionarios WHERE nome = ? AND ativo = 1",
            (funcionario_nome,),
            fetch_one=True
        )
        if not funcionario:
            flash('Funcionario nao encontrado!', 'error')
            return redirect(url_for('registrar_horas'))
        # Verifica carga do funcionário
        carga = DatabaseManager.execute_query(
            "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1",
            (funcionario['id'],),
            fetch_one=True
        )

        # Campos obrigatórios
        if not hora_entrada or not hora_saida:
            flash('Preencha hora de entrada e hora de saída.', 'error')
            return redirect(url_for('registrar_horas'))

        # Decidir uso de intervalo: somente se a carga definir intervalo_min>0 e ambos os campos de almoço estiverem preenchidos
        has_interval = False
        try:
            if carga and (carga.get('intervalo_min') or 0) > 0 and hora_saida_almoco and hora_volta_almoco:
                has_interval = True
        except Exception:
            has_interval = False

        # Parse e validação dos horários
        try:
            entrada = datetime.strptime(f"{data_str} {hora_entrada}", "%Y-%m-%d %H:%M")
            saida = datetime.strptime(f"{data_str} {hora_saida}", "%Y-%m-%d %H:%M")
            if has_interval:
                saida_almoco = datetime.strptime(f"{data_str} {hora_saida_almoco}", "%Y-%m-%d %H:%M")
                volta_almoco = datetime.strptime(f"{data_str} {hora_volta_almoco}", "%Y-%m-%d %H:%M")
                if not (entrada < saida_almoco < volta_almoco < saida):
                    flash('Horários de almoço inválidos.', 'error')
                    return redirect(url_for('registrar_horas'))
                horas_trabalhadas = ((saida_almoco - entrada) + (saida - volta_almoco)).total_seconds() / 3600
                tempo_almoco_horas = (volta_almoco - saida_almoco).total_seconds() / 3600
            else:
                if saida <= entrada:
                    flash('Hora de saída deve ser maior que a hora de entrada.', 'error')
                    return redirect(url_for('registrar_horas'))
                horas_trabalhadas = (saida - entrada).total_seconds() / 3600
                tempo_almoco_horas = 0
        except ValueError:
            flash('Formato de hora inválido. Use HH:MM.', 'error')
            return redirect(url_for('registrar_horas'))
        except Exception:
            flash('Erro ao processar horários.', 'error')
            return redirect(url_for('registrar_horas'))

        data_obj = entrada.date()
        percent = extra_percentage_for_date(data_obj)
        if percent == 100:
            horas_extras = horas_trabalhadas
        else:
            horas_esperadas = obter_horas_normais_esperadas(funcionario['id'], data_str)
            horas_extras = calcular_horas_extras(horas_trabalhadas, horas_esperadas)

        try:
            DatabaseManager.execute_query(
                """
                INSERT INTO registros_ponto
                (funcionario_id, data, dia, mes, ano, hora_entrada, hora_saida_almoco,
                 hora_volta_almoco, hora_saida, tempo_almoco, horas_trabalhadas,
                 horas_extras, data_registro)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    funcionario['id'], data_str, entrada.day, entrada.month, entrada.year,
                    hora_entrada, hora_saida_almoco, hora_volta_almoco, hora_saida,
                    round(tempo_almoco_horas, 2), round(horas_trabalhadas, 2),
                    round(horas_extras, 2), datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                )
            )
            flash(f'Horas registradas para {funcionario_nome}!', 'success')
            return redirect(url_for('visualizar_funcionario', nome=funcionario_nome))
        except sqlite3.IntegrityError:
            flash(f'Ja existe registro para {funcionario_nome} na data {data_str}!', 'error')

    funcionarios_list = DatabaseManager.execute_query(
        "SELECT nome FROM funcionarios WHERE ativo = 1 ORDER BY nome",
        fetch_all=True
    )
    return render_template('registrar_horas.html', funcionarios={f['nome']: f for f in funcionarios_list})


@app.route('/relatorio_mensal/<funcionario_nome>/<int:mes>/<int:ano>')
def relatorio_mensal(funcionario_nome, mes, ano):
    funcionario_data = DatabaseManager.execute_query(
        "SELECT * FROM funcionarios WHERE nome = ? AND ativo = 1",
        (funcionario_nome,),
        fetch_one=True
    )
    if not funcionario_data:
        flash('Funcionario nao encontrado!', 'error')
        return redirect(url_for('index'))
    registros_mes = DatabaseManager.execute_query(
        """
        SELECT * FROM registros_ponto
        WHERE funcionario_id = ? AND mes = ? AND ano = ?
        ORDER BY dia
        """,
        (funcionario_data['id'], mes, ano),
        fetch_all=True
    )
    total_mensal = calcular_total_mensal(funcionario_data['id'], mes, ano)
    valor_horas_normais = 0
    valor_horas_extras = 0
    for registro in registros_mes:
        percent = extra_percentage_for_date(registro['data'])
        mult = extra_multiplier_for_date(registro['data'])
        # anexa informações para template
        registro['percentual'] = f"{percent}%"
        registro['multiplier'] = mult
        if percent == 100:
            # finais de semana / feriados: todas as horas são consideradas extras com 100% de acréscimo
            valor_horas_extras += registro['horas_trabalhadas'] * funcionario_data['salario_hora'] * mult
        else:
            horas_esperadas = obter_horas_normais_esperadas(funcionario_data['id'], registro['data'])
            valor_horas_normais += min(registro['horas_trabalhadas'], horas_esperadas) * funcionario_data['salario_hora']
            valor_horas_extras += registro['horas_extras'] * funcionario_data['salario_hora'] * mult
    meses_nomes = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    return render_template(
        'relatorio_mensal.html',
        funcionario=funcionario_nome,
        mes=mes,
        ano=ano,
        mes_nome=meses_nomes[mes - 1],
        registros=registros_mes,
        total=total_mensal,
        funcionario_data=funcionario_data,
        valor_horas_normais=valor_horas_normais,
        valor_horas_extras=valor_horas_extras
    )


@app.route('/editar_funcionario/<nome>', methods=['GET', 'POST'])
def editar_funcionario(nome):
    funcionario_data = DatabaseManager.execute_query(
        "SELECT * FROM funcionarios WHERE nome = ? AND ativo = 1",
        (nome,),
        fetch_one=True
    )
    if not funcionario_data:
        flash('Funcionario nao encontrado!', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        novo_nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        try:
            DatabaseManager.execute_query(
                """
                UPDATE funcionarios
                SET nome = ?, cargo = ?, salario_mensal = ?, salario_hora = ?, horas_mensais = ?
                WHERE id = ?
                """,
                (novo_nome, cargo, salario_mensal, salario_hora, horas_mensais, funcionario_data['id'])
            )
            flash(f'Funcionario {novo_nome} atualizado com sucesso!', 'success')
            return redirect(url_for('visualizar_funcionario', nome=novo_nome))
        except sqlite3.IntegrityError:
            flash(f'Nome {novo_nome} ja existe no sistema!', 'error')
    return render_template('editar_funcionario.html', funcionario=funcionario_data, nome=nome)


@app.route('/funcionario/excluir/<int:funcionario_id>', methods=['POST'])
def excluir_funcionario(funcionario_id):
    DatabaseManager.execute_query("UPDATE funcionarios SET ativo = 0 WHERE id = ?", (funcionario_id,))
    flash('Funcionario removido com sucesso!', 'success')
    return redirect(url_for('index'))


@app.route('/editar_registro/<int:registro_id>', methods=['GET', 'POST'])
def editar_registro(registro_id):
    registro = DatabaseManager.execute_query(
        """
        SELECT r.*, f.nome as funcionario_nome
        FROM registros_ponto r
        JOIN funcionarios f ON r.funcionario_id = f.id
        WHERE r.id = ?
        """,
        (registro_id,),
        fetch_one=True
    )
    if not registro:
        flash('Registro nao encontrado!', 'error')
        return redirect(url_for('index'))
    if request.method == 'POST':
        data_str = registro['data']
        hora_entrada = request.form.get('hora_entrada', '').strip()
        hora_saida_almoco = request.form.get('hora_saida_almoco', '').strip()
        hora_volta_almoco = request.form.get('hora_volta_almoco', '').strip()
        hora_saida = request.form.get('hora_saida', '').strip()

        # Checa carga do colaborador para saber se tem intervalo
        carga = DatabaseManager.execute_query(
            "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1",
            (registro['funcionario_id'],),
            fetch_one=True
        )

        # Campos obrigatórios
        if not hora_entrada or not hora_saida:
            flash('Preencha hora de entrada e hora de saída.', 'error')
            return redirect(url_for('editar_registro', registro_id=registro_id))

        # Decidir uso de intervalo: somente se a carga definir intervalo_min>0 e ambos os campos de almoço estiverem preenchidos
        has_interval = False
        try:
            if carga and (carga.get('intervalo_min') or 0) > 0 and hora_saida_almoco and hora_volta_almoco:
                has_interval = True
        except Exception:
            has_interval = False

        try:
            entrada = datetime.strptime(f"{data_str} {hora_entrada}", "%Y-%m-%d %H:%M")
            saida = datetime.strptime(f"{data_str} {hora_saida}", "%Y-%m-%d %H:%M")
            if has_interval:
                saida_almoco = datetime.strptime(f"{data_str} {hora_saida_almoco}", "%Y-%m-%d %H:%M")
                volta_almoco = datetime.strptime(f"{data_str} {hora_volta_almoco}", "%Y-%m-%d %H:%M")
                if not (entrada < saida_almoco < volta_almoco < saida):
                    flash('Horários de almoço inválidos.', 'error')
                    return redirect(url_for('editar_registro', registro_id=registro_id))
                horas_trabalhadas = ((saida_almoco - entrada) + (saida - volta_almoco)).total_seconds() / 3600
                tempo_almoco_horas = (volta_almoco - saida_almoco).total_seconds() / 3600
            else:
                if saida <= entrada:
                    flash('Hora de saída deve ser maior que a hora de entrada.', 'error')
                    return redirect(url_for('editar_registro', registro_id=registro_id))
                horas_trabalhadas = (saida - entrada).total_seconds() / 3600
                tempo_almoco_horas = 0
        except ValueError:
            flash('Formato de hora inválido. Use HH:MM.', 'error')
            return redirect(url_for('editar_registro', registro_id=registro_id))
        except Exception:
            flash('Erro ao processar horários.', 'error')
            return redirect(url_for('editar_registro', registro_id=registro_id))

        percent = extra_percentage_for_date(entrada.date())
        if percent == 100:
            horas_extras = horas_trabalhadas
        else:
            horas_esperadas = obter_horas_normais_esperadas(registro['funcionario_id'], data_str)
            horas_extras = calcular_horas_extras(horas_trabalhadas, horas_esperadas)
        DatabaseManager.execute_query(
            """
            UPDATE registros_ponto
            SET hora_entrada = ?, hora_saida_almoco = ?, hora_volta_almoco = ?, hora_saida = ?,
                tempo_almoco = ?, horas_trabalhadas = ?, horas_extras = ?, data_edicao = ?
            WHERE id = ?
            """,
            (
                hora_entrada, hora_saida_almoco, hora_volta_almoco, hora_saida,
                round(tempo_almoco_horas, 2), round(horas_trabalhadas, 2), round(horas_extras, 2),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'), registro_id
            )
        )
        flash('Registro atualizado com sucesso!', 'success')
        return redirect(url_for('visualizar_funcionario', nome=registro['funcionario_nome']))
    return render_template('editar_registro.html', registro=registro, registro_id=registro_id)


@app.route('/excluir_registro/<int:registro_id>', methods=['POST'])
def excluir_registro(registro_id):
    registro = DatabaseManager.execute_query(
        """
        SELECT f.nome as funcionario_nome
        FROM registros_ponto r
        JOIN funcionarios f ON r.funcionario_id = f.id
        WHERE r.id = ?
        """,
        (registro_id,),
        fetch_one=True
    )
    if registro:
        DatabaseManager.execute_query("DELETE FROM registros_ponto WHERE id = ?", (registro_id,))
        flash('Registro excluido com sucesso!', 'success')
        return redirect(url_for('visualizar_funcionario', nome=registro['funcionario_nome']))
    flash('Registro nao encontrado!', 'error')
    return redirect(url_for('index'))


@app.route('/relatorios')
@app.route('/relatorios/page/<int:page>')
def relatorios(page=1):
    per_page = 6
    offset = (page - 1) * per_page
    total_result = DatabaseManager.execute_query(
        "SELECT COUNT(*) as total FROM funcionarios WHERE ativo = 1",
        fetch_one=True
    )
    total = total_result['total'] if total_result else 0
    funcionarios = DatabaseManager.execute_query(
        "SELECT * FROM funcionarios WHERE ativo = 1 ORDER BY nome LIMIT ? OFFSET ?",
        (per_page, offset),
        fetch_all=True
    )
    meses_nomes = ['Janeiro', 'Fevereiro', 'Marco', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    relatorios_data = []
    for funcionario in funcionarios:
        meses = DatabaseManager.execute_query(
            """
            SELECT mes, ano, COUNT(*) as total
            FROM registros_ponto
            WHERE funcionario_id = ?
            GROUP BY mes, ano
            ORDER BY ano DESC, mes DESC
            """,
            (funcionario['id'],),
            fetch_all=True
        )
        for mes_item in meses:
            mes_item['nome'] = meses_nomes[mes_item['mes'] - 1]
        relatorios_data.append({
            'funcionario': funcionario,
            'total_registros': sum(m['total'] for m in meses),
            'meses_trabalhados': meses
        })
    return render_template(
        'relatorios.html',
        relatorios_data=relatorios_data,
        pagination=pagination_info(page, per_page, total)
    )


@app.route('/calculo_avulso', methods=['GET', 'POST'])
def calculo_avulso():
    funcionarios_list = DatabaseManager.execute_query(
        "SELECT nome, salario_hora FROM funcionarios WHERE ativo = 1 ORDER BY nome",
        fetch_all=True
    )
    funcionarios = {
        item['nome']: {'valor_hora': item['salario_hora'], 'salario_hora': item['salario_hora']}
        for item in funcionarios_list
    }
    resultado = None
    if request.method == 'POST':
        funcionario_nome = request.form['funcionario']
        quantidade_horas = float(request.form['quantidade_horas'])
        percentual = request.form['percentual']
        valor_hora_base = funcionarios[funcionario_nome]['valor_hora']
        multiplicador = 1.5 if percentual == '50' else 2.0
        valor_hora_calculado = valor_hora_base * multiplicador
        resultado = {
            'funcionario': funcionario_nome,
            'quantidade_horas': quantidade_horas,
            'valor_hora_base': valor_hora_base,
            'percentual': f'{percentual}%',
            'valor_hora_calculado': valor_hora_calculado,
            'valor_total': quantidade_horas * valor_hora_calculado
        }
    return render_template('calculo_avulso.html', funcionarios=funcionarios, resultado=resultado)


@app.route('/config_carga', methods=['GET', 'POST'])
def config_carga():
    initialize_carga_table()
    if request.method == 'POST':
        funcionario_id = int(request.form['funcionario_id'])
        inicio = request.form['inicio']
        fim = request.form['fim']
        dias_semana = ','.join(request.form.getlist('dias[]'))
        intervalo = int(request.form.get('intervalo') or 0)
        if not dias_semana:
            flash('Selecione ao menos um dia da semana.', 'error')
        else:
            DatabaseManager.execute_query(
                "UPDATE carga_horaria SET ativo = 0 WHERE funcionario_id = ?",
                (funcionario_id,)
            )
            DatabaseManager.execute_query(
                """
                INSERT INTO carga_horaria (funcionario_id, inicio, fim, dias_semana, intervalo_min, ativo)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (funcionario_id, inicio, fim, dias_semana, intervalo)
            )
            flash('Configuracao de carga salva com sucesso!', 'success')
            return redirect(url_for('config_carga'))
    funcionarios = DatabaseManager.execute_query(
        "SELECT id, nome FROM funcionarios WHERE ativo = 1 ORDER BY nome",
        fetch_all=True
    )
    cargas = DatabaseManager.execute_query(
        """
        SELECT c.*, f.nome as funcionario_nome
        FROM carga_horaria c
        LEFT JOIN funcionarios f ON f.id = c.funcionario_id
        WHERE c.ativo = 1
        ORDER BY f.nome
        """,
        fetch_all=True
    )
    return render_template('config_carga.html', funcionarios=funcionarios, cargas=cargas)


@app.route('/config_carga/delete/<int:carga_id>', methods=['POST'])
def config_carga_delete(carga_id):
    DatabaseManager.execute_query("UPDATE carga_horaria SET ativo = 0 WHERE id = ?", (carga_id,))
    flash('Configuracao removida com sucesso!', 'success')
    return redirect(url_for('config_carga'))


def categorias_gastos():
    return ['Alimentacao', 'Moradia', 'Transporte', 'Saude', 'Lazer', 'Outros']


@app.route('/controle_financeiro')
def controle_financeiro():
    ensure_gastos_table()
    hoje = datetime.now()
    resumo_mes = DatabaseManager.execute_query(
        """
        SELECT COALESCE(SUM(valor), 0) as gastos_mes, COUNT(*) as num_transacoes
        FROM gastos_domesticos
        WHERE data_gasto BETWEEN ? AND ?
        """,
        (hoje.strftime('%Y-%m-01'), hoje.strftime('%Y-%m-31')),
        fetch_one=True
    )
    gastos_mes = resumo_mes['gastos_mes'] if resumo_mes else 0
    resumo = {
        'gastos_mes': gastos_mes,
        'orcamento_restante': max(0, 3000 - gastos_mes),
        'num_transacoes': resumo_mes['num_transacoes'] if resumo_mes else 0
    }
    return render_template('controle_financeiro.html', resumo=resumo)


@app.route('/gastos/adicionar', methods=['GET', 'POST'])
def adicionar_gasto():
    ensure_gastos_table()
    if request.method == 'POST':
        DatabaseManager.execute_query(
            """
            INSERT INTO gastos_domesticos
            (descricao, categoria, valor, data_gasto, forma_pagamento, observacoes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request.form['descricao'].strip(),
                request.form['categoria'],
                float(request.form['valor']),
                request.form['data'],
                request.form['forma_pagamento'],
                request.form.get('observacoes', '').strip()
            )
        )
        flash('Gasto salvo com sucesso!', 'success')
        return redirect(url_for('listar_gastos'))
    return render_template('adicionar_gasto.html', categorias=categorias_gastos())


@app.route('/gastos')
def listar_gastos():
    ensure_gastos_table()
    gastos = DatabaseManager.execute_query(
        "SELECT * FROM gastos_domesticos ORDER BY data_gasto DESC, id DESC",
        fetch_all=True
    )
    for gasto in gastos:
        try:
            gasto['data_formatada'] = datetime.strptime(gasto['data_gasto'], '%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception:
            gasto['data_formatada'] = gasto['data_gasto']
    return render_template('listar_gastos.html', gastos=gastos, total_gastos=sum(g['valor'] for g in gastos))


@app.route('/gastos/excluir/<int:gasto_id>', methods=['POST'])
def excluir_gasto(gasto_id):
    ensure_gastos_table()
    DatabaseManager.execute_query("DELETE FROM gastos_domesticos WHERE id = ?", (gasto_id,))
    flash('Gasto excluido com sucesso!', 'success')
    return redirect(url_for('listar_gastos'))


@app.route('/gastos/relatorio')
def relatorio_gastos():
    ensure_gastos_table()
    hoje = datetime.now()
    inicio = request.args.get('data_inicio') or hoje.strftime('%Y-%m-01')
    fim = request.args.get('data_fim') or hoje.strftime('%Y-%m-31')
    rows = DatabaseManager.execute_query(
        """
        SELECT categoria, COALESCE(SUM(valor), 0) as total
        FROM gastos_domesticos
        WHERE data_gasto BETWEEN ? AND ?
        GROUP BY categoria
        ORDER BY total DESC
        """,
        (inicio, fim),
        fetch_all=True
    )
    total_geral = sum(row['total'] for row in rows)
    icons = {
        'Alimentacao': 'shopping-cart',
        'Moradia': 'home',
        'Transporte': 'car',
        'Saude': 'heartbeat',
        'Lazer': 'gamepad',
        'Outros': 'ellipsis-h'
    }
    cores = ['primary', 'success', 'info', 'warning', 'danger', 'secondary']
    gastos_por_categoria = []
    for idx, row in enumerate(rows):
        gastos_por_categoria.append({
            'nome': row['categoria'],
            'total': row['total'],
            'percentual': (row['total'] / total_geral * 100) if total_geral else 0,
            'icon': icons.get(row['categoria'], 'receipt'),
            'cor': cores[idx % len(cores)]
        })
    dados = {
        'mes_referencia': hoje.strftime('%m/%Y'),
        'total_geral': total_geral,
        'gastos_por_categoria': gastos_por_categoria
    }
    return render_template('relatorio_gastos.html', dados=dados)


@app.route('/api/funcionarios')
def api_funcionarios():
    funcionarios = DatabaseManager.execute_query(
        "SELECT id, nome, cargo, salario_hora FROM funcionarios WHERE ativo = 1 ORDER BY nome",
        fetch_all=True
    )
    return jsonify(funcionarios)


@app.route('/api/get_carga', methods=['POST'])
def api_get_carga():
    try:
        payload = request.get_json() or {}
        nome = payload.get('funcionario')
        data_str = payload.get('data')
        if not nome or not data_str:
            return jsonify({'aplicavel': False})

        funcionario = DatabaseManager.execute_query(
            "SELECT id FROM funcionarios WHERE nome = ? AND ativo = 1",
            (nome,),
            fetch_one=True
        )
        if not funcionario:
            return jsonify({'aplicavel': False})

        carga = DatabaseManager.execute_query(
            "SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1",
            (funcionario['id'],),
            fetch_one=True
        )

        if not carga:
            return jsonify({'aplicavel': False, 'intervalo_min': None, 'horas_esperadas': None})

        # Determina se a carga se aplica ao dia informado
        try:
            data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
            dias_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            dia_tag = dias_map[data_obj.weekday()]
            dias_semana = carga['dias_semana'].split(',') if carga.get('dias_semana') else []
            aplicavel = dia_tag in dias_semana
        except Exception:
            aplicavel = False

        intervalo_min = carga.get('intervalo_min') or 0
        horas_esperadas = None
        if aplicavel:
            horas_esperadas = obter_horas_normais_esperadas(funcionario['id'], data_str)

        return jsonify({'aplicavel': aplicavel, 'intervalo_min': intervalo_min, 'horas_esperadas': horas_esperadas})
    except Exception:
        return jsonify({'aplicavel': False})


@app.route('/api/verificar_lancamento', methods=['POST'])
def api_verificar_lancamento():
    try:
        payload = request.get_json() or {}
        nome = payload.get('funcionario')
        data_str = payload.get('data')
        if not nome or not data_str:
            return jsonify({'existe': False})

        funcionario = DatabaseManager.execute_query(
            "SELECT id FROM funcionarios WHERE nome = ? AND ativo = 1",
            (nome,),
            fetch_one=True
        )
        if not funcionario:
            return jsonify({'existe': False})

        registro = DatabaseManager.execute_query(
            "SELECT * FROM registros_ponto WHERE funcionario_id = ? AND data = ?",
            (funcionario['id'], data_str),
            fetch_one=True
        )
        if registro:
            return jsonify({'existe': True, 'registro': {
                'id': registro.get('id'),
                'hora_entrada': registro.get('hora_entrada'),
                'hora_saida': registro.get('hora_saida'),
                'horas_trabalhadas': registro.get('horas_trabalhadas'),
                'horas_extras': registro.get('horas_extras')
            }})
        return jsonify({'existe': False})
    except Exception:
        return jsonify({'existe': False})


if __name__ == '__main__':
    if not os.path.exists(DB_FILE):
        print("[AVISO] Banco SQLite nao encontrado!")
        print("        Execute: python migrar_para_sqlite.py")
        raise SystemExit(1)
    initialize_carga_table()
    ensure_gastos_table()
    print("[INFO] Usando banco SQLite: " + DB_FILE)
    app.run(debug=True, host='0.0.0.0', port=5001)
