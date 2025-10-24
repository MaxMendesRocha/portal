# 💰 Cálculo Avulso - Documentação

## 📋 Visão Geral

A funcionalidade **Cálculo Avulso** permite calcular rapidamente o valor a ser pago a um funcionário com base na quantidade de horas trabalhadas e um percentual de pagamento (50% ou 100%).

Esta é uma ferramenta auxiliar que **NÃO interfere** nos registros do sistema, sendo utilizada apenas para obter valores de forma rápida e prática.

---

## 🎯 Objetivo

Facilitar o cálculo de pagamentos avulsos, como:
- Horas extras pagas com acréscimo de 50%
- Horas extras pagas com acréscimo de 100%
- Períodos de trabalho parcial (meio período = 50%)
- Períodos de trabalho completo (período integral = 100%)

---

## 🚀 Como Acessar

### Opção 1: Menu de Navegação
1. No menu superior, clique em **"Cálculo Avulso"**

### Opção 2: Página Inicial
1. Na página inicial, localize o card **"Cálculo Avulso"**
2. Clique no botão **"Calcular Valor"**

**URL Direta:** `http://127.0.0.1:5001/calculo_avulso`

---

## 📝 Como Usar

### Passo 1: Selecionar Funcionário
- Escolha o funcionário na lista suspensa
- O sistema mostrará automaticamente o valor da hora base do funcionário

### Passo 2: Informar Quantidade de Horas
- Digite a quantidade de horas a serem pagas
- Use **ponto** para decimais (Ex: 8.5 para 8 horas e 30 minutos)
- Exemplos válidos:
  - `8` = 8 horas
  - `8.5` = 8 horas e 30 minutos
  - `2.25` = 2 horas e 15 minutos

### Passo 3: Escolher o Percentual

#### 50% - Meio Período / Hora Extra 50%
- Usado para:
  - Trabalho em meio período
  - Horas extras pagas com acréscimo de 50% sobre o valor normal
  - Cálculo: `Valor da Hora × 0,5`

#### 100% - Período Completo / Hora Extra 100%
- Usado para:
  - Trabalho em período completo
  - Horas extras pagas com acréscimo de 100% (dobro)
  - Cálculo: `Valor da Hora × 1,0`

### Passo 4: Calcular
- Clique no botão **"Calcular Valor"**
- O resultado será exibido com todos os detalhes

---

## 📊 Resultado do Cálculo

O sistema exibirá:

### Informações do Cálculo
- **Funcionário:** Nome do funcionário selecionado
- **Quantidade de Horas:** Total de horas informadas
- **Valor da Hora Base:** Valor cadastrado para o funcionário
- **Percentual Aplicado:** 50% ou 100%
- **Valor da Hora Calculado:** Valor após aplicar o percentual
- **VALOR TOTAL:** Valor final a ser pago (destaque em verde)

### Fórmula
```
Valor Total = Quantidade de Horas × (Valor da Hora Base × Percentual)
```

---

## 💡 Exemplos Práticos

### Exemplo 1: Hora Extra com 50% de Acréscimo
- **Funcionário:** Maria Silva
- **Valor da Hora:** R$ 20,00
- **Horas trabalhadas:** 3 horas
- **Percentual:** 50%

**Cálculo:**
- Valor da hora com 50%: R$ 20,00 × 0,5 = R$ 10,00
- Valor total: 3h × R$ 10,00 = **R$ 30,00**

### Exemplo 2: Hora Extra com 100% de Acréscimo
- **Funcionário:** João Santos
- **Valor da Hora:** R$ 25,00
- **Horas trabalhadas:** 5 horas
- **Percentual:** 100%

**Cálculo:**
- Valor da hora com 100%: R$ 25,00 × 1,0 = R$ 25,00
- Valor total: 5h × R$ 25,00 = **R$ 125,00**

### Exemplo 3: Meio Período
- **Funcionário:** Ana Costa
- **Valor da Hora:** R$ 30,00
- **Horas trabalhadas:** 4.5 horas (4h30min)
- **Percentual:** 50%

