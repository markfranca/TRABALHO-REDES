"""
Cliente do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores

Este arquivo implementa o CLIENTE que se conecta ao servidor via TCP.
Permite jogar o jogo pelo terminal/console.
"""

import socket      # Biblioteca para comunicação via sockets TCP/IP
import threading   # Para executar recebimento e envio de mensagens simultaneamente
import sys         # Para argumentos de linha de comando
import os          # Para obter PID do processo

class ClienteJogo:
    """
    Classe que representa o cliente do jogo.
    Gerencia a conexão TCP com o servidor e a comunicação bidirecional.
    """
    
    def __init__(self, host='127.0.0.1', porta=5555):
        """
        Inicializa o cliente com configurações de rede.
        
        Args:
            host: Endereço IP do servidor (padrão: localhost)
            porta: Porta TCP do servidor (padrão: 5555)
        """
        self.host = host                    # IP do servidor
        self.porta = porta                  # Porta TCP do servidor
        self.cliente_socket = None          # Socket TCP (será criado ao conectar)
        self.conectado = False              # Flag de status da conexão
        self.nome = ""                      # Nome do jogador
        
    def conectar(self):
        """
        Estabelece conexão TCP com o servidor do jogo.
        
        Returns:
            bool: True se conectou com sucesso, False caso contrário
        """
        try:
            # Cria um socket TCP/IP (AF_INET = IPv4, SOCK_STREAM = TCP)
            self.cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            
            # Tenta conectar no servidor (handshake TCP de 3 vias acontece aqui)
            self.cliente_socket.connect((self.host, self.porta))
            
            # Marca como conectado
            self.conectado = True
            
            print(f"[OK] Conectado ao servidor {self.host}:{self.porta}\n")
            return True
            
        except Exception as e:
            # Captura erros como servidor offline, porta errada, etc.
            print(f"[ERRO] Erro ao conectar: {e}")
            print("[AVISO] Certifique-se de que o servidor está rodando!")
            return False
    
    def registrar_nome(self):
        """
        Faz o registro do jogador no servidor.
        Protocolo: Servidor envia "NOME_REQUEST" -> Cliente envia nome.
        
        Returns:
            bool: True se registrou com sucesso, False caso contrário
        """
        try:
            # Aguarda solicitação de nome do servidor (protocolo definido)
            # recv(1024) = recebe até 1024 bytes do servidor
            mensagem = self.cliente_socket.recv(1024).decode('utf-8')
            
            # Verifica se o servidor enviou a mensagem esperada
            if mensagem == "NOME_REQUEST":
                print("Digite seu nome de jogador:")
                self.nome = input("Nome: ").strip()
                
                # Se não digitou nada, gera nome automático com PID do processo
                if not self.nome:
                    self.nome = f"Jogador_{os.getpid()}"
                
                # Envia nome para o servidor (codifica string em bytes UTF-8)
                self.cliente_socket.send(self.nome.encode('utf-8'))
                return True
                
        except Exception as e:
            print(f"[ERRO] Erro ao registrar nome: {e}")
            return False
    
    def receber_mensagens(self):
        """
        Thread dedicada para receber mensagens do servidor continuamente.
        Roda em loop até a conexão ser fechada.
        Este método é executado em paralelo com enviar_mensagens().
        """
        while self.conectado:
            try:
                # Recebe dados do servidor (bloqueia até receber algo)
                # 4096 bytes = tamanho do buffer de recepção
                mensagem = self.cliente_socket.recv(4096).decode('utf-8')
                
                # Se recv() retorna string vazia, servidor fechou a conexão
                if not mensagem:
                    break
                
                # Exibe a mensagem do servidor (ranking, feedback, etc)
                print(mensagem, end='')
                
                # Adiciona quebra de linha se necessário (formatação)
                if not mensagem.endswith('\n'):
                    print()
                    
            except Exception as e:
                # Erro de rede (servidor caiu, conexão perdida, etc)
                if self.conectado:
                    print(f"\n[ERRO] Erro ao receber mensagem: {e}")
                break
        
        # Marca como desconectado quando sair do loop
        self.conectado = False
    
    def enviar_mensagens(self):
        """
        Thread principal que lê input do usuário e envia ao servidor.
        Roda em loop esperando o jogador digitar palpites.
        Este método roda no thread principal (não é daemon).
        """
        print("\n[DICA] Digite seus palpites (números de 1 a 100)")
        print("[DICA] Digite 'sair' para desconectar\n")
        
        while self.conectado:
            try:
                # Aguarda input do usuário (bloqueia até pressionar ENTER)
                palpite = input()
                
                # Verifica se ainda está conectado
                if not self.conectado:
                    break
                
                # Comando especial para sair
                if palpite.lower() == 'sair':
                    print("[SAINDO] Desconectando...")
                    self.desconectar()
                    break
                
                # Envia palpite ao servidor via TCP
                # encode('utf-8') converte string para bytes
                self.cliente_socket.send(palpite.encode('utf-8'))
                
            except KeyboardInterrupt:
                # Usuário pressionou Ctrl+C
                print("\n[SAINDO] Desconectando...")
                self.desconectar()
                break
            except Exception as e:
                # Erro de rede ao enviar
                if self.conectado:
                    print(f"[ERRO] Erro ao enviar mensagem: {e}")
                break
    
    def iniciar(self):
        """
        Método principal que inicia o cliente e o jogo.
        Orquestra: conexão -> registro -> threads de comunicação.
        """
        # Passo 1: Conecta ao servidor
        if not self.conectar():
            return  # Falhou, não continua
        
        # Passo 2: Registra nome do jogador
        if not self.registrar_nome():
            self.desconectar()
            return  # Falhou no registro
        
        # Passo 3: Cria thread para RECEBER mensagens do servidor
        thread_receber = threading.Thread(target=self.receber_mensagens)
        thread_receber.daemon = True  # Thread daemon morre quando programa termina
        thread_receber.start()        # Inicia a thread em paralelo
        
        # Passo 4: Thread principal ENVIA mensagens (input do usuário)
        # Roda no thread principal para poder usar input() corretamente
        self.enviar_mensagens()
    
    def desconectar(self):
        """
        Fecha a conexão TCP com o servidor de forma limpa.
        Libera recursos de rede.
        """
        # Marca como desconectado (para as threads pararem)
        self.conectado = False
        
        # Fecha o socket TCP se existir
        if self.cliente_socket:
            try:
                self.cliente_socket.close()  # Fecha conexão (envia FIN no TCP)
            except:
                pass  # Ignora erros ao fechar (socket já pode estar fechado)
        
        print("[DESCONECTADO] Desconectado do servidor")


