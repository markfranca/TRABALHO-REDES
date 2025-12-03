"""
Frontend Web para o Jogo Multiplayer: Número Misterioso Online
Servidor Flask + Socket.IO adaptado para servidor_multiplayer.py

Funcionalidades:
- Sistema de salas via web
- Chat UDP integrado
- Interface moderna
- Multiplayer competitivo
"""

import socket
import threading
import json
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'numero_misterioso_multiplayer_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Dicionário para armazenar conexões por sessão
conexoes = {}

class ConexaoMultiplayer:
    """Gerencia conexão TCP (jogo) e UDP (chat) com servidor multiplayer"""
    
    def __init__(self, sid, host='127.0.0.1', porta_tcp=5555, porta_udp=5556):
        self.sid = sid
        self.host = host
        self.porta_tcp = porta_tcp
        self.porta_udp = porta_udp
        self.socket_tcp = None
        self.socket_udp = None
        self.conectado = False
        self.nome = ""
        self.sala_atual = ""
        self.thread_tcp = None
        self.thread_udp = None
        
    def conectar_tcp(self, nome):
        """Conecta ao servidor TCP do jogo"""
        try:
            self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_tcp.connect((self.host, self.porta_tcp))
            self.conectado = True
            self.nome = nome
            
            # Aguarda NOME_REQUEST
            mensagem = self.socket_tcp.recv(1024).decode('utf-8')
            
            if mensagem == "NOME_REQUEST":
                self.socket_tcp.send(nome.encode('utf-8'))
                
                # Inicia thread para receber mensagens TCP
                self.thread_tcp = threading.Thread(target=self.receber_tcp)
                self.thread_tcp.daemon = True
                self.thread_tcp.start()
                
                return True, "Conectado com sucesso!"
            else:
                return False, "Resposta inesperada do servidor"
                
        except ConnectionRefusedError:
            return False, "Servidor multiplayer não está online! Inicie servidor_multiplayer.py primeiro!"
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"
    
    def conectar_udp(self):
        """Conecta ao servidor UDP do chat"""
        try:
            self.socket_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Registra no servidor UDP
            registro = json.dumps({
                'tipo': 'REGISTRO',
                'nome': self.nome
            })
            self.socket_udp.sendto(registro.encode('utf-8'), (self.host, self.porta_udp))
            
            # Inicia thread para receber mensagens UDP
            self.thread_udp = threading.Thread(target=self.receber_udp)
            self.thread_udp.daemon = True
            self.thread_udp.start()
            
            return True
        except Exception as e:
            print(f"[AVISO] Chat UDP não disponível: {e}")
            return False
    
    def receber_tcp(self):
        """Thread para receber mensagens do servidor TCP (jogo)"""
        while self.conectado:
            try:
                mensagem = self.socket_tcp.recv(4096).decode('utf-8')
                
                if not mensagem:
                    break
                
                # Identifica tipo de mensagem
                tipo = self.identificar_tipo(mensagem)
                
                # Envia para o cliente web via Socket.IO
                socketio.emit('mensagem_jogo', {
                    'mensagem': mensagem,
                    'tipo': tipo
                }, room=self.sid)
                    
            except Exception as e:
                if self.conectado:
                    socketio.emit('erro', {'mensagem': f'Conexão perdida: {str(e)}'}, room=self.sid)
                break
        
        self.conectado = False
        socketio.emit('desconectado', {}, room=self.sid)
    
    def receber_udp(self):
        """Thread para receber mensagens do chat UDP"""
        while self.conectado:
            try:
                dados, _ = self.socket_udp.recvfrom(4096)
                mensagem = json.loads(dados.decode('utf-8'))
                
                tipo = mensagem.get('tipo', '')
                
                if tipo == 'CHAT':
                    # Mensagem de chat
                    socketio.emit('chat_mensagem', {
                        'nome': mensagem.get('nome', ''),
                        'texto': mensagem.get('texto', ''),
                        'sala': mensagem.get('sala', ''),
                        'timestamp': mensagem.get('timestamp', '')
                    }, room=self.sid)
                    
            except Exception as e:
                if self.conectado:
                    print(f"[ERRO] Erro UDP: {e}")
                break
    
    def identificar_tipo(self, mensagem):
        """Identifica o tipo de mensagem para estilização"""
        if 'BEM-VINDO' in mensagem or 'Escolha uma opção' in mensagem:
            return 'menu'
        elif 'SALAS DISPONÍVEIS' in mensagem:
            return 'lista_salas'
        elif 'Você entrou na sala' in mensagem:
            return 'entrou_sala'
        elif 'ACERTOU' in mensagem:
            return 'vitoria'
        elif 'Muito BAIXO' in mensagem or '[BAIXO]' in mensagem:
            return 'baixo'
        elif 'Muito ALTO' in mensagem or '[ALTO]' in mensagem:
            return 'alto'
        elif 'NOVA RODADA' in mensagem:
            return 'nova_rodada'
        elif 'RANKING' in mensagem:
            return 'ranking'
        elif 'criada com sucesso' in mensagem:
            return 'sala_criada'
        elif '>>>' in mensagem:
            return 'sistema'
        else:
            return 'normal'
    
    def enviar_comando(self, comando):
        """Envia comando ao servidor TCP"""
        if self.conectado and self.socket_tcp:
            try:
                self.socket_tcp.send(str(comando).encode('utf-8'))
                return True
            except Exception as e:
                return False
        return False
    
    def enviar_chat(self, texto):
        """Envia mensagem de chat via UDP"""
        if self.conectado and self.socket_udp:
            try:
                mensagem = json.dumps({
                    'tipo': 'MENSAGEM',
                    'nome': self.nome,
                    'texto': texto,
                    'sala': self.sala_atual
                })
                self.socket_udp.sendto(mensagem.encode('utf-8'), (self.host, self.porta_udp))
                return True
            except Exception as e:
                return False
        return False
    
    def desconectar(self):
        """Desconecta de TCP e UDP"""
        self.conectado = False
        
        if self.socket_tcp:
            try:
                self.socket_tcp.close()
            except:
                pass
        
        if self.socket_udp:
            try:
                self.socket_udp.close()
            except:
                pass


