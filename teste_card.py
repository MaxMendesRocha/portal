import requests

try:
    response = requests.get('http://127.0.0.1:5001/')
    print(f"Status: {response.status_code}")
    print(f"Tamanho: {len(response.text)}")
    
    if 'Controle Financeiro' in response.text:
        print("✅ Card 'Controle Financeiro' ENCONTRADO!")
    else:
        print("❌ Card 'Controle Financeiro' NÃO encontrado")
    
    # Contar cards
    import re
    cards = re.findall(r'<h5 class="card-title">(.*?)</h5>', response.text)
    print(f"Cards encontrados: {len(cards)}")
    for i, card in enumerate(cards, 1):
        print(f"  {i}. {card}")
        
except Exception as e:
    print(f"Erro: {e}")
