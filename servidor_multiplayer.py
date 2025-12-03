"""
Servidor Multiplayer do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores

Funcionalidades:
- Sistema de Salas (múltiplas salas independentes)
- Multiplayer competitivo (vários jogadores por sala)
- Servidor de Chat UDP paralelo
- Ranking em tempo real
- Broadcast de eventos
"""

import socket
import threading
import random
import time
import json
from datetime import datetime

class Sala:
    """
    CLASSE SALA - Representa uma sala de jogo onde múltiplos jogadores competem
    
    Esta classe gerencia:
    - Lista de jogadores conectados na sala
    - Número secreto que os jogadores devem adivinhar
    - Contagem de rodadas
    - Ranking de pontuação
    """
    
    def __init__(self, nome, id_sala, criador):
        """
        CONSTRUTOR DA SALA
        Inicializa uma nova sala de jogo
        
        Parâmetros:
            nome: Nome da sala (ex: "Sala Principal")
            id_sala: Identificador único da sala (número)
            criador: Nome do jogador que criou a sala
        """
        self.nome = nome                                    # Nome da sala
        self.id = id_sala                                   # ID único para identificar a sala
        self.criador = criador                              # Quem criou a sala
        self.jogadores = []                                 # Lista de jogadores (cada um é um dicionário)
        self.numero_secreto = random.randint(1, 100)       # Número que os jogadores devem adivinhar
        self.rodada = 1                                     # Contador de rodadas
        self.tentativas = {}                                # Dicionário para contar tentativas de cada jogador
        self.max_jogadores = 10                             # Máximo de jogadores permitidos na sala
        self.lock = threading.Lock()                        # Lock para evitar condições de corrida (thread safety)
        
    def adicionar_jogador(self, cliente_info):
        """
        ADICIONAR JOGADOR À SALA
        Tenta adicionar um novo jogador na sala
        
        Parâmetros:
            cliente_info: Dicionário com dados do jogador (nome, socket, pontos, etc)
        
        Retorna:
            True se conseguiu adicionar, False se a sala está cheia
        """
        with self.lock:  # Usa lock para garantir que apenas uma thread modifique a lista por vez
            if len(self.jogadores) < self.max_jogadores:  # Verifica se há espaço
                self.jogadores.append(cliente_info)        # Adiciona o jogador
                return True
            return False  # Sala cheia
    
    def remover_jogador(self, cliente_socket):
        """
        REMOVER JOGADOR DA SALA
        Remove um jogador que desconectou
        
        Parâmetros:
            cliente_socket: Socket do cliente a ser removido
        """
        with self.lock:  # Thread safety
            # Filtra a lista mantendo apenas jogadores diferentes do que será removido
            self.jogadores = [j for j in self.jogadores if j['socket'] != cliente_socket]
    
    def nova_rodada(self):
        """
        INICIAR NOVA RODADA
        Cria uma nova rodada do jogo com novo número secreto
        
        O que acontece:
        1. Incrementa o contador de rodadas
        2. Gera novo número aleatório entre 1 e 100
        3. Reseta o contador de tentativas de todos
        """
        with self.lock:  # Thread safety
            self.rodada += 1                                # Incrementa número da rodada
            self.numero_secreto = random.randint(1, 100)    # Gera novo número secreto
            self.tentativas = {}                            # Reseta tentativas (dicionário vazio)
            print(f"[NOVA RODADA] Sala '{self.nome}' - Rodada {self.rodada} - Número: {self.numero_secreto}")
    
    def gerar_ranking(self):
        """
        GERAR RANKING DA SALA
        Cria uma string formatada com o ranking de todos os jogadores
        
        Retorna:
            String com o ranking formatado (1º, 2º, 3º, etc)
        """
        with self.lock:  # Thread safety
            if not self.jogadores:  # Se não há jogadores
                return "Nenhum jogador na sala"
            
            # Ordena jogadores por pontos (do maior para o menor)
            ranking = sorted(self.jogadores, key=lambda x: x['pontos'], reverse=True)
            
            # Monta o texto do ranking
            texto = f"=== RANKING - Sala '{self.nome}' ===\n"
            for i, jogador in enumerate(ranking, 1):  # enumerate começa em 1
                # Define prefixo especial para os 3 primeiros
                prefixo = "[1º]" if i == 1 else "[2º]" if i == 2 else "[3º]" if i == 3 else "    "
                texto += f"{prefixo} {i}º {jogador['nome']}: {jogador['pontos']} pontos\n"
            return texto
    
    def broadcast(self, mensagem, excluir=None):
        """
        BROADCAST (TRANSMISSÃO PARA TODOS)
        Envia uma mensagem para todos os jogadores da sala
        
        Parâmetros:
            mensagem: Texto a ser enviado
            excluir: Socket do jogador que NÃO deve receber (opcional)
        
        Explicação do Broadcast:
            Broadcast significa "transmitir para todos". É como um megafone
            que anuncia algo para todos os jogadores da sala ao mesmo tempo.
        """
        with self.lock:  # Thread safety
            for jogador in self.jogadores:  # Para cada jogador na sala
                # Se excluir foi especificado e é este jogador, pula
                if excluir and jogador['socket'] == excluir:
                    continue
                try:
                    # Envia a mensagem via TCP para o socket do jogador
                    jogador['socket'].send(mensagem.encode('utf-8'))
                except:
                    # Se der erro (jogador desconectou), ignora
                    pass


