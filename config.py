# config.py
import os
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
load_dotenv()

# Configurações de email
EMAIL_CONFIG = {
    'smtp_server': os.getenv('SMTP_SERVER', 'smtp.gmail.com'),
    'smtp_port': int(os.getenv('SMTP_PORT', 587)),
    'email_remetente': os.getenv('EMAIL_REMETENTE', 'mjcursodatascience@gmail.com'),
    'email_senha': os.getenv('EMAIL_SENHA', 'sua-senha'),
    'email_destinatario': os.getenv('EMAIL_DESTINATARIO', 'quilomboviagens@gmail.com'),
    'assunto_padrao': os.getenv('ASSUNTO_PADRAO', 'Nova Viagem Cadastrada - Divisão Quilombola')
}