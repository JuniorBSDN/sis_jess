from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

class handler(BaseHTTPRequestHandler):

    def _set_headers(self):
        """Define os cabeçalhos de resposta padrão e trata o CORS."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        """Trata a requisição de pré-vôo (preflight) do CORS."""
        self._set_headers()

    def do_POST(self):
        """Processa as requisições principais do ecossistema."""
        self._set_headers()

        try:
            # 1. Ler e decodificar o corpo da requisição JSON do front-end
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            dados = json.loads(post_data.decode('utf-8'))
            
            action = dados.get('action')

            # -------------------------------------------------------------
            # AÇÃO 1: Validar USER_SENHA (Acesso ao master.html)
            # -------------------------------------------------------------
            if action == 'verificar_senha':
                senha_digitada = dados.get('senha')
                senha_correta = os.environ.get('USER_SENHA')

                if not senha_correta:
                    resposta = {"autorizado": False, "mensagem": "Erro: USER_SENHA não configurada na Vercel."}
                elif senha_digitada == senha_correta:
                    resposta = {"autorizado": True, "mensagem": "Acesso Master concedido!"}
                else:
                    resposta = {"autorizado": False, "mensagem": "Senha incorreta."}
                
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # -------------------------------------------------------------
            # AÇÃO 2: Alterar Status da Unidade (Ativa/Desativa o admin.html)
            # -------------------------------------------------------------
            elif action == 'alterar_status_unidade':
                novo_status = dados.get('status') # Espera 'true' ou 'false'
                
                sb_url = os.environ.get('SUPABASE_URL')
                sb_key = os.environ.get('SUPABASE_SERVICE_KEY') # sb_secret_...

                if not sb_url or not sb_key:
                    resposta = {"sucesso": False, "mensagem": "Erro: Credenciais do Supabase ausentes na Vercel."}
                    self.wfile.write(json.dumps(resposta).encode('utf-8'))
                    return

                # Endpoint exato da Data API (PostgREST) do Supabase filtrando pela chave da unidade
                url = f"{sb_url}/rest/v1/configuracoes?chave=eq.unidade_ativa"
                
                # Payload contendo o novo valor textual ('true' ou 'false')
                payload = json.dumps({"valor": str(novo_status)}).encode('utf-8')
                
                # Montagem milimétrica da requisição HTTP PATCH usando urllib
                req = urllib.request.Request(
                    url, 
                    data=payload, 
                    headers={
                        'apikey': sb_key,
                        'Authorization': f'Bearer {sb_key}',
                        'Content-Type': 'application/json',
                        'Prefer': 'resolution=merge-duplicates'
                    },
                    method='PATCH'
                )
                
                try:
                    with urllib.request.urlopen(req) as response:
                        resposta = {"sucesso": True, "mensagem": f"Unidade configurada para: {novo_status}"}
                except urllib.error.HTTPError as http_err:
                    detalhes_erro = http_err.read().decode('utf-8')
                    resposta = {"sucesso": False, "mensagem": f"Erro Supabase Data API: {detalhes_erro}"}
                except Exception as e:
                    resposta = {"sucesso": False, "mensagem": f"Erro de conexão: {str(e)}"}

                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # Caso nenhuma ação válida seja enviada
            self.wfile.write(json.dumps({"erro": "Ação operacional não identificada."}).encode('utf-8'))

        except Exception as e:
            # Captura de exceções genéricas na leitura do payload do servidor
            self.wfile.write(json.dumps({"erro": f"Falha interna na API: {str(e)}"}).encode('utf-8'))