class ServidorChatUDP:
    """
    SERVIDOR DE CHAT UDP
    Gerencia o sistema de chat usando protocolo UDP (paralelo ao jogo TCP)
    
    POR QUE UDP PARA CHAT?
    - UDP é mais rápido que TCP (não espera confirmação)
    - Para chat, se uma mensagem se perder não é crítico
    - Demonstra o uso de DOIS protocolos diferentes no mesmo sistema
    
    DIFERENÇA TCP vs UDP:
    TCP: Confiável, garante entrega, em ordem (usado no JOGO)
    UDP: Rápido, sem garantia, pode perder pacotes (usado no CHAT)
    """
    
    def __init__(self, host='127.0.0.1', porta=5556):
        """
        CONSTRUTOR DO CHAT UDP
        
        Parâmetros:
            host: IP do servidor (127.0.0.1 = localhost)
            porta: Porta UDP para o chat (5556)
        """
        self.host = host                      # IP onde o servidor UDP vai rodar
        self.porta = porta                    # Porta do servidor UDP
        self.socket_udp = None                # Socket UDP (será criado no iniciar)
        self.clientes_udp = {}                # Dicionário: {nome_cliente: (ip, porta)}
        self.lock = threading.Lock()          # Lock para thread safety
        
    def iniciar(self):
        """
        INICIAR SERVIDOR UDP
        Cria o socket UDP e começa a escutar mensagens
        
        ETAPAS:
        1. Cria socket UDP (SOCK_DGRAM = datagrama)
        2. Faz bind (vincula) no IP e porta
        3. Inicia thread para receber mensagens continuamente
        """
        try:
            # SOCK_DGRAM = UDP (diferente de SOCK_STREAM que é TCP)
            self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Vincula o socket ao endereço (IP e porta)
            self.socket_udp.bind((self.host, self.porta))
            print(f"[CHAT] Chat UDP iniciado em {self.host}:{self.porta}")
            
            # Cria thread para receber mensagens em paralelo
            thread = threading.Thread(target=self.receber_mensagens)
            thread.daemon = True  # Thread daemon = termina quando o programa principal termina
            thread.start()
            
        except Exception as e:
            print(f"[ERRO] Erro ao iniciar chat UDP: {e}")
    
    def receber_mensagens(self):
        """
        RECEBER MENSAGENS UDP (Loop Infinito)
        Thread que fica rodando continuamente esperando mensagens UDP
        
        COMO FUNCIONA UDP:
        - Cliente envia pacote UDP para o servidor
        - Servidor recebe e processa
        - Não há "conexão" estabelecida (diferente do TCP)
        """
        while True:  # Loop infinito - sempre esperando mensagens
            try:
                # recvfrom = recebe dados UDP
                # Retorna: (dados recebidos, endereço de quem enviou)
                dados, endereco = self.socket_udp.recvfrom(4096)  # Buffer de 4KB
                mensagem = dados.decode('utf-8')  # Converte bytes para string
                
                # PROCESSA MENSAGEM JSON
                # Usamos JSON para estruturar as mensagens do chat
                try:
                    msg_json = json.loads(mensagem)  # Converte JSON para dicionário Python
                    tipo = msg_json.get('tipo', '')   # Pega o tipo da mensagem
                    
                    if tipo == 'REGISTRO':
                        """
                        TIPO: REGISTRO
                        Cliente se registrando no chat pela primeira vez
                        """
                        nome = msg_json.get('nome', '')
                        with self.lock:  # Thread safety
                            # Salva o endereço do cliente para enviar mensagens depois
                            self.clientes_udp[nome] = endereco
                        print(f"[CHAT] {nome} registrado no chat UDP de {endereco}")
                        
                        # CONFIRMA REGISTRO ao cliente
                        resposta = json.dumps({'tipo': 'CONFIRMACAO', 'mensagem': 'Registrado no chat!'})
                        self.socket_udp.sendto(resposta.encode('utf-8'), endereco)
                        
                    elif tipo == 'MENSAGEM':
                        """
                        TIPO: MENSAGEM
                        Cliente enviou uma mensagem de chat
                        Fazemos BROADCAST (envia para TODOS)
                        """
                        nome = msg_json.get('nome', 'Anônimo')   # Nome de quem enviou
                        texto = msg_json.get('texto', '')         # Texto da mensagem
                        sala = msg_json.get('sala', 'Geral')      # Sala de origem
                        
                        print(f"[CHAT] [{sala}] {nome}: {texto}")
                        
                        # MONTA MENSAGEM DE BROADCAST
                        msg_broadcast = json.dumps({
                            'tipo': 'CHAT',
                            'nome': nome,
                            'texto': texto,
                            'sala': sala,
                            'timestamp': datetime.now().strftime('%H:%M:%S')  # Hora atual
                        })
                        
                        # ENVIA PARA TODOS OS CLIENTES registrados
                        with self.lock:  # Thread safety
                            for cliente_nome, cliente_end in self.clientes_udp.items():
                                try:
                                    # sendto = envia UDP para um endereço específico
                                    self.socket_udp.sendto(msg_broadcast.encode('utf-8'), cliente_end)
                                except:
                                    # Se falhar, ignora (UDP não garante entrega)
                                    pass
                                    
                except json.JSONDecodeError:
                    # Mensagem não é JSON válido
                    print(f"[AVISO] Mensagem UDP inválida de {endereco}")
                    
            except Exception as e:
                print(f"[ERRO] Erro no chat UDP: {e}")
                break  # Sai do loop se houver erro crítico


