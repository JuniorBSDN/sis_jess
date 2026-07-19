from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error

class handler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_POST(self):
        self._set_headers()
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            dados = json.loads(post_data.decode('utf-8'))
            action = dados.get('action')

            sb_url = os.environ.get('SUPABASE_URL')
            sb_key = os.environ.get('SUPABASE_SERVICE_KEY')

            # -------------------------------------------------------------
            # AÇÃO 1: Validar USER_SENHA (master.html)
            # -------------------------------------------------------------
            if action == 'verificar_senha':
                senha_digitada = dados.get('senha')
                senha_correta = os.environ.get('USER_SENHA')

                if senha_digitada == senha_correta:
                    resposta = {"autorizado": True}
                else:
                    resposta = {"autorizado": False, "mensagem": "Senha incorreta."}
                
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # -------------------------------------------------------------
            # AÇÃO 2: Verificar Status da Unidade (admin.html)
            # -------------------------------------------------------------
            elif action == 'verificar_status_unidade':
                url = f"{sb_url}/rest/v1/configuracoes?chave=eq.unidade_ativa&select=valor"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                
                try:
                    with urllib.request.urlopen(req) as response:
                        res_data = json.loads(response.read().decode('utf-8'))
                        ativo = res_data[0]['valor'] == 'true' if res_data else True
                        resposta = {"ativo": ativo}
                except:
                    resposta = {"ativo": True} # Fallback seguro
                
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # -------------------------------------------------------------
            # AÇÃO 3: Alterar Status da Unidade (master.html)
            # -------------------------------------------------------------
            elif action == 'alterar_status_unidade':
                novo_status = dados.get('status')
                url = f"{sb_url}/rest/v1/configuracoes?chave=eq.unidade_ativa"
                payload = json.dumps({"valor": str(novo_status)}).encode('utf-8')
                
                req = urllib.request.Request(
                    url, data=payload, 
                    headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'},
                    method='PATCH'
                )
                
                with urllib.request.urlopen(req) as response:
                    resposta = {"sucesso": True}
                
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # -------------------------------------------------------------
            # AÇÃO 4: Salvar Novo Apoiador (index.html)
            # -------------------------------------------------------------
            elif action == 'salvar_apoiador':
                url = f"{sb_url}/rest/v1/eleitores"
                payload = json.dumps({
                    "nome": dados.get('nome'),
                    "whatsapp": dados.get('whatsapp'),
                    "bairro": dados.get('bairro'),
                    "titulo_eleitor": dados.get('titulo'),
                    "demanda_inicial": dados.get('demanda'),
                    "origem_cadastro": "Portal Público"
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    url, data=payload,
                    headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req) as response:
                    resposta = {"sucesso": True}
                
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

            # -------------------------------------------------------------
            # AÇÃO 5: Buscar Dados Consolidados (master.html)
            # -------------------------------------------------------------
            elif action == 'buscar_dados_master':
                # Puxa Eleitores
                url_e = f"{sb_url}/rest/v1/eleitores?select=bairro"
                req_e = urllib.request.Request(url_e, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req_e) as r_e:
                    eleitores = json.loads(r_e.read().decode('utf-8'))

                # Puxa Financeiro
                url_f = f"{sb_url}/rest/v1/financeiro?select=*"
                req_f = urllib.request.Request(url_f, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req_f) as r_f:
                    financeiro = json.loads(r_f.read().decode('utf-8'))

                resposta = {"eleitores": eleitores, "financeiro": financeiro}
                self.wfile.write(json.dumps(resposta).encode('utf-8'))
                return

        except Exception as e:
            self.wfile.write(json.dumps({"erro": str(e)}).encode('utf-8'))
