# 🎮 Número Misterioso Online - Jogo Cliente-Servidor

## 📝 Descrição do Projeto

Jogo multiplayer de adivinhação implementado com sockets TCP em Python para demonstrar conceitos de redes de computadores. Múltiplos jogadores competem em tempo real para adivinhar um número secreto gerado pelo servidor.

## 🎯 Objetivos de Aprendizagem

- **Sockets TCP**: Comunicação confiável entre cliente e servidor
- **Threading**: Gerenciamento de múltiplos clientes simultâneos
- **Protocolo Cliente-Servidor**: Arquitetura de comunicação em rede
- **Broadcasting**: Envio de mensagens para múltiplos clientes
- **Sincronização**: Coordenação de estado entre servidor e clientes

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────┐
│           SERVIDOR (servidor.py)            │
│  - Gerencia conexões TCP                    │
│  - Gera números secretos                    │
│  - Processa palpites                        │
│  - Mantém ranking                           │
│  - Broadcast de eventos                     │
└──────┬──────────┬──────────┬────────────────┘
       │          │          │
   Socket TCP Socket TCP Socket TCP
       │          │          │
    ┌──▼──┐    ┌──▼──┐    ┌──▼──┐
    │ CLI │    │ CLI │    │ CLI │
    │  1  │    │  2  │    │  3  │
    └─────┘    └─────┘    └─────┘
```

## 🚀 Como Executar

### Pré-requisitos
- Python 3.7 ou superior
- Nenhuma biblioteca externa necessária (usa apenas bibliotecas padrão)

### Passo 1: Iniciar o Servidor

Abra um terminal e execute:

```bash
python servidor.py
```

O servidor iniciará na porta **5555** e aguardará conexões.

**Saída esperada:**
```
🎮 Servidor iniciado em 127.0.0.1:5555
⏰ 14:30:25
==================================================
Aguardando conexões de jogadores...

🔄 NOVA RODADA 1
🔐 Número secreto: 42
==================================================
```

### Passo 2: Conectar Clientes

Em **outros terminais** (pode abrir quantos quiser), execute:

```bash
python cliente.py
```

Cada cliente solicitará um nome e então poderá começar a jogar.

**Exemplo de uso:**
```
✅ Conectado ao servidor 127.0.0.1:5555

Digite seu nome de jogador:
👤 Nome: João

==================================================
🎮 Bem-vindo ao NÚMERO MISTERIOSO ONLINE! 🎮
==================================================
Jogador: João
Rodada atual: 1
Número secreto: 1-100
Digite seu palpite e pressione ENTER!
==================================================

💡 Digite seus palpites (números de 1 a 100)
💡 Digite 'sair' para desconectar

50
📉 Muito ALTO! Tentativa 1
30
📈 Muito BAIXO! Tentativa 2
42
🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
🏆 PARABÉNS! Você ACERTOU! 🏆
Número secreto: 42
Tentativas: 3
Pontos ganhos: +7
🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉🎉
```

### Conectar de Outra Máquina

Para jogar em rede local:

1. **No servidor**, altere em `servidor.py`:
   ```python
   HOST = '0.0.0.0'  # Aceita conexões de qualquer IP
   ```

2. **No cliente**, descubra o IP do servidor:
   ```bash
   # Windows
   ipconfig
   
   # Linux/Mac
   ifconfig
   ```

3. Execute o cliente com o IP do servidor:
   ```bash
   python cliente.py 192.168.1.100
   ```

## 🎲 Regras do Jogo

1. **Objetivo**: Adivinhar o número secreto (1-100) gerado pelo servidor
2. **Palpites**: Digite um número e pressione ENTER
3. **Feedback**: 
   - 📈 "Muito BAIXO" - seu palpite é menor que o número
   - 📉 "Muito ALTO" - seu palpite é maior que o número
   - 🎉 "ACERTOU!" - você encontrou o número!
4. **Pontuação**:
   - Menos tentativas = mais pontos
   - Fórmula: `max(10 - tentativas, 1)`
   - 1 tentativa = 9 pontos
   - 2 tentativas = 8 pontos
   - 10+ tentativas = 1 ponto
5. **Rodadas**: Quando alguém acerta, nova rodada começa automaticamente
6. **Ranking**: Atualizado a cada nova rodada

## 🔧 Conceitos Técnicos Implementados

### 1. **Sockets TCP**
```python
# Servidor cria socket e aguarda conexões
servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor_socket.bind((host, porta))
servidor_socket.listen(5)

# Cliente conecta ao servidor
cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente_socket.connect((host, porta))
```

### 2. **Threading para Múltiplos Clientes**
```python
# Cada cliente é tratado em uma thread separada
thread_cliente = threading.Thread(
    target=self.manipular_cliente,
    args=(cliente_socket, endereco)
)
thread_cliente.start()
```

### 3. **Sincronização com Locks**
```python
# Protege acesso concorrente à lista de clientes
with self.clientes_lock:
    self.clientes.append(novo_cliente)
