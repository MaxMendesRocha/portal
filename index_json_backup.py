from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime, timedelta
import json
import os

app = Flask(__name__)
app.secret_key = 'sua_chave_secreta_aqui'

# Arquivo para armazenar os dados
DATA_FILE = 'horas_trabalho.json'

def carregar_dados():
    """Carrega os dados do arquivo JSON"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            dados = json.load(f)
            
        # Migração automática: se não tem salario_mensal, calcula baseado no salario_hora
        migrou = False
        for nome, funcionario in dados.get('funcionarios', {}).items():
            if 'salario_mensal' not in funcionario and 'salario_hora' in funcionario:
                funcionario['salario_mensal'] = funcionario['salario_hora'] * 220
                funcionario['horas_mensais'] = 220
                migrou = True
            elif 'salario_mensal' not in funcionario:
                # Valor padrão se não tem nem salario_hora nem salario_mensal
                funcionario['salario_mensal'] = 1518.00
                funcionario['salario_hora'] = 1518.00 / 220
                funcionario['horas_mensais'] = 220
                migrou = True
        
        # Salvar dados migrados
        if migrou:
            salvar_dados(dados)
            
        return dados
    return {'funcionarios': {}, 'registros': []}

def salvar_dados(dados):
    """Salva os dados no arquivo JSON"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def calcular_horas_extras(horas_trabalhadas, horas_normais=8):
    """Calcula horas extras baseado nas horas trabalhadas no dia"""
    if horas_trabalhadas > horas_normais:
        return horas_trabalhadas - horas_normais
    return 0

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

def calcular_total_mensal(funcionario, mes, ano):
    """Calcula o total de horas trabalhadas e extras no mês"""
    dados = carregar_dados()
    total_horas = 0
    total_extras = 0
    dias_trabalhados = 0
    
    for registro in dados['registros']:
        if (registro['funcionario'] == funcionario and 
            registro['mes'] == mes and 
            registro['ano'] == ano):
            total_horas += registro['horas_trabalhadas']
            total_extras += registro['horas_extras']
            dias_trabalhados += 1
    
    return {
        'total_horas': total_horas,
        'total_extras': total_extras,
        'dias_trabalhados': dias_trabalhados
    }

@app.route('/')
def index():
    """Página inicial"""
    dados = carregar_dados()
    funcionarios = dados['funcionarios']
    return render_template('index.html', funcionarios=funcionarios)

@app.route('/funcionario/<nome>')
def visualizar_funcionario(nome):
    """Visualiza os dados de um funcionário específico"""
    dados = carregar_dados()
    
    # Obter registros do funcionário com índices
    registros_com_id = []
    for i, registro in enumerate(dados['registros']):
        if registro['funcionario'] == nome:
            registro_copy = registro.copy()
            registro_copy['id'] = i
            registros_com_id.append(registro_copy)
    
    registros_com_id.sort(key=lambda x: (x['ano'], x['mes'], x['dia']), reverse=True)
    
    # Calcular totais por mês
    meses_anos = set((r['mes'], r['ano']) for r in registros_com_id)
    totais_mensais = []
    
    for mes, ano in meses_anos:
        total_mensal = calcular_total_mensal(nome, mes, ano)
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
                         registros=registros_com_id, 
                         totais_mensais=totais_mensais,
                         funcionario_data=dados['funcionarios'].get(nome, {}))

@app.route('/adicionar_funcionario', methods=['GET', 'POST'])
def adicionar_funcionario():
    """Adiciona um novo funcionário"""
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        
        # Calcular valor da hora baseado no salário mensal
        # 220 horas mensais (44h/semana x 5 semanas)
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        
        dados = carregar_dados()
        dados['funcionarios'][nome] = {
            'cargo': cargo,
            'salario_mensal': salario_mensal,
            'salario_hora': salario_hora,
            'horas_mensais': horas_mensais,
            'data_cadastro': datetime.now().strftime('%Y-%m-%d')
        }
        
        salvar_dados(dados)
        flash(f'Funcionário {nome} adicionado com sucesso! Salário: R$ {salario_mensal:.2f}/mês - R$ {salario_hora:.2f}/hora', 'success')
        return redirect(url_for('index'))
    
    return render_template('adicionar_funcionario.html')

