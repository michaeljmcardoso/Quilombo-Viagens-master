import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from config import EMAIL_CONFIG

def enviar_email_confirmacao(viagem_data, orcamento):
    """
    Envia um email de confirmação quando uma nova viagem é cadastrada
    """
    try:
        # Configurações do email
        remetente = EMAIL_CONFIG['email_remetente']
        senha = EMAIL_CONFIG['email_senha']
        destinatario = EMAIL_CONFIG['email_destinatario']
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"{EMAIL_CONFIG['assunto_padrao']} - {viagem_data['comunidade']}"
        msg['From'] = remetente
        msg['To'] = destinatario
        
        # Criar corpo do email em HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #2C1810, #4A2F1A); padding: 20px; border-radius: 8px; text-align: center; color: white; margin-bottom: 20px; }}
                .header h1 {{ color: #FFD700; margin: 0; }}
                .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
                .info-label {{ font-weight: bold; color: #555; }}
                .info-value {{ color: #333; }}
                .total {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center; }}
                .total-value {{ font-size: 24px; color: #2C1810; font-weight: bold; }}
                .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }}
                .badge {{ background: #FFD700; color: #2C1810; padding: 5px 10px; border-radius: 5px; font-weight: bold; }}
                .details {{ margin: 20px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🏘️ Divisão Quilombola</h1>
                    <p style="color: #DAA520;">Sistema de Cadastramento de Viagens</p>
                </div>
                
                <h2 style="color: #2C1810;">✅ Nova Viagem Cadastrada!</h2>
                <p style="color: #666;">Uma nova viagem foi cadastrada no sistema. Confira os detalhes abaixo:</p>
                
                <div class="details">
                    <div class="info-row">
                        <span class="info-label">🏘️ Comunidade:</span>
                        <span class="info-value">{viagem_data['comunidade']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📍 Município:</span>
                        <span class="info-value">{viagem_data['municipio']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📅 Período:</span>
                        <span class="info-value">{viagem_data['data_inicio']} a {viagem_data['data_fim']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📆 Dias:</span>
                        <span class="info-value">{viagem_data['dias_totais']} dia(s)</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">👥 Servidores:</span>
                        <span class="info-value">{viagem_data['quantidade_servidores']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">🏨 Diárias por Servidor:</span>
                        <span class="info-value">{viagem_data['diarias_por_servidor']:.1f}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">🛣️ Distância Rodoviária:</span>
                        <span class="info-value">{viagem_data['distancia_rodoviaria']:.1f} km</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">🚙 Distância Local:</span>
                        <span class="info-value">{viagem_data['distancia_local']:.1f} km</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">📋 Atividade:</span>
                        <span class="info-value"><span class="badge">{viagem_data['tipo_atividade']}</span></span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">👤 Cadastrante:</span>
                        <span class="info-value">{viagem_data['cadastrante']}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">🕐 Data Cadastro:</span>
                        <span class="info-value">{viagem_data['data_cadastro']}</span>
                    </div>
                </div>
                
                <div class="total">
                    <h3 style="color: #2C1810;">💰 Orçamento</h3>
                    <div style="display: flex; justify-content: space-around; margin: 10px 0;">
                        <div>
                            <div style="font-size: 12px; color: #666;">Diárias</div>
                            <div style="font-size: 18px; color: #2C1810; font-weight: bold;">{formatar_moeda_html(orcamento['total_diarias_valor'])}</div>
                        </div>
                        <div>
                            <div style="font-size: 12px; color: #666;">Combustível</div>
                            <div style="font-size: 18px; color: #2C1810; font-weight: bold;">{formatar_moeda_html(orcamento['total_combustivel'])}</div>
                        </div>
                    </div>
                    <hr style="border: 1px solid #eee; margin: 10px 0;">
                    <div>
                        <div style="font-size: 14px; color: #666;">TOTAL GERAL</div>
                        <div class="total-value">{formatar_moeda_html(orcamento['total_geral'])}</div>
                    </div>
                </div>
                
                <div class="footer">
                    <p>Este é um email automático gerado pelo Sistema QuilomboViagens.</p>
                    <p>© 2026 SISCOV - Todos os direitos reservados.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Função auxiliar para formatar moeda no HTML
        def formatar_moeda_html(valor):
            return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Criar parte HTML
        html_part = MIMEText(html, 'html')
        msg.attach(html_part)
        
        # Enviar email
        try:
            server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
            server.starttls()
            server.login(remetente, senha)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"Erro ao enviar email: {str(e)}")
            return False
            
    except Exception as e:
        print(f"Erro geral no envio de email: {str(e)}")
        return False