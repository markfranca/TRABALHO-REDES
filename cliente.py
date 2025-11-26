"""
Cliente do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores
"""

import socket
import threading
import sys
import os

class ClienteJogo:
    def __init__(self, host='127.0.0.1', porta=5555):
        self.host = host
        self.porta = porta
        self.cliente_socket = None
        self.conectado = False
        self.nome = ""
        
    def conectar(self):
        """Conecta ao servidor do jogo"""
        try:
            self.cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.cliente_socket.connect((self.host, self.porta))
            self.conectado = True
            
            print(f"✅ Conectado ao servidor {self.host}:{self.porta}\n")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao conectar: {e}")
            print("⚠️ Certifique-se de que o servidor está rodando!")
            return False
    
    def registrar_nome(self):
        """Registra o nome do jogador no servidor"""
        try:
            # Aguarda solicitação de nome
            mensagem = self.cliente_socket.recv(1024).decode('utf-8')
            
            if mensagem == "NOME_REQUEST":
                print("Digite seu nome de jogador:")
                self.nome = input("👤 Nome: ").strip()
                
                if not self.nome:
                    self.nome = f"Jogador_{os.getpid()}"
                
                self.cliente_socket.send(self.nome.encode('utf-8'))
                return True
                
        except Exception as e:
            print(f"❌ Erro ao registrar nome: {e}")
            return False
    
    def receber_mensagens(self):
        """Thread para receber mensagens do servidor"""
        while self.conectado:
            try:
                mensagem = self.cliente_socket.recv(4096).decode('utf-8')
                
                if not mensagem:
                    break
                
                # Exibe a mensagem do servidor
                print(mensagem, end='')
                
                # Se não termina com \n, adiciona
                if not mensagem.endswith('\n'):
                    print()
                    
            except Exception as e:
                if self.conectado:
                    print(f"\n❌ Erro ao receber mensagem: {e}")
                break
        
        self.conectado = False
    
    def enviar_mensagens(self):
        """Thread para enviar mensagens (palpites) ao servidor"""
        print("\n💡 Digite seus palpites (números de 1 a 100)")
        print("💡 Digite 'sair' para desconectar\n")
        
        while self.conectado:
            try:
                palpite = input()
                
                if not self.conectado:
                    break
                
                if palpite.lower() == 'sair':
                    print("👋 Desconectando...")
                    self.desconectar()
                    break
                
                # Envia palpite ao servidor
                self.cliente_socket.send(palpite.encode('utf-8'))
                
            except KeyboardInterrupt:
                print("\n👋 Desconectando...")
                self.desconectar()
                break
            except Exception as e:
                if self.conectado:
                    print(f"❌ Erro ao enviar mensagem: {e}")
                break
    
    def iniciar(self):
        """Inicia o cliente do jogo"""
        if not self.conectar():
            return
        
        if not self.registrar_nome():
            self.desconectar()
            return
        
        # Cria threads para enviar e receber mensagens
        thread_receber = threading.Thread(target=self.receber_mensagens)
        thread_receber.daemon = True
        thread_receber.start()
        
        # Thread de envio roda no thread principal
        self.enviar_mensagens()
    
    def desconectar(self):
        """Desconecta do servidor"""
        self.conectado = False
        
        if self.cliente_socket:
            try:
                self.cliente_socket.close()
            except:
                pass
        
        print("🔌 Desconectado do servidor")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   🎮 NÚMERO MISTERIOSO - CLIENTE 🎮           ║
    ║   Trabalho de Redes de Computadores           ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # Configurações de conexão
    HOST = '127.0.0.1'  # Servidor local
    PORTA = 5555
    
    # Se o servidor estiver em outra máquina, altere o HOST:
    # HOST = '192.168.1.100'  # Exemplo
    
    # Permite passar host e porta como argumentos
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORTA = int(sys.argv[2])
    
    cliente = ClienteJogo(HOST, PORTA)
    
    try:
        cliente.iniciar()
    except KeyboardInterrupt:
        print("\n\n⚠️ Cliente interrompido pelo usuário")
        cliente.desconectar()
    except Exception as e:
        print(f"\n❌ Erro inesperado: {e}")
        cliente.desconectar()