@app.route('/registrar_horas', methods=['GET', 'POST'])
def registrar_horas():
    """Registra horas trabalhadas"""
    dados = carregar_dados()
    
    if request.method == 'POST':
        funcionario = request.form['funcionario']
        data = request.form['data']
        hora_entrada = request.form['hora_entrada']
        hora_saida_almoco = request.form['hora_saida_almoco']
        hora_volta_almoco = request.form['hora_volta_almoco']
        hora_saida = request.form['hora_saida']
        
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
        
        # Criar registro
        registro = {
            'funcionario': funcionario,
            'data': data,
            'dia': entrada.day,
            'mes': entrada.month,
            'ano': entrada.year,
            'hora_entrada': hora_entrada,
            'hora_saida_almoco': hora_saida_almoco,
            'hora_volta_almoco': hora_volta_almoco,
            'hora_saida': hora_saida,
            'tempo_almoco': round(tempo_almoco_horas, 2),
            'horas_trabalhadas': round(horas_trabalhadas, 2),
            'horas_extras': round(horas_extras, 2),
            'data_registro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        dados['registros'].append(registro)
        salvar_dados(dados)
        
        flash(f'Horas registradas para {funcionario}! Total: {horas_trabalhadas:.2f}h, Extras: {horas_extras:.2f}h, Almoço: {tempo_almoco_horas:.2f}h', 'success')
        return redirect(url_for('visualizar_funcionario', nome=funcionario))
    
    funcionarios = dados['funcionarios']
    return render_template('registrar_horas.html', funcionarios=funcionarios)

@app.route('/relatorio_mensal/<funcionario>/<int:mes>/<int:ano>')
def relatorio_mensal(funcionario, mes, ano):
    """Gera relatório mensal detalhado"""
    dados = carregar_dados()
    
    # Filtrar registros do mês com IDs
    registros_mes = []
    for i, registro in enumerate(dados['registros']):
        if (registro['funcionario'] == funcionario and 
            registro['mes'] == mes and 
            registro['ano'] == ano):
            registro_copy = registro.copy()
            registro_copy['id'] = i
            registros_mes.append(registro_copy)
    
    registros_mes.sort(key=lambda x: x['dia'])
    
    total_mensal = calcular_total_mensal(funcionario, mes, ano)
    funcionario_data = dados['funcionarios'].get(funcionario, {})
    
    # Calcular valores monetários
    valor_horas_normais = 0
    valor_horas_extras = 0
    
    if 'salario_hora' in funcionario_data:
        salario_hora = funcionario_data['salario_hora']
        for registro in registros_mes:
            horas_normais = min(registro['horas_trabalhadas'], 8)
            valor_horas_normais += horas_normais * salario_hora
            valor_horas_extras += registro['horas_extras'] * salario_hora * 1.5  # 50% adicional
    
    meses_nomes = ['Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
                   'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro']
    
    return render_template('relatorio_mensal.html',
                         funcionario=funcionario,
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
    dados = carregar_dados()
    
    if nome not in dados['funcionarios']:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        novo_nome = request.form['nome'].strip()
        cargo = request.form['cargo'].strip()
        salario_mensal = float(request.form['salario_mensal'])
        
        # Calcular valor da hora baseado no salário mensal
        horas_mensais = 220
        salario_hora = salario_mensal / horas_mensais
        
        # Se o nome mudou, atualizar todas as referências
        if novo_nome != nome:
            # Atualizar funcionário
            dados['funcionarios'][novo_nome] = dados['funcionarios'].pop(nome)
            
            # Atualizar registros
            for registro in dados['registros']:
                if registro['funcionario'] == nome:
                    registro['funcionario'] = novo_nome
        
        # Atualizar dados do funcionário
        dados['funcionarios'][novo_nome] = {
            'cargo': cargo,
            'salario_mensal': salario_mensal,
            'salario_hora': salario_hora,
            'horas_mensais': horas_mensais,
            'data_cadastro': dados['funcionarios'][novo_nome].get('data_cadastro', datetime.now().strftime('%Y-%m-%d'))
        }
        
        salvar_dados(dados)
        flash(f'Funcionário {novo_nome} atualizado com sucesso!', 'success')
        return redirect(url_for('visualizar_funcionario', nome=novo_nome))
    
    funcionario_data = dados['funcionarios'][nome]
    return render_template('editar_funcionario.html', nome=nome, funcionario_data=funcionario_data)

@app.route('/editar_registro/<int:registro_id>', methods=['GET', 'POST'])
def editar_registro(registro_id):
    """Edita um registro de horas"""
    dados = carregar_dados()
    
    if registro_id >= len(dados['registros']) or registro_id < 0:
        flash('Registro não encontrado!', 'error')
        return redirect(url_for('index'))
    
    registro = dados['registros'][registro_id]
    
    if request.method == 'POST':
        funcionario = request.form['funcionario']
        data = request.form['data']
        hora_entrada = request.form['hora_entrada']
        hora_saida_almoco = request.form['hora_saida_almoco']
        hora_volta_almoco = request.form['hora_volta_almoco']
        hora_saida = request.form['hora_saida']
        
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
        
        # Atualizar registro
        dados['registros'][registro_id] = {
            'funcionario': funcionario,
            'data': data,
            'dia': entrada.day,
            'mes': entrada.month,
            'ano': entrada.year,
            'hora_entrada': hora_entrada,
            'hora_saida_almoco': hora_saida_almoco,
            'hora_volta_almoco': hora_volta_almoco,
            'hora_saida': hora_saida,
            'tempo_almoco': round(tempo_almoco_horas, 2),
            'horas_trabalhadas': round(horas_trabalhadas, 2),
            'horas_extras': round(horas_extras, 2),
            'data_registro': registro.get('data_registro', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'data_edicao': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        salvar_dados(dados)
        flash(f'Registro editado com sucesso! Total: {horas_trabalhadas:.2f}h, Extras: {horas_extras:.2f}h', 'success')
        return redirect(url_for('visualizar_funcionario', nome=funcionario))
    
    funcionarios = dados['funcionarios']
    return render_template('editar_registro.html', registro=registro, registro_id=registro_id, funcionarios=funcionarios)

@app.route('/excluir_registro/<int:registro_id>', methods=['POST'])
def excluir_registro(registro_id):
    """Exclui um registro de horas"""
    dados = carregar_dados()
    
    if registro_id >= len(dados['registros']) or registro_id < 0:
        flash('Registro não encontrado!', 'error')
        return redirect(url_for('index'))
    
    registro = dados['registros'][registro_id]
    funcionario_nome = registro['funcionario']
    
    # Remover registro
    dados['registros'].pop(registro_id)
    
    salvar_dados(dados)
    flash('Registro excluído com sucesso!', 'success')
    return redirect(url_for('visualizar_funcionario', nome=funcionario_nome))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)