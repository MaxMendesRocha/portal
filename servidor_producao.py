#!/usr/bin/env python3
"""
Servidor de Produção para Portal de Horas
Configurado para uso doméstico em rede local
"""

import os
import subprocess
import sys
from datetime import datetime
import socket

def obter_ip_local():
    """Obtém o IP local da máquina"""
    try:
        # Conecta a um endereço externo para descobrir o IP local
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip_local = s.getsockname()[0]
        return ip_local
    except Exception:
        return "127.0.0.1"

def verificar_dependencias():
    """Verifica se Flask está instalado"""
    try:
        import flask
        print("✅ Flask encontrado")
        return True
    except ImportError:
        print("❌ Flask não encontrado!")
        print("   Execute: pip install flask")
        return False

def iniciar_servidor_producao():
    """Inicia o servidor usando Waitress (WSGI server para produção)"""
    print("🚀 Iniciando Portal de Horas - Servidor de Produção")
    print("=" * 60)
    
    # Verificar dependências
    if not verificar_dependencias():
        print("❌ Falha na verificação de dependências")
        return False
    
    # Verificar se o banco existe
    if not os.path.exists('horas_trabalho.db'):
        print("❌ Banco de dados não encontrado!")
        print("   Execute: python migrar_para_sqlite.py")
        return False
    
    # Obter IP local
    ip_local = obter_ip_local()
    porta = 5001
    
    print(f"🌐 Servidor iniciado em:")
    print(f"   Local:      http://127.0.0.1:{porta}")
    print(f"   Rede:       http://{ip_local}:{porta}")
    print(f"   Data/Hora:  {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print()
    print("💡 Compartilhe o endereço da rede com outros dispositivos:")
    print(f"   http://{ip_local}:{porta}")
    print()
    print("🔧 Configurações:")
    print("   - Servidor: Flask (Otimizado para uso doméstico)")
    print("   - Banco: SQLite (horas_trabalho.db)")
    print("   - Fechamento: 26-25 (customizado)")
    print("   - Base mensal: 200 horas")
    print()
    print("⏹️  Para parar o servidor: Ctrl+C")
    print("=" * 60)
    
    try:
        # Usar Flask nativo (adequado para uso doméstico)
        from index import app
        
        # Configurar aplicação para produção
        app.config['ENV'] = 'production'
        app.config['DEBUG'] = True
        
        # Iniciar servidor Flask
        app.run(host='0.0.0.0', port=porta, threaded=True, debug=True)
        
    except KeyboardInterrupt:
        print("\n\n🛑 Servidor interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro ao iniciar servidor: {e}")
        return False
    
    return True

def mostrar_informacoes_rede():
    """Mostra informações sobre como acessar na rede"""
    ip_local = obter_ip_local()
    print("\n📱 ACESSO VIA REDE LOCAL")
    print("=" * 40)
    print("Para acessar de outros dispositivos na sua rede:")
    print()
    print("🖥️  Computadores:")
    print(f"   http://{ip_local}:5000")
    print()
    print("📱 Smartphones/Tablets:")
    print("   1. Conecte na mesma rede WiFi")
    print(f"   2. Abra o navegador e digite: {ip_local}:5000")
    print()
    print("🔒 FIREWALL DO WINDOWS:")
    print("   Se não conseguir acessar, libere a porta 5000:")
    print("   1. Painel de Controle > Sistema e Segurança > Firewall do Windows")
    print("   2. Configurações Avançadas > Regras de Entrada")
    print("   3. Nova Regra > Porta > TCP > 5000")
    print()

if __name__ == '__main__':
    print("🏠 PORTAL DE HORAS - CONFIGURAÇÃO RESIDENCIAL")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--info':
        mostrar_informacoes_rede()
    else:
        if iniciar_servidor_producao():
            print("✅ Servidor finalizado com sucesso")
        else:
            print("❌ Erro na execução do servidor")
            sys.exit(1)
