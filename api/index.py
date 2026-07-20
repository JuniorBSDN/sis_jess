from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import mimetypes
import base64

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

    def _obter_url_supabase(self):
        return "https://scotyvkhwptckrvrjzdi.supabase.co"

    def do_POST(self):
        self._set_headers()
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                self.wfile.write(json.dumps({"erro": "Sem payload"}).encode('utf-8'))
                return

            post_data = self.rfile.read(content_length)
            dados = json.loads(post_data.decode('utf-8'))
            action = dados.get('action')

            sb_url = self._obter_url_supabase()
            sb_key = os.environ.get('SUPABASE_SERVICE_KEY')
            senha_mestra = os.environ.get('USER_SENHA')

            # ==========================================
            # ROTAS DO MASTER
            # ==========================================
            if action == 'verificar_senha_master':
                senha_digitada = dados.get('senha')
                self.wfile.write(json.dumps({"autorizado": senha_digitada == senha_mestra}).encode('utf-8'))
                return

            elif action == 'upload_logo':
                file_base64 = dados.get('file_base64')
                filename = dados.get('filename')
                file_bytes = base64.b64decode(file_base64.split(",")[-1])
                url_storage = f"{sb_url}/storage/v1/object/logos/{filename}"
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                req = urllib.request.Request(url_storage, data=file_bytes,
                                             headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}',
                                                      'Content-Type': content_type}, method='POST')
                try:
                    with urllib.request.urlopen(req): pass
                except urllib.error.HTTPError as e:
                    if e.code != 400: raise e

                url_publica = f"{sb_url}/storage/v1/object/public/logos/{filename}"
                self.wfile.write(json.dumps({"sucesso": True, "url_logo": url_publica}).encode('utf-8'))
                return

            elif action == 'cadastrar_gestor':
                url = f"{sb_url}/rest/v1/gestores"
                payload = json.dumps({
                    "nome_gestor": dados.get('nome_gestor'),
                    "nome_campanha_gabinete": dados.get('nome_gabinete'),
                    "whatsapp": dados.get('whatsapp'),
                    "email": dados.get('email'),
                    "documento": dados.get('documento'),
                    "data_inicio": dados.get('data_inicio'),
                    "endereco": dados.get('endereco'),
                    "senha_admin": dados.get('senha_admin'),
                    "cor_layout": dados.get('cor_layout'),
                    "url_logo": dados.get('url_logo'),
                    "status": "Ativo"
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'dados_dashboard_master':
                url = f"{sb_url}/rest/v1/gestores?select=id,nome_gestor,nome_campanha_gabinete,status,cor_layout,url_logo,whatsapp,email,documento,data_inicio,endereco,senha_admin&order=id.desc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    gestores = json.loads(response.read().decode('utf-8'))
                self.wfile.write(json.dumps({"gestores": gestores}).encode('utf-8'))
                return

            elif action == 'editar_gestor':
                gid = dados.get('id')
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                body = {
                    "nome_gestor": dados.get('nome_gestor'),
                    "nome_campanha_gabinete": dados.get('nome_gabinete'),
                    "whatsapp": dados.get('whatsapp'),
                    "email": dados.get('email'),
                    "documento": dados.get('documento'),
                    "data_inicio": dados.get('data_inicio'),
                    "endereco": dados.get('endereco'),
                    "cor_layout": dados.get('cor_layout')
                }
                if dados.get('url_logo'): body["url_logo"] = dados.get('url_logo')
                payload = json.dumps(body).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'alterar_status_gestor':
                gid = dados.get('id')
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                payload = json.dumps({"status": dados.get('status')}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'excluir_gestor':
                gid = dados.get('id')
                url = f"{sb_url}/rest/v1/gestores?id=eq.{gid}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # ==========================================
            # ROTAS DO PAINEL OPERACIONAL E SITE (PÚBLICO)
            # ==========================================
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

            # --- FUNCIONÁRIOS (RH) ---
            elif action == 'listar_funcionarios':
                gestor_id = dados.get('gestor_id')
                url = f"{sb_url}/rest/v1/funcionarios?gestor_id=eq.{gestor_id}&order=id.desc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    funcs = json.loads(response.read().decode('utf-8'))
                self.wfile.write(json.dumps({"funcionarios": funcs}).encode('utf-8'))
                return

            elif action == 'cadastrar_funcionario':
                url = f"{sb_url}/rest/v1/funcionarios"
                payload = json.dumps({
                    "nome": dados.get('nome'),
                    "cargo": dados.get('cargo'),
                    "whatsapp": dados.get('whatsapp'),
                    "gestor_id": dados.get('gestor_id'),
                    "status": "Ativo"
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'editar_funcionario':
                fid = dados.get('id')
                url = f"{sb_url}/rest/v1/funcionarios?id=eq.{fid}"
                payload = json.dumps({
                    "nome": dados.get('nome'),
                    "whatsapp": dados.get('whatsapp'),
                    "cargo": dados.get('cargo')
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return
                
            elif action == 'alterar_status_funcionario':
                fid = dados.get('id')
                url = f"{sb_url}/rest/v1/funcionarios?id=eq.{fid}"
                
                # Consolidado milimetricamente para evitar conflitos de maiúsculas/minúsculas no banco
                status_bruto = dados.get('status')
                novo_status = status_bruto.capitalize() if status_bruto else "Ativo"
                
                payload = json.dumps({"status": novo_status}).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return
                
            elif action == 'excluir_funcionario':
                fid = dados.get('id')
                url = f"{sb_url}/rest/v1/funcionarios?id=eq.{fid}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- ELEITORES ---
            elif action == 'salvar_apoiador':
                url = f"{sb_url}/rest/v1/eleitores"
                payload = json.dumps({
                    "nome": dados.get('nome'),
                    "whatsapp": dados.get('whatsapp'),
                    "bairro": dados.get('bairro'),
                    "titulo": dados.get('titulo'),
                    "demanda": dados.get('demanda'),
                    "gestor_id": dados.get('gestor_id')
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'listar_eleitores_gestor':
                gestor_id = dados.get('gestor_id')
                url = f"{sb_url}/rest/v1/eleitores?gestor_id=eq.{gestor_id}&order=id.desc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    eleitores = json.loads(response.read().decode('utf-8'))
                self.wfile.write(json.dumps({"eleitores": eleitores}).encode('utf-8'))
                return
                
            elif action == 'excluir_eleitor':
                eid = dados.get('id')
                url = f"{sb_url}/rest/v1/eleitores?id=eq.{eid}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- AGENDA ---
            elif action == 'listar_agenda_gestor':
                gestor_id = dados.get('gestor_id')
                url = f"{sb_url}/rest/v1/agenda?gestor_id=eq.{gestor_id}&order=data_evento.asc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                try:
                    with urllib.request.urlopen(req) as response:
                        agenda = json.loads(response.read().decode('utf-8'))
                except:
                    agenda = []
                self.wfile.write(json.dumps({"agenda": agenda}).encode('utf-8'))
                return

            elif action == 'cadastrar_agenda':
                url = f"{sb_url}/rest/v1/agenda"
                payload = json.dumps({
                    "titulo": dados.get('titulo'),
                    "tipo": dados.get('tipo'),
                    "data_evento": dados.get('data'),
                    "gestor_id": dados.get('gestor_id')
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return
                
            elif action == 'excluir_agenda':
                aid = dados.get('id')
                url = f"{sb_url}/rest/v1/agenda?id=eq.{aid}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            # --- DOCUMENTOS E ARQUIVOS ---
            elif action == 'upload_documento':
                file_base64 = dados.get('file_base64')
                filename = dados.get('filename')
                file_bytes = base64.b64decode(file_base64.split(",")[-1])
                url_storage = f"{sb_url}/storage/v1/object/documentos/{filename}"
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                req = urllib.request.Request(url_storage, data=file_bytes,
                                             headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}',
                                                      'Content-Type': content_type}, method='POST')
                try:
                    with urllib.request.urlopen(req): pass
                except urllib.error.HTTPError as e:
                    if e.code != 400: raise e

                url_publica = f"{sb_url}/storage/v1/object/public/documentos/{filename}"
                self.wfile.write(json.dumps({"sucesso": True, "url_arquivo": url_publica}).encode('utf-8'))
                return

            elif action == 'listar_documentos_gestor':
                gestor_id = dados.get('gestor_id')
                url = f"{sb_url}/rest/v1/documentos?gestor_id=eq.{gestor_id}&order=id.desc"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                try:
                    with urllib.request.urlopen(req) as response:
                        docs = json.loads(response.read().decode('utf-8'))
                except:
                    docs = []
                self.wfile.write(json.dumps({"documentos": docs}).encode('utf-8'))
                return

            elif action == 'cadastrar_documento':
                url = f"{sb_url}/rest/v1/documentos"
                payload = json.dumps({
                    "titulo": dados.get('titulo'),
                    "categoria": dados.get('categoria'),
                    "url_arquivo": dados.get('url_arquivo'),
                    "gestor_id": dados.get('gestor_id')
                }).encode('utf-8')
                req = urllib.request.Request(url, data=payload, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json'}, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return
                
            elif action == 'excluir_documento':
                did = dados.get('id')
                url = f"{sb_url}/rest/v1/documentos?id=eq.{did}"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='DELETE')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

        except Exception as e:
            self.wfile.write(json.dumps({"erro": str(e)}).encode('utf-8'))
