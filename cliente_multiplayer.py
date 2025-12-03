"""
Cliente Multiplayer do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores

Funcionalidades:
- Conexão TCP ao servidor do jogo
- Sistema de salas
- Chat UDP paralelo (mensagens em tempo real)
- Interface colorida no terminal
"""

import socket
import threading
import sys
import os
import json
from datetime import datetime

class ChatUDP:
    """Cliente de chat usando UDP"""
    
    def __init__(self, host='127.0.0.1', porta=5556):
        self.host = host
        self.porta = porta
        self.socket_udp = None
        self.ativo = False
        self.nome_usuario = ""
        self.sala_atual = ""
        
    def conectar(self, nome_usuario, sala):
        """Conecta ao servidor de chat UDP"""
        try:
            self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.nome_usuario = nome_usuario
            self.sala_atual = sala
            self.ativo = True
            
            # Registra no servidor
            registro = json.dumps({
                'tipo': 'REGISTRO',
                'nome': nome_usuario
            })
            self.socket_udp.sendto(registro.encode('utf-8'), (self.host, self.porta))
            
            # Inicia thread para receber mensagens
            thread = threading.Thread(target=self.receber_mensagens)
            thread.daemon = True
            thread.start()
            
            print(f"[CHAT] Chat UDP conectado!")
            return True
            
        except Exception as e:
            print(f"[AVISO] Chat UDP não disponível: {e}")
            return False
    
    def receber_mensagens(self):
        """Recebe mensagens do chat"""
        while self.ativo:
            try:
                dados, _ = self.socket_udp.recvfrom(4096)
                mensagem = json.loads(dados.decode('utf-8'))
                
                tipo = mensagem.get('tipo', '')
                
                if tipo == 'CHAT':
                    nome = mensagem.get('nome', '')
                    texto = mensagem.get('texto', '')
                    sala = mensagem.get('sala', '')
                    timestamp = mensagem.get('timestamp', '')
                    
                    # Exibe apenas se for da mesma sala ou sala geral
                    if sala == self.sala_atual or sala == 'Geral':
                        print(f"\n[CHAT] [{timestamp}] {nome}: {texto}")
                        print(">>> ", end='', flush=True)
                        
                elif tipo == 'CONFIRMACAO':
                    # Confirmação de registro (silencioso)
                    pass
                    
            except Exception as e:
                if self.ativo:
                    print(f"\n[ERRO] Erro no chat: {e}")
                break
    
    def enviar_mensagem(self, texto):
        """Envia mensagem para o chat"""
        if not self.ativo:
            return False
            
        try:
            mensagem = json.dumps({
                'tipo': 'MENSAGEM',
                'nome': self.nome_usuario,
                'texto': texto,
                'sala': self.sala_atual
            })
            self.socket_udp.sendto(mensagem.encode('utf-8'), (self.host, self.porta))
            return True
        except Exception as e:
            print(f"[ERRO] Erro ao enviar mensagem: {e}")
            return False
    
    def desconectar(self):
        """Desconecta do chat"""
        self.ativo = False
        if self.socket_udp:
            try:
                self.socket_udp.close()
            except:
                pass


