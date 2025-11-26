"""
Frontend Web para o Jogo: Número Misterioso Online
Servidor Flask + Socket.IO que faz a ponte entre o navegador e o servidor TCP

Trabalho de Redes de Computadores
"""

import socket
import threading
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'numero_misterioso_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Dicionário para armazenar conexões TCP por sessão
conexoes_tcp = {}

class ConexaoJogo:
    """Gerencia a conexão TCP com o servidor do jogo"""
    
    def __init__(self, sid, host='127.0.0.1', porta=5555):
        self.sid = sid
        self.host = host
        self.porta = porta
        self.socket_tcp = None
        self.conectado = False
        self.nome = ""
        self.thread_receber = None
        
    def conectar(self, nome):
        """Conecta ao servidor do jogo"""
        try:
            self.socket_tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket_tcp.connect((self.host, self.porta))
            self.conectado = True
            self.nome = nome
            
            # Aguarda solicitação de nome
            mensagem = self.socket_tcp.recv(1024).decode('utf-8')
            
            if mensagem == "NOME_REQUEST":
                self.socket_tcp.send(nome.encode('utf-8'))
                
                # Inicia thread para receber mensagens
                self.thread_receber = threading.Thread(target=self.receber_mensagens)
                self.thread_receber.daemon = True
                self.thread_receber.start()
                
                return True, "Conectado com sucesso!"
            else:
                return False, "Resposta inesperada do servidor"
                
        except ConnectionRefusedError:
            return False, "Servidor não está online. Inicie o servidor.py primeiro!"
        except Exception as e:
            return False, f"Erro ao conectar: {str(e)}"
    
    def receber_mensagens(self):
        """Thread para receber mensagens do servidor TCP"""
        while self.conectado:
            try:
                mensagem = self.socket_tcp.recv(4096).decode('utf-8')
                
                if not mensagem:
                    break
                
                # Envia para o cliente web via Socket.IO
                socketio.emit('mensagem_jogo', {
                    'mensagem': mensagem,
                    'tipo': self.identificar_tipo_mensagem(mensagem)
                }, room=self.sid)
                    
            except Exception as e:
                if self.conectado:
                    socketio.emit('erro', {'mensagem': f'Conexão perdida: {str(e)}'}, room=self.sid)
                break
        
        self.conectado = False
        socketio.emit('desconectado', {}, room=self.sid)
    
    def identificar_tipo_mensagem(self, mensagem):
        """Identifica o tipo de mensagem para estilização no frontend"""
        if 'ACERTOU' in mensagem or 'PARABÉNS' in mensagem or '🏆' in mensagem:
            return 'vitoria'
        elif 'Muito BAIXO' in mensagem or '📈' in mensagem:
            return 'baixo'
        elif 'Muito ALTO' in mensagem or '📉' in mensagem:
            return 'alto'
        elif 'NOVA RODADA' in mensagem or '🔄' in mensagem:
            return 'nova_rodada'
        elif 'RANKING' in mensagem or '🏆 RANKING' in mensagem:
            return 'ranking'
        elif 'entrou no jogo' in mensagem or 'saiu do jogo' in mensagem:
            return 'sistema'
        elif 'Bem-vindo' in mensagem:
            return 'boas_vindas'
        elif '❌' in mensagem or '⚠️' in mensagem:
            return 'erro'
        else:
            return 'normal'
    
    def enviar_palpite(self, palpite):
        """Envia um palpite ao servidor"""
        if self.conectado and self.socket_tcp:
            try:
                self.socket_tcp.send(str(palpite).encode('utf-8'))
                return True
            except Exception as e:
                return False
        return False
    
    def desconectar(self):
        """Desconecta do servidor"""
        self.conectado = False
        if self.socket_tcp:
            try:
                self.socket_tcp.close()
            except:
                pass


@app.route('/')
def index():
    """Página principal do jogo"""
    return render_template('index.html')


@socketio.on('connect')
def handle_connect():
    """Quando um cliente web conecta"""
    print(f'🌐 Cliente web conectado: {request.sid}')


@socketio.on('disconnect')
def handle_disconnect():
    """Quando um cliente web desconecta"""
    sid = request.sid
    if sid in conexoes_tcp:
        conexoes_tcp[sid].desconectar()
        del conexoes_tcp[sid]
    print(f'🔌 Cliente web desconectado: {sid}')


@socketio.on('conectar_jogo')
def handle_conectar_jogo(data):
    """Conecta ao servidor do jogo"""
    sid = request.sid
    nome = data.get('nome', 'Jogador')
    host = data.get('host', '127.0.0.1')
    porta = int(data.get('porta', 5555))
    
    # Desconecta conexão anterior se existir
    if sid in conexoes_tcp:
        conexoes_tcp[sid].desconectar()
    
    # Cria nova conexão
    conexao = ConexaoJogo(sid, host, porta)
    sucesso, mensagem = conexao.conectar(nome)
    
    if sucesso:
        conexoes_tcp[sid] = conexao
        emit('conectado', {'mensagem': mensagem, 'nome': nome})
        print(f'✅ {nome} conectou ao jogo via web')
    else:
        emit('erro_conexao', {'mensagem': mensagem})


@socketio.on('enviar_palpite')
def handle_enviar_palpite(data):
    """Envia um palpite ao servidor do jogo"""
    sid = request.sid
    palpite = data.get('palpite', '')
    
    if sid in conexoes_tcp:
        if conexoes_tcp[sid].enviar_palpite(palpite):
            emit('palpite_enviado', {'palpite': palpite})
        else:
            emit('erro', {'mensagem': 'Erro ao enviar palpite'})
    else:
        emit('erro', {'mensagem': 'Não conectado ao jogo'})


@socketio.on('desconectar_jogo')
def handle_desconectar_jogo():
    """Desconecta do servidor do jogo"""
    sid = request.sid
    if sid in conexoes_tcp:
        conexoes_tcp[sid].desconectar()
        del conexoes_tcp[sid]
        emit('desconectado', {})


if __name__ == '__main__':
    print("""
    ╔════════════════════════════════════════════════════════════╗
    ║   🌐 NÚMERO MISTERIOSO - FRONTEND WEB 🌐                   ║
    ║   Trabalho de Redes de Computadores                        ║
    ╚════════════════════════════════════════════════════════════╝
    """)
    
    print("📌 Instruções:")
    print("   1. Inicie o servidor.py em outro terminal")
    print("   2. Acesse http://localhost:5000 no navegador")
    print("   3. Digite seu nome e conecte-se ao jogo!")
    print("")
    print("🚀 Iniciando servidor web...")
    print("=" * 60)
    
    # Cria pasta templates se não existir
    os.makedirs('templates', exist_ok=True)
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

