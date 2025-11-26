"""
Servidor do Jogo: Número Misterioso Online
Trabalho de Redes de Computadores
"""

import socket
import threading
import random
import time
from datetime import datetime

class ServidorJogo:
    def __init__(self, host='127.0.0.1', porta=5555):
        self.host = host
        self.porta = porta
        self.servidor_socket = None
        self.clientes = []  # Lista de (socket, endereco, nome, pontos)
        self.clientes_lock = threading.Lock()
        
        # Controle do jogo
        self.numero_secreto = None
        self.rodada = 0
        self.tentativas_rodada = {}
        self.jogo_ativo = False
        
    def iniciar_servidor(self):
        """Inicializa o servidor e começa a aceitar conexões"""
        self.servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.servidor_socket.bind((self.host, self.porta))
            self.servidor_socket.listen(5)
            print(f"🎮 Servidor iniciado em {self.host}:{self.porta}")
            print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
            print("=" * 50)
            print("Aguardando conexões de jogadores...\n")
            
            # Inicia primeira rodada
            self.nova_rodada()
            
            # Loop principal - aceita novos clientes
            while True:
                cliente_socket, endereco = self.servidor_socket.accept()
                print(f"📡 Nova conexão de {endereco}")
                
                # Cria thread para lidar com o cliente
                thread_cliente = threading.Thread(
                    target=self.manipular_cliente,
                    args=(cliente_socket, endereco)
                )
                thread_cliente.daemon = True
                thread_cliente.start()
                
        except Exception as e:
            print(f"❌ Erro no servidor: {e}")
        finally:
            self.fechar_servidor()
    
    def manipular_cliente(self, cliente_socket, endereco):
        """Manipula a comunicação com um cliente específico"""
        nome_cliente = None
        
        try:
            # Solicita nome do jogador
            cliente_socket.send("NOME_REQUEST".encode('utf-8'))
            nome_cliente = cliente_socket.recv(1024).decode('utf-8').strip()
            
            if not nome_cliente:
                nome_cliente = f"Jogador_{endereco[1]}"
            
            # Adiciona cliente à lista
            with self.clientes_lock:
                self.clientes.append({
                    'socket': cliente_socket,
                    'endereco': endereco,
                    'nome': nome_cliente,
                    'pontos': 0
                })
            
            print(f"✅ {nome_cliente} entrou no jogo! ({endereco})")
            
            # Envia mensagem de boas-vindas
            mensagem_boas_vindas = (
                f"\n{'='*50}\n"
                f"🎮 Bem-vindo ao NÚMERO MISTERIOSO ONLINE! 🎮\n"
                f"{'='*50}\n"
                f"Jogador: {nome_cliente}\n"
                f"Rodada atual: {self.rodada}\n"
                f"Número secreto: 1-100\n"
                f"Digite seu palpite e pressione ENTER!\n"
                f"{'='*50}\n"
            )
            cliente_socket.send(mensagem_boas_vindas.encode('utf-8'))
            
            # Broadcast para outros jogadores
            self.broadcast(f"📢 {nome_cliente} entrou no jogo!", excluir=cliente_socket)
            
            # Loop de recebimento de mensagens
            while True:
                dados = cliente_socket.recv(1024).decode('utf-8').strip()
                
                if not dados:
                    break
                
                # Processa palpite
                self.processar_palpite(cliente_socket, nome_cliente, dados)
                
        except Exception as e:
            print(f"⚠️ Erro com {nome_cliente or endereco}: {e}")
        finally:
            # Remove cliente da lista
            with self.clientes_lock:
                self.clientes = [c for c in self.clientes if c['socket'] != cliente_socket]
            
            cliente_socket.close()
            print(f"🔌 {nome_cliente or endereco} desconectou")
            
            if nome_cliente:
                self.broadcast(f"📢 {nome_cliente} saiu do jogo!")
    
    def processar_palpite(self, cliente_socket, nome_cliente, palpite_str):
        """Processa o palpite enviado pelo cliente"""
        try:
            palpite = int(palpite_str)
            
            if palpite < 1 or palpite > 100:
                cliente_socket.send("⚠️ Número deve estar entre 1 e 100!\n".encode('utf-8'))
                return
            
            # Registra tentativa
            if nome_cliente not in self.tentativas_rodada:
                self.tentativas_rodada[nome_cliente] = 0
            self.tentativas_rodada[nome_cliente] += 1
            
            print(f"🎯 {nome_cliente} chutou: {palpite}")
            
            # Verifica o palpite
            if palpite == self.numero_secreto:
                # ACERTOU!
                pontos_ganhos = max(10 - self.tentativas_rodada[nome_cliente], 1)
                
                # Atualiza pontuação
                with self.clientes_lock:
                    for cliente in self.clientes:
                        if cliente['nome'] == nome_cliente:
                            cliente['pontos'] += pontos_ganhos
                            break
                
                # Mensagem de vitória
                mensagem_vitoria = (
                    f"\n{'🎉'*25}\n"
                    f"🏆 PARABÉNS! Você ACERTOU! 🏆\n"
                    f"Número secreto: {self.numero_secreto}\n"
                    f"Tentativas: {self.tentativas_rodada[nome_cliente]}\n"
                    f"Pontos ganhos: +{pontos_ganhos}\n"
                    f"{'🎉'*25}\n"
                )
                cliente_socket.send(mensagem_vitoria.encode('utf-8'))
                
                # Broadcast para todos
                self.broadcast(
                    f"\n🎊 {nome_cliente} ACERTOU o número {self.numero_secreto}! "
                    f"({self.tentativas_rodada[nome_cliente]} tentativas) 🎊\n"
                )
                
                # Aguarda 3 segundos e inicia nova rodada
                time.sleep(3)
                self.nova_rodada()
                
            elif palpite < self.numero_secreto:
                resposta = f"📈 Muito BAIXO! Tentativa {self.tentativas_rodada[nome_cliente]}\n"
                cliente_socket.send(resposta.encode('utf-8'))
                self.broadcast(f"💭 {nome_cliente} chutou um número... (tentativa {self.tentativas_rodada[nome_cliente]})", excluir=cliente_socket)
                
            else:  # palpite > numero_secreto
                resposta = f"📉 Muito ALTO! Tentativa {self.tentativas_rodada[nome_cliente]}\n"
                cliente_socket.send(resposta.encode('utf-8'))
                self.broadcast(f"💭 {nome_cliente} chutou um número... (tentativa {self.tentativas_rodada[nome_cliente]})", excluir=cliente_socket)
                
        except ValueError:
            cliente_socket.send("❌ Digite apenas números!\n".encode('utf-8'))
    
    def nova_rodada(self):
        """Inicia uma nova rodada do jogo"""
        self.rodada += 1
        self.numero_secreto = random.randint(1, 100)
        self.tentativas_rodada = {}
        self.jogo_ativo = True
        
        print(f"\n🔄 NOVA RODADA {self.rodada}")
        print(f"🔐 Número secreto: {self.numero_secreto}")
        print("=" * 50)
        
        # Envia ranking e nova rodada para todos
        ranking = self.gerar_ranking()
        mensagem = (
            f"\n{'='*50}\n"
            f"🔄 NOVA RODADA {self.rodada} 🔄\n"
            f"{'='*50}\n"
            f"{ranking}\n"
            f"Adivinhe o número entre 1 e 100!\n"
            f"{'='*50}\n"
        )
        self.broadcast(mensagem)
    
    def gerar_ranking(self):
        """Gera o ranking de pontuação dos jogadores"""
        with self.clientes_lock:
            if not self.clientes:
                return "Nenhum jogador online"
            
            # Ordena por pontos
            ranking_ordenado = sorted(self.clientes, key=lambda x: x['pontos'], reverse=True)
            
            ranking_texto = "🏆 RANKING 🏆\n"
            for i, cliente in enumerate(ranking_ordenado, 1):
                emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "  "
                ranking_texto += f"{emoji} {i}º {cliente['nome']}: {cliente['pontos']} pontos\n"
            
            return ranking_texto
    
    def broadcast(self, mensagem, excluir=None):
        """Envia mensagem para todos os clientes conectados"""
        with self.clientes_lock:
            for cliente in self.clientes:
                if excluir and cliente['socket'] == excluir:
                    continue
                try:
                    cliente['socket'].send(mensagem.encode('utf-8'))
                except:
                    pass
    
    def fechar_servidor(self):
        """Fecha o servidor e todas as conexões"""
        print("\n🛑 Encerrando servidor...")
        
        with self.clientes_lock:
            for cliente in self.clientes:
                try:
                    cliente['socket'].close()
                except:
                    pass
        
        if self.servidor_socket:
            self.servidor_socket.close()
        
        print("✅ Servidor encerrado!")


if __name__ == "__main__":
    print("""
    ╔════════════════════════════════════════════════╗
    ║   🎮 NÚMERO MISTERIOSO - SERVIDOR 🎮          ║
    ║   Trabalho de Redes de Computadores           ║
    ╚════════════════════════════════════════════════╝
    """)
    
    # Configurações do servidor
    HOST = '127.0.0.1'  # Localhost para testes
    PORTA = 5555
    
    # Pode alterar para aceitar conexões externas:
    # HOST = '0.0.0.0'  # Aceita de qualquer IP
    
    servidor = ServidorJogo(HOST, PORTA)
    
    try:
        servidor.iniciar_servidor()
    except KeyboardInterrupt:
        print("\n\n⚠️ Servidor interrompido pelo usuário")
        servidor.fechar_servidor()