# ============================================================================
# BLOCO PRINCIPAL - Executa quando arquivo é rodado diretamente
# ============================================================================
if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   === NÚMERO MISTERIOSO - CLIENTE ===           ║
    ║   Trabalho de Redes de Computadores           ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # ========== CONFIGURAÇÕES DE REDE ==========
    HOST = '127.0.0.1'  # Servidor local (localhost)
    PORTA = 5555        # Porta TCP do servidor
    
    # Para conectar em outro computador da rede:
    # HOST = '192.168.1.100'  # Substitua pelo IP do servidor
    
    # ========== ARGUMENTOS DE LINHA DE COMANDO ==========
    # Permite executar: python cliente.py 192.168.1.100 5555
    if len(sys.argv) > 1:
        HOST = sys.argv[1]   # Primeiro argumento = IP
    if len(sys.argv) > 2:
        PORTA = int(sys.argv[2])  # Segundo argumento = Porta
    
    # ========== CRIAÇÃO E INICIALIZAÇÃO DO CLIENTE ==========
    cliente = ClienteJogo(HOST, PORTA)
    
    try:
        # Inicia o cliente (conecta, registra, joga)
        cliente.iniciar()
        
    except KeyboardInterrupt:
        # Usuário pressionou Ctrl+C
        print("\n\n[INTERROMPIDO] Cliente interrompido pelo usuário")
        cliente.desconectar()
        
    except Exception as e:
        # Qualquer outro erro não tratado
        print(f"\n[ERRO] Erro inesperado: {e}")
        cliente.desconectar()