@app.route('/')
def index():
    """Página principal do jogo multiplayer"""
    return render_template('index_multiplayer.html')


@socketio.on('connect')
def handle_connect():
    """Quando um cliente web conecta"""
    print(f'[WEB] Cliente web conectado: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    """Quando um cliente web desconecta"""
    sid = request.sid
    if sid in conexoes:
        conexoes[sid].desconectar()
        del conexoes[sid]
    print(f'[WEB] Cliente web desconectado: {sid}')


@socketio.on('conectar_jogo')
def handle_conectar_jogo(data):
    """Conecta ao servidor multiplayer"""
    sid = request.sid
    nome = data.get('nome', 'Jogador')
    host = data.get('host', '127.0.0.1')
    porta_tcp = int(data.get('porta_tcp', 5555))
    porta_udp = int(data.get('porta_udp', 5556))
    
    # Desconecta conexão anterior se existir
    if sid in conexoes:
        conexoes[sid].desconectar()
    
    # Cria nova conexão
    conexao = ConexaoMultiplayer(sid, host, porta_tcp, porta_udp)
    
    # Conecta TCP
    sucesso, mensagem = conexao.conectar_tcp(nome)
    
    if sucesso:
        # Conecta UDP
        conexao.conectar_udp()
        
        conexoes[sid] = conexao
        
        # Emite confirmação para o cliente
        emit('conectado', {
            'mensagem': 'Conectado com sucesso!',
            'nome': nome
        })
        
        print(f'[OK] {nome} conectou ao jogo multiplayer via web (SID: {sid})')
        
        # Pequeno delay para garantir que a primeira mensagem seja recebida
        import time
        time.sleep(0.1)
    else:
        emit('erro_conexao', {'mensagem': mensagem})
        print(f'[ERRO] Falha ao conectar: {mensagem}')


@socketio.on('enviar_comando')
def handle_enviar_comando(data):
    """Envia comando ao servidor (escolha de menu, palpite, etc)"""
    sid = request.sid
    comando = data.get('comando', '')
    
    if sid in conexoes:
        if conexoes[sid].enviar_comando(comando):
            emit('comando_enviado', {'comando': comando})
        else:
            emit('erro', {'mensagem': 'Erro ao enviar comando'})
    else:
        emit('erro', {'mensagem': 'Não conectado ao jogo'})


@socketio.on('enviar_chat')
def handle_enviar_chat(data):
    """Envia mensagem de chat via UDP"""
    sid = request.sid
    texto = data.get('texto', '')
    
    if sid in conexoes:
        if conexoes[sid].enviar_chat(texto):
            emit('chat_enviado', {'texto': texto})
        else:
            emit('erro', {'mensagem': 'Erro ao enviar chat'})
    else:
        emit('erro', {'mensagem': 'Não conectado ao chat'})


@socketio.on('set_sala')
def handle_set_sala(data):
    """Define sala atual do jogador"""
    sid = request.sid
    sala = data.get('sala', '')
    
    if sid in conexoes:
        conexoes[sid].sala_atual = sala


@socketio.on('desconectar_jogo')
def handle_desconectar_jogo():
    """Desconecta do servidor"""
    sid = request.sid
    if sid in conexoes:
        conexoes[sid].desconectar()
        del conexoes[sid]
        emit('desconectado', {})


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   NUMERO MISTERIOSO - FRONTEND MULTIPLAYER WEB       ║
    ║   Sistema de Salas + Chat UDP via Navegador               ║
    ║   Trabalho de Redes de Computadores                        ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print("=== Instruções:")
    print("   1. Inicie o servidor_multiplayer.py em outro terminal")
    print("   2. Acesse http://localhost:5000 no navegador")
    print("   3. Digite seu nome, escolha/crie sala e jogue!")
    print("   4. Use o chat integrado para conversar!")
    print("")
    print("[INICIO] Iniciando servidor web multiplayer...")
    print("=" * 60)
    
    # Cria pasta templates se não existir
    os.makedirs('templates', exist_ok=True)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)