**Cálculo:**
- Valor da hora com 50%: R$ 30,00 × 0,5 = R$ 15,00
- Valor total: 4.5h × R$ 15,00 = **R$ 67,50**

---

## 🔍 Prévia em Tempo Real

Ao preencher o formulário, o sistema mostra uma **prévia do cálculo** antes de clicar em "Calcular":

- Atualiza automaticamente conforme você digita
- Mostra todos os valores intermediários
- Facilita a conferência antes de confirmar

---

## ⚠️ Observações Importantes

### ✅ O que esta funcionalidade FAZ:
- Calcula valores de pagamento baseado em horas e percentual
- Usa o valor da hora cadastrado no sistema
- Mostra resultado detalhado e formatado

### ❌ O que esta funcionalidade NÃO FAZ:
- **Não registra** as horas no sistema
- **Não afeta** os relatórios mensais
- **Não gera** histórico ou banco de dados
- **Não interfere** nos registros de ponto existentes

### 💡 Quando Usar:
- Para calcular pagamentos avulsos rapidamente
- Para simular cenários de pagamento
- Para conferir valores antes de fazer lançamentos oficiais
- Para calcular horas extras não registradas no sistema

---

## 🛠️ Detalhes Técnicos

### Rota Backend
```python
@app.route('/calculo_avulso', methods=['GET', 'POST'])
def calculo_avulso():
    # Busca funcionário ativo
    # Calcula valor baseado no percentual
    # Retorna resultado formatado
```

### Template HTML
- **Arquivo:** `templates/calculo_avulso.html`
- **Framework CSS:** Bootstrap 5.1.3
- **JavaScript:** Cálculo de prévia em tempo real
- **Responsivo:** Funciona em desktop, tablet e mobile

### Validações
- Funcionário deve estar ativo no sistema
- Quantidade de horas deve ser maior que zero
- Percentual deve ser 50% ou 100%
- Todos os campos são obrigatórios

---

## 🎨 Interface

### Cores e Ícones
- **Card Principal:** Azul (primary)
- **Botão Calcular:** Azul (primary)
- **Resultado:** Verde (success) com destaque
- **Ícones Font Awesome:** calculator, user, clock, percent, etc.

### Responsividade
- Desktop: Layout em 2 colunas
- Tablet: Layout adaptável
- Mobile: Layout em 1 coluna

---

## 📱 Acesso Móvel

A página funciona perfeitamente em dispositivos móveis:
- Formulário otimizado para toque
- Teclado numérico ao digitar horas
- Botões grandes para fácil seleção
- Resultado em formato legível

---

## 🔄 Fluxo de Uso

```
1. Acessar página "Cálculo Avulso"
   ↓
2. Selecionar Funcionário
   ↓
3. Informar Quantidade de Horas
   ↓
4. Escolher Percentual (50% ou 100%)
   ↓
5. Visualizar Prévia (opcional)
   ↓
6. Clicar em "Calcular Valor"
   ↓
7. Ver Resultado Detalhado
   ↓
8. Fazer Novo Cálculo (se necessário)
```

---

## 📞 Suporte

Para dúvidas ou problemas:
1. Verifique se o funcionário está cadastrado e ativo
2. Confirme se o valor da hora está correto no cadastro
3. Certifique-se de usar ponto (.) para decimais

---

## 📅 Histórico de Versões

### v1.0 - 24/10/2025
- ✅ Criação da funcionalidade de Cálculo Avulso
- ✅ Interface responsiva com Bootstrap
- ✅ Cálculo em tempo real (prévia)
- ✅ Suporte para percentuais de 50% e 100%
- ✅ Integração com cadastro de funcionários
- ✅ Adicionado ao menu de navegação
- ✅ Card na página inicial

---

## 🎓 Dicas de Uso

1. **Use a prévia:** Confira o valor antes de calcular oficialmente
2. **Decimais precisos:** Use até 2 casas decimais para maior precisão
3. **Conferência:** Sempre confira o valor da hora do funcionário antes
4. **Impressão:** Use Ctrl+P para imprimir o resultado do cálculo
5. **Múltiplos cálculos:** Faça quantos cálculos precisar, não há limite

---

**Desenvolvido para o Portal de Controle de Horas** 🕐
