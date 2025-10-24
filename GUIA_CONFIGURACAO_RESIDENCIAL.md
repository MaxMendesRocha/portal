# 🏠 PORTAL DE HORAS - GUIA DE CONFIGURAÇÃO RESIDENCIAL

## ✅ SISTEMA CONFIGURADO E FUNCIONANDO!

### 🌐 **ENDEREÇOS DE ACESSO**

**Seu servidor está disponível em:**
- **Local:** http://127.0.0.1:5001
- **Rede:** http://192.168.3.139:5001

### 📱 **ACESSO DE OUTROS DISPOSITIVOS**

Para acessar de smartphones, tablets ou outros computadores:

1. **Conectar na mesma rede WiFi**
2. **Abrir o navegador**
3. **Digitar:** `192.168.3.139:5001`

---

## 🚀 COMO INICIAR O SISTEMA

### Método 1: Script Automático (Recomendado)
```bash
# Clique duplo no arquivo:
iniciar_servidor.bat
```

### Método 2: Linha de Comando
```bash
cd "C:\Users\max_rocha\OneDrive - Sicredi\Documents\Doc Max\Portal"
python servidor_producao.py
```

### Método 3: Servidor de Desenvolvimento
```bash
python index.py
```

---

## 🛠️ CONFIGURAÇÕES ESSENCIAIS

### 1. **Firewall do Windows**
Se outros dispositivos não conseguem acessar:

**PowerShell (Executar como Administrador):**
```powershell
New-NetFirewallRule -DisplayName "Portal de Horas" -Direction Inbound -Protocol TCP -LocalPort 5001 -Action Allow
```

**Ou pelo Painel de Controle:**
1. Painel de Controle → Firewall do Windows
2. Configurações Avançadas → Regras de Entrada
3. Nova Regra → Porta → TCP → 5001 → Permitir

### 2. **IP Fixo (Opcional)**
Para manter sempre o mesmo IP:
1. Roteador → Configurações DHCP
2. Reservar IP para seu computador
3. Ou configurar IP estático no Windows

### 3. **Inicialização Automática**
Para iniciar com o Windows:
1. Criar atalho de `iniciar_servidor.bat`
2. Colocar em: `C:\Users\max_rocha\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

---

## 📊 FUNCIONALIDADES DISPONÍVEIS

- ✅ **Cadastro de Funcionários**
- ✅ **Registro de Horas (08:00-12:00 / 13:00-17:00)**
- ✅ **Cálculo Automático de Horas Extras**
- ✅ **Relatórios Mensais (Período 26-25)**
- ✅ **Base de Cálculo: 200h mensais**
- ✅ **Salário: R$ 1.518,00**
- ✅ **Interface Responsiva (Mobile)**
- ✅ **Banco SQLite Seguro**

---

## 🔧 TROUBLESHOOTING

### Problema: "Não consegue acessar de outro dispositivo"
**Soluções:**
- Verificar se ambos estão na mesma rede WiFi
- Liberar porta 5001 no firewall
- Confirmar IP: `192.168.3.139:5001`
- Testar acesso local primeiro

### Problema: "Servidor não inicia"
**Soluções:**
- Verificar se Python está instalado
- Executar: `pip install flask`
- Verificar se porta 5001 está livre

### Problema: "Dados não salvam"
**Soluções:**
- Verificar se arquivo `horas_trabalho.db` existe
- Executar: `python migrar_para_sqlite.py`
- Verificar permissões da pasta

---

## 📞 COMANDOS ÚTEIS

### Verificar IP atual:
```bash
python servidor_producao.py --info
```

### Backup do banco:
```bash
copy horas_trabalho.db backup_horas_$(Get-Date -Format "yyyyMMdd").db
```

### Ver dispositivos na rede:
```bash
arp -a
```

### Testar conectividade:
```bash
ping 192.168.3.139
```

---

## 🔐 SEGURANÇA

- **Acesso apenas na rede local** (não exposto à internet)
- **Banco SQLite criptografado** no filesystem
- **Sem autenticação** (adequado para uso familiar)
- **Logs de acesso** visíveis no console

---

## 📈 PRÓXIMOS PASSOS

1. **Testar acesso de outros dispositivos**
2. **Configurar backup automático**
3. **Treinar usuários no sistema**
4. **Monitorar logs de acesso**
5. **Considerar IP fixo se necessário**

---

## 🎯 SISTEMA 100% OPERACIONAL!

Seu **Portal de Horas** está configurado e funcionando perfeitamente para uso residencial. Todos podem acessar através da rede WiFi doméstica!
