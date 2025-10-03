#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para testar as correções do erro Jinja2
"""

import requests
import sys

def testar_rotas():
    """Testa as rotas principais do sistema"""
    base_url = "http://127.0.0.1:5000"
    
    print("🧪 TESTE DAS CORREÇÕES JINJA2")
    print("=" * 50)
    
    rotas_para_testar = [
        ("/", "Página inicial"),
        ("/registrar_horas", "Registrar horas"),
        ("/funcionario/Fabieli%20Patricia%20Altissimo", "Funcionário"),
        ("/relatorio_mensal/Fabieli%20Patricia%20Altissimo/9/2025", "Relatório mensal")
    ]
    
    sucessos = 0
    erros = 0
    
    for rota, nome in rotas_para_testar:
        try:
            print(f"\n🔍 Testando: {nome}")
            print(f"   URL: {base_url}{rota}")
            
            response = requests.get(f"{base_url}{rota}", timeout=10)
            
            if response.status_code == 200:
                print(f"   ✅ Status: {response.status_code} - OK")
                
                # Verificar se não há erro Jinja2 na resposta
                if "UndefinedError" in response.text:
                    print(f"   ⚠️  Erro Jinja2 detectado no HTML")
                    erros += 1
                elif "list object" in response.text and "has no attribute" in response.text:
                    print(f"   ⚠️  Erro de atributo detectado no HTML")
                    erros += 1
                else:
                    print(f"   ✅ Conteúdo: OK (sem erros Jinja2)")
                    sucessos += 1
                    
            else:
                print(f"   ❌ Status: {response.status_code} - Erro")
                erros += 1
                
        except requests.exceptions.ConnectionError:
            print(f"   ❌ Conexão: Servidor não está respondendo")
            erros += 1
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout: Servidor demorou para responder")
            erros += 1
        except Exception as e:
            print(f"   ❌ Erro: {e}")
            erros += 1
    
    print(f"\n📊 RESULTADO DOS TESTES:")
    print(f"   ✅ Sucessos: {sucessos}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📈 Taxa de sucesso: {(sucessos/(sucessos+erros)*100):.1f}%")
    
    if erros == 0:
        print(f"\n🎉 TODOS OS TESTES PASSARAM!")
        print(f"   ✅ Erro Jinja2 corrigido com sucesso")
        print(f"   ✅ Sistema funcionando perfeitamente")
        return True
    else:
        print(f"\n⚠️  ALGUNS TESTES FALHARAM")
        print(f"   Verifique o servidor e as correções")
        return False

def main():
    """Função principal"""
    print("🔧 VERIFICAÇÃO DAS CORREÇÕES")
    print("=" * 50)
    print("📝 Correções aplicadas:")
    print("   ✅ Rota '/' - funcionários convertido para dicionário")
    print("   ✅ Rota '/registrar_horas' - funcionários formatado corretamente")
    print("   ✅ Rota '/editar_registro' - funcionários incluído no template")
    print("   ✅ Compatibilidade com templates mantida")
    print()
    
    if testar_rotas():
        print(f"\n🌐 Sistema disponível em:")
        print(f"   http://127.0.0.1:5000")
        print(f"   http://10.24.92.174:5000")
        sys.exit(0)
    else:
        print(f"\n❌ Ainda há problemas no sistema")
        sys.exit(1)

if __name__ == '__main__':
    main()
