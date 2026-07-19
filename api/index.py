from http.server import BaseHTTPRequestHandler
import json
import os

class handler(BaseHTTPRequestHandler):

    def do_POST(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

        # Ler os dados enviados pelo master.html
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        dados = json.loads(post_data.decode('utf-8'))
        
        senha_digitada = dados.get('senha')

        # Puxa a senha da variável exata definida na Vercel
        senha_correta = os.environ.get('USER_SENHA')

        # Validação
        if senha_digitada == senha_correta:
            resposta = {"autorizado": True, "mensagem": "Acesso concedido!"}
        else:
            resposta = {"autorizado": False, "mensagem": "Senha incorreta."}

        self.wfile.write(json.dumps(resposta).encode('utf-8'))
        return
