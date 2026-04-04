"""
AgroCaua Email Service — SMTP
Sends transactional emails for alerts, notifications, and contact forms.
"""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from queue import Queue
import threading
import time


# ─────────────────────────────────────────────
# Config from environment
# ─────────────────────────────────────────────
SMTP_HOST     = os.environ.get("SMTP_HOST",     "smtp.gmail.com")
SMTP_PORT     = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER     = os.environ.get("SMTP_USER",     "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM     = os.environ.get("SMTP_FROM",     SMTP_USER)
SMTP_FROM_NAME= os.environ.get("SMTP_FROM_NAME","AgroCaua")
SMTP_TLS      = os.environ.get("SMTP_TLS", "True").lower() == "true"
SMTP_SSL      = os.environ.get("SMTP_SSL", "False").lower() == "true"


_MAIL_Q: "Queue[tuple]" = Queue()
_WORKER_STARTED = False
_RETRY_MAX = 3
_RETRY_BASE_DELAY = 2.0

def _worker():
    while True:
        try:
            to_email, subject, html_body, attempt = _MAIL_Q.get()
        except Exception:
            time.sleep(0.2)
            continue
        ok = _send_immediate(to_email, subject, html_body)
        if not ok and attempt < _RETRY_MAX:
            delay = _RETRY_BASE_DELAY * (2 ** (attempt-1))
            time.sleep(delay)
            _MAIL_Q.put((to_email, subject, html_body, attempt+1))
        _MAIL_Q.task_done()

def _start_worker_once():
    global _WORKER_STARTED
    if not _WORKER_STARTED:
        th = threading.Thread(target=_worker, daemon=True)
        th.start()
        _WORKER_STARTED = True

def _enqueue(to_email: str, subject: str, html_body: str) -> bool:
    _start_worker_once()
    try:
        _MAIL_Q.put((to_email, subject, html_body, 1))
        return True
    except Exception as e:
        print(f"[Email] QUEUE error: {e}")
        return False

def _send_immediate(to_email: str, subject: str, html_body: str) -> bool:
    """
    Core send function. Returns True on success, False on failure.
    Silently logs errors so callers never crash.
    """
    if not SMTP_USER or not SMTP_PASSWORD:
        print(f"[Email] SMTP not configured — skipping send to {to_email}")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{SMTP_FROM_NAME} <{SMTP_FROM}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        if SMTP_SSL:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)

        if SMTP_TLS and not SMTP_SSL:
            server.starttls()

        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_email, msg.as_string())
        server.quit()
        print(f"[Email] Sent '{subject}' to {to_email}")
        return True
    except Exception as e:
        print(f"[Email] ERROR sending to {to_email}: {e}")
        return False

def _send(to_email: str, subject: str, html_body: str) -> bool:
    # Enfileirar com retry automático
    return _enqueue(to_email, subject, html_body)


# ─────────────────────────────────────────────
# Base HTML template
# ─────────────────────────────────────────────
def _base_template(title: str, content: str, cta_label: str = None, cta_url: str = "#") -> str:
    cta_html = f"""
    <div style="text-align:center;margin:24px 0">
      <a href="{cta_url}" style="display:inline-block;padding:12px 28px;background:linear-gradient(135deg,#2E8B57,#38A169);color:white;border-radius:8px;text-decoration:none;font-weight:700;font-size:14px">{cta_label}</a>
    </div>""" if cta_label else ""

    return f"""<!DOCTYPE html>
<html lang="pt"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{title}</title></head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:'Segoe UI',Arial,sans-serif">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 16px">
    <tr><td align="center">
      <table width="600" style="background:white;border-radius:16px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.08);max-width:100%">
        <!-- Header -->
        <tr><td style="background:linear-gradient(135deg,#1a4d1a,#2E8B57);padding:24px 32px;text-align:center">
          <div style="font-size:24px;font-weight:800;color:white;letter-spacing:-0.5px">🌾 AgroCaua</div>
          <div style="font-size:12px;color:rgba(255,255,255,0.75);margin-top:4px">Sistema de Monitoramento Agrícola</div>
        </td></tr>
        <!-- Body -->
        <tr><td style="padding:32px">
          <h2 style="color:#111827;font-size:20px;margin:0 0 16px">{title}</h2>
          {content}
          {cta_html}
        </td></tr>
        <!-- Footer -->
        <tr><td style="background:#f9fafb;padding:16px 32px;text-align:center;border-top:1px solid #e5e7eb">
          <p style="color:#9ca3af;font-size:12px;margin:0">© {datetime.now().year} AgroCaua · Sistema de Monitoramento Agrícola Inteligente</p>
          <p style="color:#9ca3af;font-size:11px;margin:4px 0 0">Este é um email automático. Por favor não responda diretamente.</p>
        </td></tr>
      </table>
    </td></tr>
  </table>
</body></html>"""