class ClienteMultiplayer:
    """Cliente do jogo com suporte a salas e chat"""
    
    def __init__(self, host='127.0.0.1', porta_tcp=5555, porta_udp=5556):
        self.host = host
        self.porta_tcp = porta_tcp
        self.porta_udp = porta_udp
        self.socket_tcp = None
        self.conectado = False
        self.nome = ""
        self.sala_nome = ""
        self.chat_udp = None
        
    def conectar(self):
        """Conecta ao servidor TCP do jogo"""
        try:
            self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_tcp.connect((self.host, self.porta_tcp))
            self.conectado = True
            
            print(f"[OK] Conectado ao servidor {self.host}:{self.porta_tcp}\n")
            return True
            
        except Exception as e:
            print(f"[ERRO] Erro ao conectar: {e}")
            print("[AVISO] Certifique-se de que o servidor está rodando!")
            return False
    
    def registrar_nome(self):
        """Registra nome do jogador"""
        try:
            mensagem = self.socket_tcp.recv(1024).decode('utf-8')
            
            if mensagem == "NOME_REQUEST":
                print("=" * 50)
                print("Digite seu nome de jogador:")
                self.nome = input("Nome: ").strip()
                
                if not self.nome:
                    self.nome = f"Jogador_{os.getpid()}"
                
                self.socket_tcp.send(self.nome.encode('utf-8'))
                print(f"[OK] Registrado como: {self.nome}\n")
                return True
                
        except Exception as e:
            print(f"[ERRO] Erro ao registrar: {e}")
            return False
    
    def menu_salas(self):
        """Interage com o menu de salas"""
        try:
            while True:
                # Recebe menu
                menu = self.socket_tcp.recv(4096).decode('utf-8')
                print(menu, end='')
                
                escolha = input().strip()
                self.socket_tcp.send(escolha.encode('utf-8'))
                
                if escolha == '1':
                    # Lista de salas
                    lista = self.socket_tcp.recv(4096).decode('utf-8')
                    print(lista)
                    
                elif escolha == '2':
                    # Criar sala
                    prompt = self.socket_tcp.recv(1024).decode('utf-8')
                    print(prompt, end='')
                    nome_sala = input().strip()
                    self.socket_tcp.send(nome_sala.encode('utf-8'))
                    
                    resposta = self.socket_tcp.recv(1024).decode('utf-8')
                    print(resposta)
                    
                elif escolha == '3':
                    # Entrar em sala
                    prompt = self.socket_tcp.recv(1024).decode('utf-8')
                    print(prompt, end='')
                    id_sala = input().strip()
                    self.socket_tcp.send(id_sala.encode('utf-8'))
                    
                    # Aguarda confirmação
                    resposta = self.socket_tcp.recv(4096).decode('utf-8')
                    print(resposta)
                    
                    # Se entrou na sala, inicia o jogo
                    if "Você entrou na sala" in resposta:
                        # Extrai nome da sala
                        try:
                            self.sala_nome = resposta.split("sala: ")[1].split("\n")[0]
                        except:
                            self.sala_nome = f"Sala {id_sala}"
                        
                        # Conecta ao chat UDP
                        self.chat_udp = ChatUDP(self.host, self.porta_udp)
                        self.chat_udp.conectar(self.nome, self.sala_nome)
                        
                        return True
                        
        except Exception as e:
            print(f"[ERRO] Erro no menu: {e}")
            return False
    
    def receber_mensagens_jogo(self):
        """Thread para receber mensagens do jogo (TCP)"""
        while self.conectado:
            try:
                mensagem = self.socket_tcp.recv(4096).decode('utf-8')
                
                if not mensagem:
                    break
                
                # Exibe mensagem do servidor
                print(f"\n{mensagem}", end='')
                
                # Prompt para próximo input
                if not mensagem.endswith('\n'):
                    print()
                print(">>> ", end='', flush=True)
                
            except Exception as e:
                if self.conectado:
                    print(f"\n[ERRO] Conexão perdida: {e}")
                break
        
        self.conectado = False
    
    def enviar_comandos(self):
        """Thread para enviar comandos do usuário"""
        print("\n" + "=" * 50)
        print("=== COMANDOS:")
        print("   - Digite números (1-100) para fazer palpites")
        print("   - Digite 'chat <mensagem>' para enviar no chat")
        print("   - Digite 'sair' para desconectar")
        print("=" * 50)
        print()
        
        while self.conectado:
            try:
                print(">>> ", end='', flush=True)
                comando = input().strip()
                
                if not self.conectado:
                    break
                
                if comando.lower() == 'sair':
                    print("👋 Desconectando...")
                    self.desconectar()
                    break
                
                # Verifica se é comando de chat
                if comando.lower().startswith('chat '):
                    mensagem_chat = comando[5:].strip()
                    if mensagem_chat and self.chat_udp:
                        self.chat_udp.enviar_mensagem(mensagem_chat)
                    continue
                
                # Envia palpite ao servidor TCP
                self.socket_tcp.send(comando.encode('utf-8'))
                
            except KeyboardInterrupt:
                print("\n👋 Desconectando...")
                self.desconectar()
                break
            except Exception as e:
                if self.conectado:
                    print(f"[ERRO] Erro: {e}")
                break
    
    def iniciar(self):
        """Inicia o cliente"""
        if not self.conectar():
            return
        
        if not self.registrar_nome():
            self.desconectar()
            return
        
        if not self.menu_salas():
            self.desconectar()
            return
        
        # Threads de comunicação
        thread_receber = threading.Thread(target=self.receber_mensagens_jogo)
        thread_receber.daemon = True
        thread_receber.start()
        
        # Thread de envio (principal)
        self.enviar_comandos()
    
    def desconectar(self):
        """Desconecta do servidor"""
        self.conectado = False
        
        if self.chat_udp:
            self.chat_udp.desconectar()
        
        if self.socket_tcp:
            try:
                self.socket_tcp.close()
            except:
                pass
        
        print("[DESCONECTADO] Desconectado!")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════════════╗
    ║   === NÚMERO MISTERIOSO - CLIENTE MULTIPLAYER ===   ║
    ║   Sistema de Salas + Chat UDP                          ║
    ║   Trabalho de Redes de Computadores                    ║
    ╚════════════════════════════════════════════════════════╝
    """)
    
    # Configurações
    HOST = '127.0.0.1'  # Servidor local
    PORTA_TCP = 5555    # Jogo
    PORTA_UDP = 5556    # Chat
    
    # Permite argumentos de linha de comando
    if len(sys.argv) > 1:
        HOST = sys.argv[1]
    if len(sys.argv) > 2:
        PORTA_TCP = int(sys.argv[2])
    if len(sys.argv) > 3:
        PORTA_UDP = int(sys.argv[3])
    
    print(f"[TCP] Conectando em {HOST}:{PORTA_TCP}")
    print(f"[UDP] Chat: {HOST}:{PORTA_UDP}\n")
    
    cliente = ClienteMultiplayer(HOST, PORTA_TCP, PORTA_UDP)
    
    try:
        cliente.iniciar()
    except KeyboardInterrupt:
        print("\n\n[INTERROMPIDO] Interrompido pelo usuário")
        cliente.desconectar()
    except Exception as e:
        print(f"\n[ERRO] Erro: {e}")
        cliente.desconectar()
