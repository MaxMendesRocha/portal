# Portal de Controle de Horas

Sistema web para controlar horas trabalhadas e calcular horas extras de funcionários.

## Funcionalidades

- ✅ Cadastro de funcionários com cargo e salário por hora
- ✅ Registro de horas trabalhadas (entrada e saída)
- ✅ Cálculo automático de horas extras (acima de 8h/dia)
- ✅ Relatórios mensais detalhados
- ✅ Cálculo de valores financeiros
- ✅ Interface web moderna e responsiva
- ✅ Relatórios para impressão
- ✅ Suporte para deployment em ambientes serverless (Vercel)

## Como usar

### 1. Instalar dependências

```powershell
pip install -r requirements.txt
```

### 2. Executar o sistema

**Localmente:**
```powershell
python index.py
```

Abra seu navegador e acesse: http://localhost:5000

**Em produção (Vercel):**
```bash
vercel deploy
```

### 3. Configuração de Variáveis de Ambiente

Para produção, configure as seguintes variáveis no seu ambiente:

```bash
DB_FILE=/tmp/horas_trabalho.json  # Caminho para o arquivo de banco de dados
```

## Fluxo de Uso

1. **Adicionar Funcionário**
   - Acesse "Adicionar Funcionário"
   - Preencha nome, cargo e salário por hora
   - Salve o cadastro

2. **Registrar Horas**
   - Acesse "Registrar Horas"
   - Selecione o funcionário
   - Informe data, hora de entrada e saída
   - O sistema calcula automaticamente as horas extras

3. **Visualizar Relatórios**
   - Na página inicial, clique em "Ver Detalhes" do funcionário
   - Visualize resumos mensais e registros detalhados
   - Acesse relatórios mensais completos com valores financeiros

## Regras de Cálculo

- **Jornada Normal**: 8 horas por dia
- **Horas Extras**: Acima de 8 horas trabalhadas no dia
- **Valor das Extras**: 50% a mais que a hora normal (conforme CLT)
- **Cálculo Automático**: Baseado na diferença entre entrada e saída

## Recursos

- **Armazenamento**: Dados salvos em arquivo JSON local
- **Responsivo**: Interface adapta para mobile e desktop
- **Impressão**: Relatórios otimizados para impressão
- **Prévia**: Cálculo em tempo real ao registrar horas
- **Bootstrap**: Interface moderna com ícones Font Awesome
- **Serverless Ready**: Compatível com ambientes serverless (Vercel, AWS Lambda, etc.)

## Estrutura de Arquivos

```
Portal/
├── index.py                 # Aplicação principal Flask
├── app.py                   # Entrypoint para ambientes serverless
├── requirements.txt         # Dependências Python
├── README.md               # Este arquivo
├── vercel.json             # Configuração Vercel
├── horas_trabalho.json     # Dados (criado automaticamente)
└── templates/              # Templates HTML
    ├── base.html           # Template base
    ├── index.html          # Página inicial
    ├── adicionar_funcionario.html
    ├── registrar_horas.html
    ├── funcionario.html    # Detalhes do funcionário
    └── relatorio_mensal.html
```

## Personalização

Para alterar configurações como porta ou chave secreta, edite as linhas no final do arquivo `index.py`:

```python
app.secret_key = 'sua_chave_secreta_aqui'  # Altere para maior segurança
app.run(debug=True, host='0.0.0.0', port=5000)  # Altere a porta se necessário
```

## Segurança

- Para uso em produção, altere a `secret_key` no código
- Configure um servidor web adequado (nginx, Apache)
- Use HTTPS para conexões seguras
- Faça backup regular do arquivo `horas_trabalho.json`
- Em ambientes serverless, use variáveis de ambiente para armazenamento seguro

## Atualizações Recentes

- ✅ **Compatibilidade Serverless**: Removida dependência de `@app.before_first_request` para suportar ambientes serverless
- ✅ **Inicialização Segura**: Banco de dados inicializado na primeira requisição
- ✅ **Validação de Endpoints**: Adicionadas verificações `has_endpoint` para evitar erros em environments com endpoints faltantes
- ✅ **Diagnóstico**: Endpoint `/_routes` disponível para listar rotas registradas
- ✅ **Correção de Dependencies**: `requirements.txt` otimizado para instalação correta

## Suporte

Sistema desenvolvido para controle interno de horas trabalhadas.
Interface intuitiva e cálculos automáticos conforme legislação trabalhista brasileira.

Para relatórios de bugs ou sugestões, abra uma issue no repositório.