class ServidorMultiplayer:
    """
    SERVIDOR MULTIPLAYER PRINCIPAL
    Esta é a classe principal que gerencia TODO o sistema:
    - Servidor TCP para o jogo
    - Servidor UDP para o chat
    - Sistema de salas
    - Conexões dos clientes
    
    ARQUITETURA DO SISTEMA:
    ┌─────────────────────────────────┐
    │  ServidorMultiplayer            │
    │  ├─ Servidor TCP (porta 5555)   │  <- Jogo principal
    │  ├─ Servidor UDP (porta 5556)   │  <- Chat paralelo
    │  └─ Sistema de Salas            │  <- Gerencia múltiplas salas
    └─────────────────────────────────┘
    """
    
    def __init__(self, host='127.0.0.1', porta_tcp=5555, porta_udp=5556):
        """
        CONSTRUTOR DO SERVIDOR MULTIPLAYER
        
        Parâmetros:
            host: IP do servidor (127.0.0.1 = localhost = seu próprio computador)
            porta_tcp: Porta para o jogo (5555)
            porta_udp: Porta para o chat (5556)
        """
        self.host = host                              # IP do servidor
        self.porta_tcp = porta_tcp                    # Porta TCP (jogo)
        self.porta_udp = porta_udp                    # Porta UDP (chat)
        self.servidor_socket = None                   # Socket TCP (será criado depois)
        self.salas = {}                               # Dicionário de salas: {id: objeto Sala}
        self.salas_lock = threading.Lock()            # Lock para thread safety
        self.proximo_id_sala = 1                      # Contador para IDs das salas
        
        # CRIA O SERVIDOR DE CHAT UDP
        self.chat_udp = ServidorChatUDP(host, porta_udp)
        
    def iniciar_servidor(self):
        """
        INICIAR SERVIDOR (Método Principal)
        Este método inicia todo o sistema: TCP, UDP e loop de aceitação de clientes
        
        ETAPAS:
        1. Inicia o servidor UDP (chat)
        2. Cria e configura o socket TCP (jogo)
        3. Entra no loop infinito aguardando conexões
        4. Para cada cliente, cria uma thread separada
        """
        
        # ========== ETAPA 1: INICIA CHAT UDP ==========
        self.chat_udp.iniciar()
        
        # ========== ETAPA 2: CRIA SOCKET TCP ==========
        # SOCK_STREAM = TCP (conexão confiável)
        self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # SO_REUSEADDR = permite reutilizar a porta imediatamente
        # (sem isso, teria que esperar alguns minutos após fechar o servidor)
        self.servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # BIND = vincula o socket ao endereço (IP + porta)
            self.servidor_socket.bind((self.host, self.porta_tcp))
            
            # LISTEN = começa a escutar conexões
            # Parâmetro 10 = tamanho da fila de conexões pendentes
            self.servidor_socket.listen(10)
            
            # Imprime informações do servidor
            print(f"\n{'='*60}")
            print(f"=== Servidor Multiplayer Iniciado! ===")
            print(f"{'='*60}")
            print(f"[TCP] Jogo: {self.host}:{self.porta_tcp}")
            print(f"[UDP] Chat: {self.host}:{self.porta_udp}")
            print(f"[HORA] {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
            print(f"{'='*60}\n")
            print("Aguardando jogadores...\n")
            
            # Cria uma sala padrão automaticamente
            self.criar_sala("Sala Principal", "Sistema")
            
            # ========== ETAPA 3: LOOP PRINCIPAL ==========
            # Loop infinito aguardando conexões de clientes
            while True:
                # ACCEPT = aguarda e aceita uma nova conexão
                # Retorna: (socket do cliente, endereço do cliente)
                # Este método BLOQUEIA até alguém conectar
                cliente_socket, endereco = self.servidor_socket.accept()
                print(f"[CONEXAO] Nova conexão: {endereco}")
                
                # ========== ETAPA 4: CRIA THREAD PARA O CLIENTE ==========
                # Cada cliente roda em sua própria thread
                # Isso permite múltiplos clientes simultâneos
                thread = threading.Thread(
                    target=self.manipular_cliente,  # Função que vai rodar na thread
                    args=(cliente_socket, endereco)  # Argumentos da função
                )
                thread.daemon = True  # Thread daemon = encerra com o programa principal
                thread.start()  # Inicia a thread
                
        except Exception as e:
            print(f"[ERRO] Erro no servidor: {e}")
        finally:
            self.fechar_servidor()
    
    def criar_sala(self, nome_sala, criador):
        """
        CRIAR NOVA SALA
        Cria uma sala de jogo onde jogadores podem entrar e competir
        
        Parâmetros:
            nome_sala: Nome da sala (ex: "Sala VIP")
            criador: Nome do jogador que criou a sala
        
        Retorna:
            Objeto Sala criado
        """
        with self.salas_lock:  # Thread safety ao modificar o dicionário de salas
            # Pega o próximo ID disponível e incrementa o contador
            id_sala = self.proximo_id_sala
            self.proximo_id_sala += 1
            
            # Cria o objeto Sala
            sala = Sala(nome_sala, id_sala, criador)
            
            # Adiciona ao dicionário de salas
            self.salas[id_sala] = sala
            
            print(f"[SALA] Sala '{nome_sala}' criada (ID: {id_sala}) por {criador}")
            return sala
    
    def listar_salas(self):
        """
        LISTAR SALAS DISPONÍVEIS
        Cria uma string formatada com todas as salas e suas informações
        
        Retorna:
            String formatada com lista de salas
        """
        with self.salas_lock:  # Thread safety ao ler o dicionário
            if not self.salas:  # Se não há salas
                return "Nenhuma sala disponível"
            
            texto = "\n=== SALAS DISPONÍVEIS ===\n"
            texto += "=" * 50 + "\n"
            for id_sala, sala in self.salas.items():
                jogadores_count = len(sala.jogadores)
                status = "[LIVRE]" if jogadores_count < sala.max_jogadores else "[CHEIA]"
                texto += f"{status} [{id_sala}] {sala.nome} - {jogadores_count}/{sala.max_jogadores} jogadores\n"
            texto += "=" * 50 + "\n"
            return texto
    
    def manipular_cliente(self, cliente_socket, endereco):
        """
        MANIPULAR CLIENTE (Método CRUCIAL!)
        Esta função roda em uma thread SEPARADA para cada cliente conectado
        
        O QUE FAZ:
        1. Solicita o nome do jogador
        2. Mostra menu de salas (listar, criar, entrar)
        3. Quando jogador entra em uma sala, inicia o jogo
        4. Processa palpites e envia feedback
        
        Parâmetros:
            cliente_socket: Socket TCP do cliente
            endereco: Tupla (IP, porta) do cliente
        
        IMPORTANTE: Esta função é chamada em THREAD para cada cliente!
        """
        nome_cliente = None   # Nome do jogador (será preenchido)
        sala_atual = None     # Sala em que o jogador está (None = no menu)
        
        try:
            # ========== ETAPA 1: SOLICITA NOME DO JOGADOR ==========
            # Envia comando especial "NOME_REQUEST" para o cliente
            cliente_socket.send("NOME_REQUEST".encode('utf-8'))
            
            # Aguarda resposta do cliente (RECV bloqueia até receber)
            nome_cliente = cliente_socket.recv(1024).decode('utf-8').strip()
            
            # Se não recebeu nome, gera um automático
            if not nome_cliente:
                nome_cliente = f"Jogador_{endereco[1]}"  # Usa porta como identificador
            
            print(f"[OK] {nome_cliente} conectado ({endereco})")
            
            # ========== ETAPA 2: MENU DE SALAS (Loop Infinito) ==========
            # O jogador fica neste loop até entrar em uma sala
            while True:
                # Monta o texto do menu
                menu = (
                    f"\n{'='*50}\n"
                    f"=== BEM-VINDO, {nome_cliente}! ===\n"
                    f"{'='*50}\n"
                    f"Escolha uma opção:\n"
                    f"1 - Listar salas disponíveis\n"
                    f"2 - Criar nova sala\n"
                    f"3 - Entrar em uma sala (digite o ID)\n"
                    f"{'='*50}\n"
                    f"Digite sua escolha: "
                )
                # Envia menu para o cliente via TCP
                cliente_socket.send(menu.encode('utf-8'))
                
                # Aguarda escolha do jogador (BLOQUEIA até receber)
                escolha = cliente_socket.recv(1024).decode('utf-8').strip()
                
                # ===== OPÇÃO 1: LISTAR SALAS =====
                if escolha == '1':
                    lista = self.listar_salas()  # Chama método que gera string com salas
                    cliente_socket.send(lista.encode('utf-8'))  # Envia lista ao cliente
                    
                # ===== OPÇÃO 2: CRIAR SALA =====
                elif escolha == '2':
                    # Pede nome da sala
                    cliente_socket.send("Digite o nome da nova sala: ".encode('utf-8'))
                    nome_sala = cliente_socket.recv(1024).decode('utf-8').strip()
                    
                    if nome_sala:  # Se digitou algo
                        sala = self.criar_sala(nome_sala, nome_cliente)  # Cria a sala
                        cliente_socket.send(f"[OK] Sala '{nome_sala}' criada com sucesso! (ID: {sala.id})\n".encode('utf-8'))
                    
                # ===== OPÇÃO 3: ENTRAR EM SALA =====
                elif escolha == '3':
                    # Pede ID da sala
                    cliente_socket.send("Digite o ID da sala: ".encode('utf-8'))
                    id_sala_str = cliente_socket.recv(1024).decode('utf-8').strip()
                    
                    try:
                        id_sala = int(id_sala_str)  # Converte string para número
                        
                        # Busca a sala no dicionário (thread safe)
                        with self.salas_lock:
                            sala_atual = self.salas.get(id_sala)
                        
                        if sala_atual:  # Se a sala existe
                            # ========== ADICIONA JOGADOR À SALA ==========
                            # Cria dicionário com informações do jogador
                            cliente_info = {
                                'socket': cliente_socket,    # Socket TCP para enviar mensagens
                                'endereco': endereco,        # (IP, porta)
                                'nome': nome_cliente,        # Nome do jogador
                                'pontos': 0                  # Pontos iniciais
                            }
                            
                            # Tenta adicionar jogador (retorna False se sala cheia)
                            if sala_atual.adicionar_jogador(cliente_info):
                                # ===== SUCESSO! JOGADOR ENTROU NA SALA =====
                                # Prepara mensagem de boas-vindas
                                msg_entrada = (
                                    f"\n{'='*50}\n"
                                    f"=== Você entrou na sala: {sala_atual.nome} ===\n"
                                    f"{'='*50}\n"
                                    f"Rodada: {sala_atual.rodada}\n"
                                    f"Jogadores: {len(sala_atual.jogadores)}/{sala_atual.max_jogadores}\n"
                                    f"Adivinhe o número entre 1 e 100!\n"
                                    f"[CHAT] Chat UDP disponível na porta {self.porta_udp}\n"
                                    f"{'='*50}\n"
                                )
                                cliente_socket.send(msg_entrada.encode('utf-8'))
                                
                                # Notifica outros jogadores
                                sala_atual.broadcast(
                                    f"\n>>> {nome_cliente} entrou na sala!\n",
                                    excluir=cliente_socket
                                )
                                
                                # Inicia jogo
                                self.jogar(cliente_socket, nome_cliente, sala_atual)
                                break
                            else:
                                cliente_socket.send("[ERRO] Sala cheia!\n".encode('utf-8'))
                        else:
                            cliente_socket.send("[ERRO] Sala não encontrada!\n".encode('utf-8'))
                            
                    except ValueError:
                        cliente_socket.send("[ERRO] ID inválido!\n".encode('utf-8'))
                        
        except Exception as e:
            print(f"[ERRO] Erro com {nome_cliente or endereco}: {e}")
        finally:
            if sala_atual:
                sala_atual.remover_jogador(cliente_socket)
                sala_atual.broadcast(f"\n>>> {nome_cliente} saiu da sala!\n")
            
            cliente_socket.close()
            print(f"[DESCONECTADO] {nome_cliente or endereco} desconectou")
    
    def jogar(self, cliente_socket, nome_cliente, sala):
        """Loop de jogo para um cliente em uma sala"""
        while True:
            try:
                palpite_str = cliente_socket.recv(1024).decode('utf-8').strip()
                
                if not palpite_str:
                    break
                
                if palpite_str.lower() == 'sair':
                    break
                
                # Processa palpite
                try:
                    palpite = int(palpite_str)
                    
                    if palpite < 1 or palpite > 100:
                        cliente_socket.send("[AVISO] Número entre 1 e 100!\n".encode('utf-8'))
                        continue
                    
                    # Registra tentativa
                    if nome_cliente not in sala.tentativas:
                        sala.tentativas[nome_cliente] = 0
                    sala.tentativas[nome_cliente] += 1
                    
                    print(f"[PALPITE] [{sala.nome}] {nome_cliente}: {palpite}")
                    
                    # Verifica acerto
                    if palpite == sala.numero_secreto:
                        # ACERTOU!
                        pontos = max(10 - sala.tentativas[nome_cliente], 1)
                        
                        # Atualiza pontuação
                        with sala.lock:
                            for jogador in sala.jogadores:
                                if jogador['nome'] == nome_cliente:
                                    jogador['pontos'] += pontos
                                    break
                        
                        vitoria = (
                            f"\n{'='*50}\n"
                            f"=== VOCÊ ACERTOU! ===\n"
                            f"Número: {sala.numero_secreto}\n"
                            f"Tentativas: {sala.tentativas[nome_cliente]}\n"
                            f"Pontos: +{pontos}\n"
                            f"{'='*50}\n"
                        )
                        cliente_socket.send(vitoria.encode('utf-8'))
                        
                        # Broadcast
                        sala.broadcast(
                            f"\n>>> {nome_cliente} ACERTOU o número {sala.numero_secreto}! "
                            f"({sala.tentativas[nome_cliente]} tentativas)\n"
                        )
                        
                        time.sleep(3)
                        
                        # Nova rodada
                        sala.nova_rodada()
                        ranking = sala.gerar_ranking()
                        msg_rodada = (
                            f"\n{'='*50}\n"
                            f"=== NOVA RODADA {sala.rodada} ===\n"
                            f"{'='*50}\n"
                            f"{ranking}\n"
                            f"Novo número entre 1 e 100!\n"
                            f"{'='*50}\n"
                        )
                        sala.broadcast(msg_rodada)
                        
                    elif palpite < sala.numero_secreto:
                        resp = f"[BAIXO] Muito BAIXO! (Tentativa {sala.tentativas[nome_cliente]})\n"
                        cliente_socket.send(resp.encode('utf-8'))
                        sala.broadcast(
                            f"... {nome_cliente} fez uma tentativa...\n",
                            excluir=cliente_socket
                        )
                        
                    else:
                        resp = f"[ALTO] Muito ALTO! (Tentativa {sala.tentativas[nome_cliente]})\n"
                        cliente_socket.send(resp.encode('utf-8'))
                        sala.broadcast(
                            f"... {nome_cliente} fez uma tentativa...\n",
                            excluir=cliente_socket
                        )
                        
                except ValueError:
                    cliente_socket.send("[ERRO] Digite apenas números!\n".encode('utf-8'))
                    
            except Exception as e:
                print(f"[ERRO] Erro no jogo: {e}")
                break
    
    def fechar_servidor(self):
        """Fecha o servidor"""
        print("\n[ENCERRANDO] Encerrando servidor...")
        
        with self.salas_lock:
            for sala in self.salas.values():
                sala.broadcast("\n[AVISO] Servidor encerrando...\n")
                with sala.lock:
                    for jogador in sala.jogadores:
                        try:
                            jogador['socket'].close()
                        except:
                            pass
        
        if self.servidor_socket:
            self.servidor_socket.close()
        
        print("[OK] Servidor encerrado!")


if __name__ == "__main__":
    print("""
    ╔══════════════════════════════════════════════════════╗
    ║   === NÚMERO MISTERIOSO - SERVIDOR MULTIPLAYER ===  ║
    ║   Sistema de Salas + Chat UDP                        ║
    ║   Trabalho de Redes de Computadores                  ║
    ╚══════════════════════════════════════════════════════╝
    """)
    
    HOST = '0.0.0.0'  # Aceita conexões de qualquer IP
    PORTA_TCP = 5555  # Porta do jogo (TCP)
    PORTA_UDP = 5556  # Porta do chat (UDP)
    
    servidor = ServidorMultiplayer(HOST, PORTA_TCP, PORTA_UDP)
    
    try:
        servidor.iniciar_servidor()
    except KeyboardInterrupt:
        print("\n\n[INTERROMPIDO] Servidor interrompido")
        servidor.fechar_servidor()
