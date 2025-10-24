# Portal de Horas - Configuração de Rede Residencial

## 🌐 ACESSO NA REDE LOCAL

### IP do Servidor
- **IP Local:** Detectado automaticamente
- **Porta:** 5001
- **Protocolo:** HTTP

### Como Acessar

#### 🖥️ **Computadores na mesma rede:**
```
http://[IP_DO_SERVIDOR]:5000
```

#### 📱 **Smartphones/Tablets:**
1. Conectar na mesma rede WiFi
2. Abrir navegador (Chrome, Firefox, Safari)
3. Digitar: `[IP_DO_SERVIDOR]:5000`

### 🔍 Descobrir o IP do Servidor
Execute no computador servidor:
```bash
python servidor_producao.py
```
O IP será mostrado no console.

## 🛡️ CONFIGURAÇÃO DO FIREWALL

### Windows Defender Firewall
1. **Painel de Controle** → **Sistema e Segurança** → **Firewall do Windows**
2. **Configurações Avançadas**
3. **Regras de Entrada** → **Nova Regra**
4. **Porta** → **TCP** → **Porta específica: 5000**
5. **Permitir a conexão**
6. **Todos os perfis marcados**
7. Nome: "Portal de Horas"

### Comando rápido (PowerShell como Admin):
```powershell
New-NetFirewallRule -DisplayName "Portal de Horas" -Direction Inbound -Protocol TCP -LocalPort 5001 -Action Allow
```

## 🔧 CONFIGURAÇÃO AUTOMÁTICA

### Inicialização Automática
1. Criar atalho do `iniciar_servidor.bat`
2. Colocar na pasta: `C:\Users\[USUARIO]\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`
3. O servidor iniciará com o Windows

### Serviço Windows (Avançado)
Para executar como serviço do Windows, instale NSSM:
```bash
# Baixar NSSM (Non-Sucking Service Manager)
# https://nssm.cc/download

nssm install "Portal de Horas"
# Aplicação: python.exe
# Argumentos: C:\caminho\para\servidor_producao.py
```

## 📋 TROUBLESHOOTING

### Problemas Comuns

1. **"Não consegue acessar de outro dispositivo"**
   - Verificar se estão na mesma rede WiFi
   - Liberar porta 5000 no firewall
   - Verificar IP correto

2. **"Página não carrega"**
   - Confirmar que servidor está rodando
   - Testar acesso local primeiro (127.0.0.1:5000)
   - Verificar antivírus não está bloqueando

3. **"Servidor para sozinho"**
   - Verificar se há atualizações automáticas
   - Configurar para não hibernar/suspender
   - Usar serviço Windows para maior estabilidade

### Logs de Acesso
O servidor mostra todos os acessos no console:
```
192.168.1.50 - - [27/Sep/2025 14:32:24] "GET / HTTP/1.1" 200 -
```

## 🔐 SEGURANÇA

### Rede Doméstica
- Sistema acessível apenas na rede local
- Não exposto à internet
- Sem autenticação (adequado para uso doméstico)

### Para Maior Segurança (Opcional)
- Configurar senha WiFi forte
- Usar rede separada para dispositivos IoT
- Monitorar acessos através dos logs

## 📞 SUPORTE

### Comandos Úteis

**Verificar IP:**
```bash
python servidor_producao.py --info
```

**Testar conectividade:**
```bash
ping [IP_DO_SERVIDOR]
```

**Ver dispositivos na rede:**
```bash
arp -a
```