```

### 4. **Broadcasting**
```python
# Envia mensagem para todos os clientes conectados
def broadcast(self, mensagem, excluir=None):
    for cliente in self.clientes:
        if cliente['socket'] != excluir:
            cliente['socket'].send(mensagem.encode('utf-8'))
```

### 5. **Protocolo de Comunicação**
```
Cliente → Servidor: Palpite (número)
Servidor → Cliente: Feedback (muito alto/baixo/acertou)
Servidor → Todos: Broadcast de eventos
```

## 📊 Estrutura de Dados

### Servidor
```python
clientes = [
    {
        'socket': socket_obj,
        'endereco': ('127.0.0.1', 54321),
        'nome': 'João',
        'pontos': 15
    },
    # ... outros clientes
]
```

### Estado do Jogo
```python
{
    'numero_secreto': 42,
    'rodada': 5,
    'tentativas_rodada': {
        'João': 3,
        'Maria': 5
    },
    'jogo_ativo': True
}
```

## 🐛 Tratamento de Erros

O projeto implementa tratamento robusto de erros:

- ✅ **Desconexão inesperada**: Cliente removido automaticamente
- ✅ **Entrada inválida**: Mensagem de erro ao cliente
- ✅ **Timeout**: Sockets configurados para não bloquear indefinidamente
- ✅ **Múltiplos acessos**: Sincronização com locks

## 🎓 Conceitos de Redes Aplicados

| Conceito | Implementação |
|----------|---------------|
| **TCP/IP** | Socket SOCK_STREAM |
| **Cliente-Servidor** | Arquitetura centralizada |
| **Port Binding** | Porta 5555 |
| **Threading** | Múltiplas conexões simultâneas |
| **Broadcasting** | Mensagens para todos os clientes |
| **Estado Compartilhado** | Gerenciamento centralizado no servidor |
| **Protocolo Customizado** | Formato de mensagens definido |

## 🔒 Segurança e Limitações

### Limitações Atuais:
- ❌ Sem criptografia (dados em texto plano)
- ❌ Sem autenticação de usuários
- ❌ Sem proteção contra DoS
- ❌ Sem validação robusta de dados

### Melhorias Possíveis:
- 🔐 Implementar SSL/TLS
- 👤 Sistema de login
- 🛡️ Rate limiting
- 📝 Logs de auditoria
- 💾 Persistência de dados (banco de dados)

## 🧪 Testando o Projeto

### Teste 1: Único Jogador
```bash
# Terminal 1
python servidor.py

# Terminal 2
python cliente.py
```

### Teste 2: Múltiplos Jogadores (Mesma Máquina)
```bash
# Terminal 1
python servidor.py

# Terminais 2, 3, 4, ...
python cliente.py
```

### Teste 3: Rede Local
```bash
# Máquina 1 (Servidor)
python servidor.py

# Máquina 2, 3, 4... (Clientes)
python cliente.py <IP_DO_SERVIDOR>
```

## 📚 Referências e Recursos

- [Python Socket Programming](https://docs.python.org/3/library/socket.html)
- [Threading em Python](https://docs.python.org/3/library/threading.html)
- [Modelo Cliente-Servidor](https://pt.wikipedia.org/wiki/Modelo_cliente-servidor)

## 👨‍💻 Estrutura do Código

### `servidor.py` (Principais métodos)
- `iniciar_servidor()`: Inicia servidor e aceita conexões
- `manipular_cliente()`: Gerencia comunicação com cada cliente
- `processar_palpite()`: Valida e processa palpites
- `nova_rodada()`: Inicia nova rodada do jogo
- `broadcast()`: Envia mensagens para todos
- `gerar_ranking()`: Cria tabela de pontuação

### `cliente.py` (Principais métodos)
- `conectar()`: Estabelece conexão TCP
- `registrar_nome()`: Envia nome ao servidor
- `receber_mensagens()`: Thread para receber dados
- `enviar_mensagens()`: Thread para enviar palpites

## 🎉 Recursos Implementados

- ✅ Múltiplos jogadores simultâneos
- ✅ Sistema de pontuação
- ✅ Ranking em tempo real
- ✅ Broadcast de eventos
- ✅ Rodadas automáticas
- ✅ Feedback detalhado
- ✅ Tratamento de erros
- ✅ Interface colorida com emojis
- ✅ Contagem de tentativas
- ✅ Desconexão graciosa

## 🏆 Diferenciais do Projeto

1. **Código Limpo**: Bem documentado e organizado
2. **Robusto**: Tratamento de exceções e edge cases
3. **Escalável**: Suporta múltiplos clientes
4. **Educacional**: Comentários explicativos
5. **Completo**: Pronto para apresentação

---

**Desenvolvido para Trabalho de Redes de Computadores** 🎓

**Tecnologias**: Python, Sockets TCP, Threading, Protocolo Cliente-Servidor