# ─────────────────────────────────────────────
# Alerta IoT para agricultor
# ─────────────────────────────────────────────
ALERT_ACTIONS = {
    "Praga":   {"icon": "🐛", "cor": "#dc2626", "acao": "Inicie o protocolo de controlo de pragas. Aplique pesticida seletivo conforme rótulo (g/ha). Monitore a área nas próximas 24h."},
    "Solo":    {"icon": "💧", "cor": "#2563eb", "acao": "Ligue a bomba de irrigação imediatamente. A humidade do solo está abaixo do limite crítico. Irrigue até atingir 60-80% da capacidade de campo."},
    "Clima":   {"icon": "🌡️", "cor": "#f59e0b", "acao": "Verifique se há risco de queima foliar (temp. alta) ou geada (temp. baixa). Considere instalação de sombrite ou cobertura de proteção."},
    "Sensor":  {"icon": "📡", "cor": "#6b7280", "acao": "Verifique a alimentação elétrica e a ligação à rede Wi-Fi do sensor. Se a bateria estiver fraca, substitua ou recarregue."},
}

def send_alert_farmer(to_email: str, nome: str, tipo: str, mensagem: str, severidade: str):
    info = ALERT_ACTIONS.get(tipo, {"icon": "⚠️", "cor": "#f59e0b", "acao": "Verifique o sistema imediatamente."})
    sev_bg  = "#fef2f2" if severidade == "crítico" else "#fef9c3"
    sev_col = "#dc2626"  if severidade == "crítico" else "#854d0e"

    content = f"""
    <p style="color:#6b7280;font-size:14px;line-height:1.6">Olá <strong>{nome}</strong>,<br>
    O seu sistema AgroCaua gerou um novo alerta que requer a sua atenção.</p>

    <div style="background:{sev_bg};border-left:4px solid {info['cor']};border-radius:8px;padding:16px;margin:16px 0">
      <div style="font-size:20px;margin-bottom:8px">{info['icon']} <strong style="color:{sev_col}">Alerta {severidade.upper()}</strong></div>
      <p style="color:#374151;margin:0;font-size:14px">{mensagem}</p>
    </div>

    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin:16px 0">
      <strong style="color:#166534;font-size:13px">✅ AÇÃO RECOMENDADA:</strong>
      <p style="color:#166534;margin:8px 0 0;font-size:14px">{info['acao']}</p>
    </div>

    <p style="color:#9ca3af;font-size:12px">Aceda ao seu painel para mais detalhes e para registar a ação tomada.</p>"""

    return _send(to_email, f"🚨 Alerta {tipo} — {severidade.upper()} | AgroCaua", _base_template(f"Alerta: {tipo}", content, "Ver no Painel", "http://localhost:5000/dashboard/alertas"))


# ─────────────────────────────────────────────
# Resposta do admin a mensagem do agricultor
# ─────────────────────────────────────────────
def send_message_reply(to_email: str, nome: str, assunto: str, resposta: str, respondido_por: str):
    content = f"""
    <p style="color:#6b7280;font-size:14px">Olá <strong>{nome}</strong>,</p>
    <p style="color:#6b7280;font-size:14px">A sua mensagem "<strong>{assunto}</strong>" foi respondida pela equipa AgroCaua.</p>

    <div style="background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;padding:16px;margin:16px 0">
      <strong style="color:#166534;font-size:12px;text-transform:uppercase">Resposta de {respondido_por}:</strong>
      <p style="color:#374151;margin:8px 0 0;font-size:14px;line-height:1.7">{resposta}</p>
    </div>

    <p style="color:#9ca3af;font-size:12px">Pode responder diretamente através do módulo Apoio &amp; Reclamações no seu painel.</p>"""

    return _send(to_email, f"Re: {assunto} | AgroCaua Suporte", _base_template("Resposta à sua mensagem", content, "Ir para Apoio", "http://localhost:5000/dashboard/apoio"))


