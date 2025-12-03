"""
Servidor do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores

Este arquivo implementa o SERVIDOR que aceita múltiplas conexões TCP.
Gerencia o jogo, pontos, ranking e broadcast de mensagens.
"""

import socket              # Biblioteca para comunicação via sockets TCP/IP
import threading           # Para gerenciar múltiplos clientes simultaneamente
import random              # Para gerar número secreto aleatório
import time                # Para pausas entre rodadas
from datetime import datetime  # Para exibir horário de eventos

class ServidorJogo:
    """
    Classe que representa o servidor do jogo.
    Gerencia múltiplos clientes, lógica do jogo e pontuação.
    """
    
    def __init__(self, host='127.0.0.1', porta=5555):
        """
        Inicializa o servidor com configurações de rede e jogo.
        
        Args:
            host: IP para escutar conexões (padrão: localhost)
            porta: Porta TCP para escutar (padrão: 5555)
        """
        self.host = host                    # IP do servidor
        self.porta = porta                  # Porta TCP
        self.servidor_socket = None         # Socket servidor (listen)
        self.clientes = []                  # Lista de dicionários com dados dos clientes
        self.clientes_lock = threading.Lock()  # Lock para acesso thread-safe à lista
        
        # ========== Controle do jogo ==========
        self.numero_secreto = None          # Número que os jogadores devem adivinhar
        self.rodada = 0                     # Contador de rodadas
        self.tentativas_rodada = {}         # {nome_jogador: número_tentativas}
        self.jogo_ativo = False             # Flag se o jogo está em andamento
        
    def iniciar_servidor(self):
        """
        Inicializa o servidor TCP e começa a aceitar conexões de clientes.
        Este método roda em loop infinito aguardando novos jogadores.
        """
        # Cria socket TCP/IP (AF_INET = IPv4, SOCK_STREAM = TCP)
        self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # SO_REUSEADDR permite reusar porta imediatamente após fechar servidor
        # (sem isso, precisa esperar alguns minutos para reusar a porta)
        self.servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            # Associa o socket ao endereço e porta (bind)
            self.servidor_socket.bind((self.host, self.porta))
            
            # Coloca o socket em modo de escuta (listen)
            # Parâmetro 5 = máximo de 5 conexões na fila de espera
            self.servidor_socket.listen(5)
            
            # Exibe informações de inicialização
            print(f"=== Servidor iniciado em {self.host}:{self.porta} ===" )
            print(f"[HORA] {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50)
            print("Aguardando conexões de jogadores...\n")
            
            # Inicia primeira rodada do jogo
            self.nova_rodada()
            
            # ========== LOOP PRINCIPAL - ACEITA NOVOS CLIENTES ==========
            while True:
                # accept() bloqueia até um cliente conectar (handshake TCP)
                # Retorna: (socket do cliente, (ip, porta) do cliente)
                cliente_socket, endereco = self.servidor_socket.accept()
                print(f"[CONEXAO] Nova conexão de {endereco}")
                
                # Cria uma thread dedicada para cada cliente
                # Isso permite gerenciar múltiplos jogadores simultaneamente
                thread_cliente = threading.Thread(
                    target=self.manipular_cliente,
                    args=(cliente_socket, endereco)
                )
                thread_cliente.daemon = True  # Thread morre quando programa termina
                thread_cliente.start()        # Inicia thread em paralelo
                
        except Exception as e:
            print(f"[ERRO] Erro no servidor: {e}")
        finally:
            self.fechar_servidor()
    
    def manipular_cliente(self, cliente_socket, endereco):
        """
        Gerencia a comunicação com um cliente específico.
        Cada cliente roda em sua própria thread.
        
        Args:
            cliente_socket: Socket TCP do cliente
            endereco: Tupla (ip, porta) do cliente
        """
        nome_cliente = None
        
        try:
            # ========== PROTOCOLO DE REGISTRO ==========
            # Envia solicitação de nome ao cliente
            cliente_socket.send("NOME_REQUEST".encode('utf-8'))
            
            # Aguarda resposta com o nome
            nome_cliente = cliente_socket.recv(1024).decode('utf-8').strip()
            
            # Se não enviou nome, gera um automático
            if not nome_cliente:
                nome_cliente = f"Jogador_{endereco[1]}"  # Usa porta como ID
            
            # ========== ADICIONA CLIENTE À LISTA ==========
            # Lock garante que apenas uma thread modifica a lista por vez
            with self.clientes_lock:
                self.clientes.append({
                    'socket': cliente_socket,
                    'endereco': endereco,
                    'nome': nome_cliente,
                    'pontos': 0  # Começa com zero pontos
                })
            
            print(f"[OK] {nome_cliente} entrou no jogo! ({endereco})")
            
            # ========== MENSAGEM DE BOAS-VINDAS ==========
            # Envia informações iniciais do jogo para o novo jogador
            mensagem_boas_vindas = (
                f"\n{'='*50}\n"
                f"=== Bem-vindo ao NÚMERO MISTERIOSO ONLINE! ===\n"
                f"{'='*50}\n"
                f"Jogador: {nome_cliente}\n"
                f"Rodada atual: {self.rodada}\n"
                f"Número secreto: 1-100\n"
                f"Digite seu palpite e pressione ENTER!\n"
                f"{'='*50}\n"
            )
            cliente_socket.send(mensagem_boas_vindas.encode('utf-8'))
            
            # ========== BROADCAST DE ENTRADA ==========
            # Notifica todos os outros jogadores que alguém entrou
            self.broadcast(f">>> {nome_cliente} entrou no jogo!", excluir=cliente_socket)
            
            # ========== LOOP DE RECEBIMENTO DE PALPITES ==========
            while True:
                # Aguarda palpite do cliente (bloqueia até receber)
                dados = cliente_socket.recv(1024).decode('utf-8').strip()
                
                # Se recv() retorna vazio, cliente desconectou
                if not dados:
                    break
                
                # Processa o palpite enviado
                self.processar_palpite(cliente_socket, nome_cliente, dados)
                
        except Exception as e:
            # Erro de comunicação (cliente desconectou inesperadamente, etc)
            print(f"[ERRO] Erro com {nome_cliente or endereco}: {e}")
            
        finally:
            # ========== LIMPEZA AO DESCONECTAR ==========
            # Remove cliente da lista (thread-safe com lock)
            with self.clientes_lock:
                self.clientes = [c for c in self.clientes if c['socket'] != cliente_socket]
            
            # Fecha socket do cliente
            cliente_socket.close()
            print(f"[DESCONECTADO] {nome_cliente or endereco} desconectou")
            
            # Notifica outros jogadores
            if nome_cliente:
                self.broadcast(f">>> {nome_cliente} saiu do jogo!")
    
    def processar_palpite(self, cliente_socket, nome_cliente, palpite_str):
        """
        Processa e valida o palpite de um jogador.
        Verifica se acertou, está alto ou baixo.
        
        Args:
            cliente_socket: Socket do cliente que enviou
            nome_cliente: Nome do jogador
            palpite_str: String com o número (ex: "50")
        """
        try:
            # Converte string para inteiro
            palpite = int(palpite_str)
            
            # ========== VALIDAÇÃO DO PALPITE ==========
            if palpite < 1 or palpite > 100:
                cliente_socket.send("[AVISO] Número deve estar entre 1 e 100!\n".encode('utf-8'))
                return
            
            # ========== REGISTRA TENTATIVA ==========
            # Conta quantas tentativas o jogador já fez nesta rodada
            if nome_cliente not in self.tentativas_rodada:
                self.tentativas_rodada[nome_cliente] = 0
            self.tentativas_rodada[nome_cliente] += 1
            
            # Log no servidor
            print(f"[PALPITE] {nome_cliente} chutou: {palpite}")
            
            # ========== VERIFICA O PALPITE ==========
            if palpite == self.numero_secreto:
                # ========== ACERTOU! ==========
                # Sistema de pontuação: menos tentativas = mais pontos
                # Máximo 10 pontos (acertar de primeira), mínimo 1 ponto
                pontos_ganhos = max(10 - self.tentativas_rodada[nome_cliente], 1)
                
                # ========== ATUALIZA PONTUAÇÃO ==========
                # Busca o jogador na lista e adiciona pontos (thread-safe)
                with self.clientes_lock:
                    for cliente in self.clientes:
                        if cliente['nome'] == nome_cliente:
                            cliente['pontos'] += pontos_ganhos
                            break
                
                # ========== MENSAGEM DE VITÓRIA ==========
                # Envia feedback personalizado para quem acertou
                mensagem_vitoria = (
                    f"\n{'='*50}\n"
                    f"=== PARABÉNS! Você ACERTOU! ===\n"
                    f"Número secreto: {self.numero_secreto}\n"
                    f"Tentativas: {self.tentativas_rodada[nome_cliente]}\n"
                    f"Pontos ganhos: +{pontos_ganhos}\n"
                    f"{'='*50}\n"
                )
                cliente_socket.send(mensagem_vitoria.encode('utf-8'))
                
                # ========== BROADCAST DE VITÓRIA ==========
                # Notifica TODOS os jogadores que alguém acertou
                self.broadcast(
                    f"\n>>> {nome_cliente} ACERTOU o número {self.numero_secreto}! "
                    f"({self.tentativas_rodada[nome_cliente]} tentativas)\n"
                )
                
                # ========== NOVA RODADA ==========
                # Aguarda 3 segundos para jogadores lerem a mensagem
                time.sleep(3)
                # Inicia nova rodada com novo número secreto
                self.nova_rodada()
                
            elif palpite < self.numero_secreto:
                # ========== PALPITE MUITO BAIXO ==========
                resposta = f"[BAIXO] Muito BAIXO! Tentativa {self.tentativas_rodada[nome_cliente]}\n"
                cliente_socket.send(resposta.encode('utf-8'))
                
                # Notifica outros jogadores (sem revelar o número exato)
                self.broadcast(
                    f"... {nome_cliente} chutou um número... (tentativa {self.tentativas_rodada[nome_cliente]})",
                    excluir=cliente_socket
                )
                
            else:  # palpite > numero_secreto
                # ========== PALPITE MUITO ALTO ==========
                resposta = f"[ALTO] Muito ALTO! Tentativa {self.tentativas_rodada[nome_cliente]}\n"
                cliente_socket.send(resposta.encode('utf-8'))
                
                # Notifica outros jogadores (sem revelar o número exato)
                self.broadcast(
                    f"... {nome_cliente} chutou um número... (tentativa {self.tentativas_rodada[nome_cliente]})",
                    excluir=cliente_socket
                )
                
        except ValueError:
            # Cliente enviou algo que não é número (ex: "abc")
            cliente_socket.send("[ERRO] Digite apenas números!\n".encode('utf-8'))
    
    def nova_rodada(self):
        """
        Inicia uma nova rodada do jogo.
        Gera novo número secreto, reseta tentativas e envia ranking.
        """
        # ========== ATUALIZA ESTADO DO JOGO ==========
        self.rodada += 1                           # Incrementa contador de rodadas
        self.numero_secreto = random.randint(1, 100)  # Gera novo número aleatório
        self.tentativas_rodada = {}                # Zera contadores de tentativas
        self.jogo_ativo = True                     # Marca jogo como ativo
        
        # ========== LOG NO SERVIDOR ==========
        # Mostra o número secreto no console do servidor (para debug/acompanhamento)
        print(f"\n[NOVA RODADA] Rodada {self.rodada}")
        print(f"[NUMERO] Número secreto: {self.numero_secreto}")
        print("=" * 50)
        
        # ========== BROADCAST PARA TODOS OS JOGADORES ==========
        # Gera ranking atualizado
        ranking = self.gerar_ranking()
        
        # Monta mensagem com informações da nova rodada
        mensagem = (
            f"\n{'='*50}\n"
            f"=== NOVA RODADA {self.rodada} ===\n"
            f"{'='*50}\n"
            f"{ranking}\n"
            f"Adivinhe o número entre 1 e 100!\n"
            f"{'='*50}\n"
        )
        
        # Envia para todos os clientes conectados
        self.broadcast(mensagem)
    
    def gerar_ranking(self):
        """
        Gera o ranking formatado dos jogadores por pontuação.
        
        Returns:
            str: String formatada com o ranking
        """
        with self.clientes_lock:  # Thread-safe
            # Verifica se há jogadores
            if not self.clientes:
                return "Nenhum jogador online"
            
            # ========== ORDENAÇÃO POR PONTOS ==========
            # Ordena lista de clientes por pontos (decrescente)
            # key=lambda x: x['pontos'] = critério de ordenação
            # reverse=True = maior para menor
            ranking_ordenado = sorted(self.clientes, key=lambda x: x['pontos'], reverse=True)
            
            # ========== FORMATA RANKING ==========
            ranking_texto = "=== RANKING ===\n"
            
            # Percorre jogadores e adiciona medalha para top 3
            for i, cliente in enumerate(ranking_ordenado, 1):
                # Prefixos especiais para os 3 primeiros
                prefixo = "[1º]" if i == 1 else "[2º]" if i == 2 else "[3º]" if i == 3 else "    "
                ranking_texto += f"{prefixo} {i}º {cliente['nome']}: {cliente['pontos']} pontos\n"
            
            return ranking_texto
    
    def broadcast(self, mensagem, excluir=None):
        """
        Envia uma mensagem para TODOS os clientes conectados.
        Implementa comunicação broadcast (1 para muitos).
        
        Args:
            mensagem: String a ser enviada
            excluir: Socket que NÃO deve receber (opcional)
        """
        with self.clientes_lock:  # Thread-safe
            # Percorre todos os clientes conectados
            for cliente in self.clientes:
                # Pula o cliente "excluir" se especificado
                # (útil para não enviar mensagem para quem gerou o evento)
                if excluir and cliente['socket'] == excluir:
                    continue
                    
                try:
                    # Envia mensagem via TCP
                    cliente['socket'].send(mensagem.encode('utf-8'))
                except:
                    # Se falhar, apenas ignora (cliente pode ter desconectado)
                    pass
    
    def fechar_servidor(self):
        """
        Encerra o servidor e fecha todas as conexões de forma limpa.
        Libera recursos de rede.
        """
        print("\n🛑 Encerrando servidor...")
        
        # ========== FECHA TODAS AS CONEXÕES DE CLIENTES ==========
        with self.clientes_lock:
            for cliente in self.clientes:
                try:
                    # Fecha cada socket de cliente individualmente
                    cliente['socket'].close()
                except:
                    # Ignora erros (socket já pode estar fechado)
                    pass
        
        # ========== FECHA SOCKET DO SERVIDOR ==========
        if self.servidor_socket:
            self.servidor_socket.close()  # Libera a porta
        
        print("[OK] Servidor encerrado!")


# ============================================================================
# BLOCO PRINCIPAL - Executa quando arquivo é rodado diretamente
# ============================================================================
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   === NÚMERO MISTERIOSO - SERVIDOR ===          ║
    ║   Trabalho de Redes de Computadores          ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # ========== CONFIGURAÇÕES DE REDE ==========
    HOST = '127.0.0.1'  # Localhost - apenas conexões locais
    PORTA = 5555        # Porta TCP padrão do jogo
    
    # Para aceitar conexões de outras máquinas na rede:
    # HOST = '0.0.0.0'  # Escuta em TODOS os IPs da máquina
    
    # ========== CRIAÇÃO E INICIALIZAÇÃO DO SERVIDOR ==========
    servidor = ServidorJogo(HOST, PORTA)
    
    try:
        # Inicia servidor (loop infinito aguardando clientes)
        servidor.iniciar_servidor()
        
    except KeyboardInterrupt:
        # Usuário pressionou Ctrl+C
        print("\n\n[AVISO] Servidor interrompido pelo usuário")
        servidor.fechar_servidor()
