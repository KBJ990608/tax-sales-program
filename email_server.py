import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse
import smtplib
from email.message import EmailMessage

HOST_NAME = '127.0.0.1'
PORT_NUMBER = 8001

class RequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path != '/send':
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'Not found'}).encode('utf-8'))
            return

        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body)

        required_fields = ['smtpServer', 'smtpPort', 'senderEmail', 'smtpPassword', 'recipients', 'subject', 'message']
        for field in required_fields:
            if not data.get(field):
                self._set_headers(400)
                self.wfile.write(json.dumps({'error': f'{field} is required'}).encode('utf-8'))
                return

        try:
            sent_count, detail = self.send_email(data)
            self._set_headers(200)
            self.wfile.write(json.dumps({'sent': sent_count, 'detail': detail}).encode('utf-8'))
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({'error': 'Send failed', 'detail': str(e)}).encode('utf-8'))

    def send_email(self, data):
        smtp_server = data['smtpServer']
        smtp_port = int(data['smtpPort'])
        sender_email = data['senderEmail']
        sender_name = data.get('senderName', sender_email)
        smtp_password = data['smtpPassword']
        recipients = data['recipients']
        subject = data['subject']
        message_text = data['message']

        msg = EmailMessage()
        msg['Subject'] = subject
        msg['From'] = f'{sender_name} <{sender_email}>'
        msg['To'] = ', '.join(recipients)
        msg.set_content(message_text)

        server = smtplib.SMTP(smtp_server, smtp_port, timeout=20)
        server.starttls()
        server.login(sender_email, smtp_password)
        server.send_message(msg)
        server.quit()

        return len(recipients), f'{len(recipients)} recipients emailed via {smtp_server}:{smtp_port}'

if __name__ == '__main__':
    httpd = HTTPServer((HOST_NAME, PORT_NUMBER), RequestHandler)
    print(f'Serving email API on http://{HOST_NAME}:{PORT_NUMBER}')
    httpd.serve_forever()