# ─────────────────────────────────────────────
# Formulário de contacto do site (landing)
# ─────────────────────────────────────────────
def send_contact_form_confirmation(to_email: str, nome: str, assunto: str):
    content = f"""
    <p style="color:#6b7280;font-size:14px">Olá <strong>{nome}</strong>,</p>
    <p style="color:#6b7280;font-size:14px">Recebemos a sua mensagem sobre "<strong>{assunto}</strong>". Entraremos em contacto em breve.</p>
    <p style="color:#6b7280;font-size:14px">Obrigado pelo seu interesse no AgroCaua!</p>"""

    return _send(to_email, "Mensagem recebida — AgroCaua", _base_template("Mensagem recebida com sucesso!", content))


def send_contact_form_to_admin(admin_email: str, nome: str, email: str, telefone: str, assunto: str, mensagem: str):
    content = f"""
    <p style="color:#6b7280;font-size:14px">Novo contacto recebido através do formulário do site.</p>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600;width:130px">Nome</td><td style="padding:8px;border:1px solid #e5e7eb">{nome}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600">Email</td><td style="padding:8px;border:1px solid #e5e7eb">{email}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600">Telefone</td><td style="padding:8px;border:1px solid #e5e7eb">{telefone or '—'}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600">Assunto</td><td style="padding:8px;border:1px solid #e5e7eb">{assunto}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600;vertical-align:top">Mensagem</td><td style="padding:8px;border:1px solid #e5e7eb;white-space:pre-wrap">{mensagem}</td></tr>
    </table>"""

    return _send(admin_email, f"📩 Novo contacto: {assunto}", _base_template("Novo Formulário de Contacto", content))


# ─────────────────────────────────────────────
# Notificação de alerta crítico do agricultor para admin
# ─────────────────────────────────────────────
def send_critical_alert_to_admin(admin_email: str, nome_agricultor: str, email_agricultor: str, assunto: str, conteudo: str):
    content = f"""
    <div style="background:#fef2f2;border-left:4px solid #dc2626;border-radius:8px;padding:16px;margin-bottom:16px">
      <strong style="color:#dc2626">🚨 ALERTA CRÍTICO recebido de agricultor</strong>
    </div>
    <table style="width:100%;border-collapse:collapse;font-size:14px">
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600;width:130px">Agricultor</td><td style="padding:8px;border:1px solid #e5e7eb">{nome_agricultor}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600">Email</td><td style="padding:8px;border:1px solid #e5e7eb">{email_agricultor}</td></tr>
      <tr><td style="padding:8px;background:#f9fafb;border:1px solid #e5e7eb;font-weight:600">Assunto</td><td style="padding:8px;border:1px solid #e5e7eb">{assunto}</td></tr>
      <tr><td style="padding:8px;background:#fef2f2;border:1px solid #fecaca;font-weight:600;vertical-align:top">Mensagem</td><td style="padding:8px;border:1px solid #fecaca;white-space:pre-wrap;color:#991b1b">{conteudo}</td></tr>
    </table>"""

    return _send(admin_email, f"🚨 ALERTA CRÍTICO de {nome_agricultor}", _base_template("Alerta Crítico do Agricultor", content, "Ver Alertas", "http://localhost:5000/admin"))


# ─────────────────────────────────────────────
# Bem-vindo ao registo
# ─────────────────────────────────────────────
def send_welcome_email(to_email: str, nome: str):
    content = f"""
    <p style="color:#6b7280;font-size:14px">Olá <strong>{nome}</strong>,</p>
    <p style="color:#6b7280;font-size:14px">A sua conta AgroCaua foi criada com sucesso! Agora pode aceder ao painel de monitoramento da sua fazenda.</p>
    <ul style="color:#374151;font-size:14px;line-height:2">
      <li>📊 Monitoramento em tempo real de sensores</li>
      <li>🌡️ Dados de clima, solo e pragas</li>
      <li>🔔 Alertas automáticos e recomendações</li>
      <li>📧 Suporte direto com a equipa</li>
    </ul>"""

    return _send(to_email, "Bem-vindo ao AgroCaua! 🌾", _base_template("Conta criada com sucesso!", content, "Aceder ao Painel", "http://localhost:5000/dashboard"))
