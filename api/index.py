from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import mimetypes

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

            # --- AÇÃO 1: Autenticação Master ---
            if action == 'verificar_senha_master':
                senha_digitada = dados.get('senha')
                senha_correta = os.environ.get('USER_SENHA')
                self.wfile.write(json.dumps({"autorizado": senha_digitada == senha_correta}).encode('utf-8'))
                return

            # --- AÇÃO 2: Upload da Logo ---
            elif action == 'upload_logo':
                file_base64 = dados.get('file_base64')
                filename = dados.get('filename')
                import base64
                file_bytes = base64.b64decode(file_base64.split(",")[-1])
                url_storage = f"{sb_url}/storage/v1/object/logos/{filename}"
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
                
                req = urllib.request.Request(
                    url_storage, data=file_bytes,
                    headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': content_type},
                    method='POST'
                )
                try:
                    with urllib.request.urlopen(req) as response: pass
                except urllib.error.HTTPError as e:
                    if e.code != 400: raise e
                
                url_publica = f"{sb_url}/storage/v1/object/public/logos/{filename}"
                self.wfile.write(json.dumps({"sucesso": True, "url_logo": url_publica}).encode('utf-8'))
                return

            # --- AÇÃO 3: Cadastrar Gestor ---
            elif action == 'cadastrar_gestor':
                url = f"{sb_url}/rest/v1/gestores"
                payload = json.dumps({
                    "nome_gestor": dados.get('nome_gestor'),
                    "nome_campanha_gabinete": dados.get('nome_gabinete'),
                    "whatsapp": dados.get('whatsapp'),
                    "senha_admin": dados.get('senha_admin'),
                    "cor_layout": dados.get('cor_layout'),
                    "url_logo": dados.get('url_logo'),
                    "status": "Ativo"
                }).encode('utf-8')
                
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req) as r: pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- AÇÃO 4: Listar Gestores ---
            elif action == 'dados_dashboard_master':
                url = f"{sb_url}/rest/v1/gestores?select=id,nome_gestor,nome_campanha_gabinete,status,cor_layout,url_logo,whatsapp,senha_admin&order=id.desc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    gestores = json.loads(response.read().decode('utf-8'))
                self.wfile.write(json.dumps({"gestores": gestores}).encode('utf-8'))
                return

            # --- NOVA AÇÃO: Atualizar / Editar Gestor ---
            elif action == 'editar_gestor':
                gid = dados.get('id')
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                body = {
                    "nome_gestor": dados.get('nome_gestor'),
                    "nome_campanha_gabinete": dados.get('nome_gabinete'),
                    "whatsapp": dados.get('whatsapp'),
                    "cor_layout": dados.get('cor_layout')
                }
                if dados.get('url_logo'):
                    body["url_logo"] = dados.get('url_logo')
                    
                payload = json.dumps(body).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req) as r: pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- NOVA AÇÃO: Alternar Status (Ativar/Desativar) ---
            elif action == 'alterar_status_gestor':
                gid = dados.get('id')
                novo_status = dados.get('status') # 'Ativo' ou 'Inativo'
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                payload = json.dumps({"status": novo_status}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req) as r: pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- NOVA AÇÃO: Excluir Gestor ---
            elif action == 'excluir_gestor':
                gid = dados.get('id')
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req) as r: pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- AÇÃO DE LOGIN DO GESTOR ---
            elif action == 'verificar_login_gestor':
                senha_input = dados.get('senha')
                url = f"{sb_url}/rest/v1/gestores?senha_admin=eq.{senha_input}&status=eq.Ativo&select=id,nome_campanha_gabinete,cor_layout,url_logo"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                if res_data:
                    self.wfile.write(json.dumps({"autorizado": True, "gestor": res_data[0]}).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"autorizado": False, "mensagem": "Acesso suspenso ou inválido."}).encode('utf-8'))
                return

        except Exception as e:
            self.wfile.write(json.dumps({"erro": str(e)}).encode('utf-8'))
