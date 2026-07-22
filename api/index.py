from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
import urllib.error
import mimetypes
import base64
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta

class handler(BaseHTTPRequestHandler):

    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def _obter_url_supabase(self):
        return "https://scotyvkhwptckrvrjzdi.supabase.co"

    def _safe_int(self, value):
        try: return int(value) if value else None
        except: return None

    # O Robô (Cron) bate aqui todos os dias via GET
    def do_GET(self):
        self._set_headers()
        
        if '/api/cron' in self.path:
            sb_url = self._obter_url_supabase()
            sb_key = os.environ.get('SUPABASE_SERVICE_KEY')
            email_remetente = os.environ.get('EMAIL_SMTP')
            senha_remetente = os.environ.get('SENHA_SMTP')
            
            if not email_remetente or not senha_remetente:
                self.wfile.write(json.dumps({"erro": "Credenciais de e-mail não configuradas no Vercel"}).encode('utf-8'))
                return

            try:
                req_gest = urllib.request.Request(f"{sb_url}/rest/v1/gestores?status=eq.Ativo&select=id,nome_gestor,email,nome_campanha_gabinete", headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req_gest) as response:
                    gestores = json.loads(response.read().decode('utf-8'))

                hoje = datetime.now()
                limite = hoje + timedelta(days=7)
                mes_atual = hoje.month

                for gestor in gestores:
                    if not gestor.get('email'): continue
                    
                    gid = gestor['id']
                    
                    req_ag = urllib.request.Request(f"{sb_url}/rest/v1/agenda?gestor_id=eq.{gid}&status=in.(Confirmado,Remarcado)", headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                    with urllib.request.urlopen(req_ag) as res_ag:
                        agenda = json.loads(res_ag.read().decode('utf-8'))
                    
                    agenda_filtrada = []
                    for a in agenda:
                        if a.get('data_evento'):
                            data_ev = datetime.strptime(a['data_evento'], '%Y-%m-%d')
                            if hoje.date() <= data_ev.date() <= limite.date():
                                agenda_filtrada.append(a)

                    req_func = urllib.request.Request(f"{sb_url}/rest/v1/funcionarios?gestor_id=eq.{gid}&status=eq.Ativo", headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                    with urllib.request.urlopen(req_func) as res_func:
                        funcs = json.loads(res_func.read().decode('utf-8'))
                    
                    nivers = []
                    for f in funcs:
                        if f.get('data_nascimento'):
                            parts = f['data_nascimento'].split('-')
                            if len(parts) == 3 and int(parts[1]) == mes_atual:
                                nivers.append(f)

                    if agenda_filtrada or nivers:
                        msg = MIMEMultipart()
                        msg['From'] = email_remetente
                        msg['To'] = gestor['email']
                        msg['Subject'] = f"Resumo Diário - {gestor['nome_campanha_gabinete']}"
                        
                        corpo = f"Olá {gestor['nome_gestor']},\nAqui está o seu resumo automático:\n\n"
                        corpo += "=== PRÓXIMOS COMPROMISSOS (7 DIAS) ===\n"
                        if agenda_filtrada:
                            for a in agenda_filtrada: corpo += f"- {a['data_evento']} às {a['hora_evento'][:5]}: {a['titulo']}\n"
                        else: corpo += "Nenhum compromisso.\n"
                        
                        corpo += "\n=== ANIVERSARIANTES DO MÊS ===\n"
                        if nivers:
                            for f in nivers: corpo += f"- Dia {f['data_nascimento'].split('-')[2]}: {f['nome']} ({f['cargo']})\n"
                        else: corpo += "Nenhum.\n"
                        
                        msg.attach(MIMEText(corpo, 'plain'))
                        
                        servidor = smtplib.SMTP('smtp.gmail.com', 587)
                        servidor.starttls()
                        servidor.login(email_remetente, senha_remetente)
                        servidor.send_message(msg)
                        servidor.quit()

                self.wfile.write(json.dumps({"sucesso": True, "msg": "E-mails enviados!"}).encode('utf-8'))
            except Exception as e:
                self.wfile.write(json.dumps({"erro": str(e)}).encode('utf-8'))
            return

        self.wfile.write(json.dumps({"status": "API Online"}).encode('utf-8'))

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

                req = urllib.request.Request(url_storage, data=file_bytes, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': content_type}, method='POST')
                try:
                    with urllib.request.urlopen(req): pass
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        self.wfile.write(json.dumps({"erro": "A pasta 'logos' não existe no Storage do Supabase."}).encode('utf-8'))
                        return
                    else:
                        self.wfile.write(json.dumps({"erro": f"Erro Storage Logos: {e.code}"}).encode('utf-8'))
                        return

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
            # ROTAS OPERACIONAIS
            # ==========================================
            elif action == 'verificar_login_gestor':
                senha_input = dados.get('senha')
                url = f"{sb_url}/rest/v1/gestores?senha_admin=eq.{senha_input}&status=eq.Ativo&select=id,nome_campanha_gabinete,cor_layout,url_logo,whatsapp"
                req = urllib.request.Request(url, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}'}, method='GET')
                with urllib.request.urlopen(req) as response:
                    res_data = json.loads(response.read().decode('utf-8'))
                if res_data:
                    self.wfile.write(json.dumps({"autorizado": True, "gestor": res_data[0]}).encode('utf-8'))
                else:
                    self.wfile.write(json.dumps({"autorizado": False, "mensagem": "Acesso suspenso ou inválido."}).encode('utf-8'))
                return

            # --- FUNCIONÁRIOS (RH) COM FOTO ---
            
            # Rota Nova: Upload de Foto 3x4
            elif action == 'upload_foto':
                file_base64 = dados.get('file_base64')
                filename = dados.get('filename')
                file_bytes = base64.b64decode(file_base64.split(",")[-1])
                url_storage = f"{sb_url}/storage/v1/object/fotos/{filename}"
                content_type = mimetypes.guess_type(filename)[0] or 'image/jpeg'

                req = urllib.request.Request(url_storage, data=file_bytes, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': content_type}, method='POST')
                try:
                    with urllib.request.urlopen(req): pass
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        self.wfile.write(json.dumps({"erro": "A pasta 'fotos' não existe no Supabase. Crie-a no painel do Supabase."}).encode('utf-8'))
                        return
                    else:
                        self.wfile.write(json.dumps({"erro": f"Erro Storage Fotos: {e.code}"}).encode('utf-8'))
                        return

                url_publica = f"{sb_url}/storage/v1/object/public/fotos/{filename}"
                self.wfile.write(json.dumps({"sucesso": True, "url_foto": url_publica}).encode('utf-8'))
                return

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
                    "email": dados.get('email'),
                    "documento": dados.get('documento'),
                    "endereco": dados.get('endereco'),
                    "conta_bancaria": dados.get('conta_bancaria'),
                    "data_nascimento": dados.get('data_nascimento'),
                    "url_foto": dados.get('url_foto'),
                    "gestor_id": self._safe_int(dados.get('gestor_id')),
                    "status": "Ativo"
                }).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'editar_funcionario':
                fid = dados.get('id')
                url = f"{sb_url}/rest/v1/funcionarios?id=eq.{fid}"
                body = {
                    "nome": dados.get('nome'),
                    "whatsapp": dados.get('whatsapp'),
                    "cargo": dados.get('cargo'),
                    "email": dados.get('email'),
                    "documento": dados.get('documento'),
                    "endereco": dados.get('endereco'),
                    "conta_bancaria": dados.get('conta_bancaria'),
                    "data_nascimento": dados.get('data_nascimento') 
                }
                if 'url_foto' in dados and dados['url_foto']:
                    body["url_foto"] = dados.get('url_foto')

                payload = json.dumps(body).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return
                
            elif action == 'alterar_status_funcionario':
                fid = dados.get('id')
                url = f"{sb_url}/rest/v1/funcionarios?id=eq.{fid}"
                status_bruto = dados.get('status')
                novo_status = status_bruto.capitalize() if status_bruto else "Ativo"
                payload = json.dumps({"status": novo_status}).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='PATCH')
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
                    "gestor_id": self._safe_int(dados.get('gestor_id')),
                    "status": "Ativo"
                }).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
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

            elif action == 'alterar_status_eleitor':
                eid = dados.get('id')
                url = f"{sb_url}/rest/v1/eleitores?id=eq.{eid}"
                payload = json.dumps({"status": dados.get('status')}).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='PATCH')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
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
                url = f"{sb_url}/rest/v1/agenda?gestor_id=eq.{gestor_id}&order=data_evento.asc,hora_evento.asc"
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
                    "tipo": 'Evento',
                    "data_evento": dados.get('data'),
                    "hora_evento": dados.get('hora'),
                    "gestor_id": self._safe_int(dados.get('gestor_id')),
                    "status": 'Confirmado'
                }).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
                with urllib.request.urlopen(req): pass
                self.wfile.write(json.dumps({"sucesso": True}).encode('utf-8'))
                return

            elif action == 'alterar_status_agenda':
                aid = dados.get('id')
                url = f"{sb_url}/rest/v1/agenda?id=eq.{aid}"
                update_data = {"status": dados.get('status')}
                
                if dados.get('data'): update_data["data_evento"] = dados.get('data')
                if dados.get('hora'): update_data["hora_evento"] = dados.get('hora')
                if 'justificativa' in dados: update_data["justificativa"] = dados.get('justificativa')
                
                payload = json.dumps(update_data).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='PATCH')
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

            # --- DOCUMENTOS MÍDIA ---
            elif action == 'upload_documento':
                file_base64 = dados.get('file_base64')
                filename = dados.get('filename')
                file_bytes = base64.b64decode(file_base64.split(",")[-1])
                url_storage = f"{sb_url}/storage/v1/object/documentos/{filename}"
                content_type = mimetypes.guess_type(filename)[0] or 'application/octet-stream'

                req = urllib.request.Request(url_storage, data=file_bytes, headers={'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': content_type}, method='POST')
                try:
                    with urllib.request.urlopen(req): pass
                except urllib.error.HTTPError as e:
                    if e.code == 404:
                        self.wfile.write(json.dumps({"erro": "A pasta (Bucket) 'documentos' não existe no Supabase. Crie-a no painel do Supabase."}).encode('utf-8'))
                        return
                    else:
                        self.wfile.write(json.dumps({"erro": f"Erro Storage Documentos: {e.code}"}).encode('utf-8'))
                        return

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
                    "gestor_id": self._safe_int(dados.get('gestor_id'))
                }).encode('utf-8')
                headers = {'apikey': sb_key, 'Authorization': f'Bearer {sb_key}', 'Content-Type': 'application/json', 'Prefer': 'return=representation'}
                req = urllib.request.Request(url, data=payload, headers=headers, method='POST')
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
