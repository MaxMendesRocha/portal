import os
import sqlite3
from datetime import datetime, date
import json

DB_FILE = os.environ.get('DB_FILE', 'horas_trabalho.db')


def carregar_feriados():
    path = 'feriados.json'
    if not os.path.exists(path):
        return set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return set(data)
    except Exception:
        return set()


def is_feriado(data_obj, feriados):
    return data_obj.strftime('%Y-%m-%d') in feriados


def extra_percentage_for_date(data_input, feriados):
    if isinstance(data_input, str):
        data_obj = datetime.strptime(data_input, '%Y-%m-%d').date()
    elif isinstance(data_input, date):
        data_obj = data_input
    else:
        data_obj = data_input.date()
    try:
        if data_obj.weekday() >= 5 or is_feriado(data_obj, feriados):
            return 100
    except Exception:
        pass
    return 50


def obter_horas_normais_esperadas(conn, funcionario_id, data_str):
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM carga_horaria WHERE funcionario_id = ? AND ativo = 1", (funcionario_id,))
        carga = cur.fetchone()
        data_obj = datetime.strptime(data_str, '%Y-%m-%d').date()
        dias_map = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        if carga:
            dias_semana = (carga['dias_semana'] or '').split(',') if carga.get('dias_semana') else []
            dia_tag = dias_map[data_obj.weekday()]
            if dia_tag in dias_semana:
                try:
                    inicio_dt = datetime.strptime(f"{data_str} {carga['inicio']}", "%Y-%m-%d %H:%M")
                    fim_dt = datetime.strptime(f"{data_str} {carga['fim']}", "%Y-%m-%d %H:%M")
                    intervalo_h = (carga.get('intervalo_min') or 0) / 60.0
                    return (fim_dt - inicio_dt).total_seconds() / 3600 - intervalo_h
                except Exception:
                    pass

        cur.execute("SELECT horas_mensais FROM funcionarios WHERE id = ?", (funcionario_id,))
        funcionario = cur.fetchone()
        if funcionario and funcionario.get('horas_mensais'):
            try:
                return float(funcionario['horas_mensais']) / 25.0
            except Exception:
                pass
    except Exception:
        pass
    return 8.0


def calcular_horas_extras(horas_trabalhadas, horas_normais=8.0):
    try:
        return max(0.0, horas_trabalhadas - horas_normais)
    except Exception:
        return 0.0


def main():
    if not os.path.exists(DB_FILE):
        print(f"Banco de dados nao encontrado: {DB_FILE}")
        return
    feriados = carregar_feriados()
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT id, funcionario_id, data, hora_entrada, hora_saida_almoco, hora_volta_almoco, hora_saida, horas_trabalhadas FROM registros_ponto")
    rows = cur.fetchall()
    total = len(rows)
    updated = 0
    for r in rows:
        rid = r['id']
        data_str = r['data']
        hora_entrada = r['hora_entrada']
        hora_saida_almoco = r['hora_saida_almoco']
        hora_volta_almoco = r['hora_volta_almoco']
        hora_saida = r['hora_saida']
        horas_trabalhadas_calc = r['horas_trabalhadas'] or 0.0

        # Recalcular horas_trabalhadas se todos os tempos existirem
        try:
            if hora_entrada and hora_saida_almoco and hora_volta_almoco and hora_saida:
                entrada = datetime.strptime(f"{data_str} {hora_entrada}", "%Y-%m-%d %H:%M")
                saida_almoco = datetime.strptime(f"{data_str} {hora_saida_almoco}", "%Y-%m-%d %H:%M")
                volta_almoco = datetime.strptime(f"{data_str} {hora_volta_almoco}", "%Y-%m-%d %H:%M")
                saida = datetime.strptime(f"{data_str} {hora_saida}", "%Y-%m-%d %H:%M")
                horas_trabalhadas_calc = ((saida_almoco - entrada) + (saida - volta_almoco)).total_seconds() / 3600
        except Exception:
            pass

        percent = extra_percentage_for_date(data_str, feriados)
        if percent == 100:
            horas_extras_calc = horas_trabalhadas_calc
        else:
            horas_esperadas = obter_horas_normais_esperadas(conn, r['funcionario_id'], data_str)
            horas_extras_calc = calcular_horas_extras(horas_trabalhadas_calc, horas_esperadas)

        horas_trabalhadas_calc = round(horas_trabalhadas_calc, 2)
        horas_extras_calc = round(horas_extras_calc, 2)

        try:
            cur.execute(
                "UPDATE registros_ponto SET horas_trabalhadas = ?, horas_extras = ? WHERE id = ?",
                (horas_trabalhadas_calc, horas_extras_calc, rid)
            )
            updated += 1
        except Exception:
            print(f"Falha ao atualizar registro id={rid}")

    conn.commit()
    conn.close()
    print(f"Total registros: {total}. Atualizados: {updated}.")


if __name__ == '__main__':
    main()
