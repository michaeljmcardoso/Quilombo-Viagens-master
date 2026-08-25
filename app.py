import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import plotly.express as px
import base64
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
import io
import sqlite3
import json
import constantes
import github_sync
from github_sync import sincronizar_github, testar_github, GitHubSync

# Carrega variáveis de ambiente
load_dotenv()

# Configuração da página
st.set_page_config(
    page_title="QuilomboViagens - Sistema de Viagens da Divisão Quilombola",
    page_icon="🏘️",
    layout="wide"
)

# Valores fixos
DIARIA_VALOR = 335.00
DIESEL_VALOR = 6.95
CONSUMO_MEDIO = 10.0
MEIA_DIARIA = DIARIA_VALOR / 2

# Configurações de email
EMAIL_ENABLED = os.getenv('EMAIL_ENABLED', 'False').lower() == 'true'
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
EMAIL_REMETENTE = os.getenv('EMAIL_REMETENTE', '')
EMAIL_SENHA = os.getenv('EMAIL_SENHA', '')
EMAIL_DESTINATARIO = os.getenv('EMAIL_DESTINATARIO', '')

# ==================== BANCO DE DADOS ====================

class Database:
    """Classe para gerenciar o banco de dados SQLite"""
    
    def __init__(self, db_file="viagens.db"):
        self.db_file = db_file
        self.init_db()
        self.migrar_tabela()
    
    def get_connection(self):
        """Retorna uma conexão com o banco de dados"""
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        """Inicializa o banco de dados com as tabelas necessárias"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Criar tabela de viagens
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS viagens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                comunidade TEXT NOT NULL,
                municipio TEXT NOT NULL,
                data_inicio TEXT NOT NULL,
                data_fim TEXT NOT NULL,
                quantidade_servidores INTEGER NOT NULL,
                diarias_por_servidor REAL NOT NULL,
                dias_totais INTEGER NOT NULL,
                distancia_rodoviaria REAL NOT NULL,
                distancia_local REAL NOT NULL,
                distancia_total REAL NOT NULL,
                tipo_atividade TEXT NOT NULL,
                cadastrante TEXT NOT NULL,
                email_usuario TEXT,
                data_cadastro TEXT NOT NULL,
                orcamento_diarias_valor REAL NOT NULL,
                orcamento_combustivel REAL NOT NULL,
                orcamento_total_geral REAL NOT NULL,
                orcamento_diarias_servidor REAL NOT NULL,
                orcamento_litros_rodoviario REAL NOT NULL,
                orcamento_litros_local REAL NOT NULL,
                orcamento_total_litros REAL NOT NULL,
                orcamento_combustivel_rodoviario REAL NOT NULL,
                orcamento_combustivel_local REAL NOT NULL
            )
        ''')
        
        # Criar tabela de feedback (ANÔNIMO)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_resposta TEXT NOT NULL,
                facilidade_uso TEXT,
                layout_intuitivo TEXT,
                encontrar_funcionalidades TEXT,
                funcionalidades_usa TEXT,
                funcionalidade_importante TEXT,
                funcionalidade_falta TEXT,
                velocidade_sistema TEXT,
                atende_necessidades TEXT,
                tempo_cadastro TEXT,
                qualidade_extratos TEXT,
                relatorios_claros TEXT,
                info_relatorios TEXT,
                recebe_email TEXT,
                email_claro TEXT,
                email_melhorias TEXT,
                importancia_banco TEXT,
                confianca_dados TEXT,
                nota_geral TEXT,
                recomendaria TEXT,
                sugestoes_melhoria TEXT,
                mais_gosta TEXT,
                menos_gosta TEXT,
                continuaria_usando TEXT,
                expansao_futuro TEXT,
                comentarios_adicionais TEXT,
                data_cadastro TEXT
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def migrar_tabela(self):
        """Migra a tabela para a versão mais recente se necessário"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verificar colunas existentes na tabela viagens
        cursor.execute("PRAGMA table_info(viagens)")
        colunas_viagens = [col[1] for col in cursor.fetchall()]
        
        # Adicionar colunas faltantes na tabela viagens
        if 'orcamento_combustivel_local' not in colunas_viagens:
            cursor.execute('ALTER TABLE viagens ADD COLUMN orcamento_combustivel_local REAL DEFAULT 0.0')
            print("✅ Coluna orcamento_combustivel_local adicionada na tabela viagens")
        
        conn.commit()
        conn.close()
    
    def salvar_feedback(self, feedback_data):
        """Salva um feedback anônimo no banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feedback (
                data_resposta,
                facilidade_uso, layout_intuitivo, encontrar_funcionalidades,
                funcionalidades_usa, funcionalidade_importante, funcionalidade_falta,
                velocidade_sistema, atende_necessidades, tempo_cadastro,
                qualidade_extratos, relatorios_claros, info_relatorios,
                recebe_email, email_claro, email_melhorias,
                importancia_banco, confianca_dados,
                nota_geral, recomendaria,
                sugestoes_melhoria, mais_gosta, menos_gosta,
                continuaria_usando, expansao_futuro, comentarios_adicionais,
                data_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            feedback_data['data_resposta'],
            feedback_data['facilidade_uso'],
            feedback_data['layout_intuitivo'],
            feedback_data['encontrar_funcionalidades'],
            feedback_data['funcionalidades_usa'],
            feedback_data['funcionalidade_importante'],
            feedback_data['funcionalidade_falta'],
            feedback_data['velocidade_sistema'],
            feedback_data['atende_necessidades'],
            feedback_data['tempo_cadastro'],
            feedback_data['qualidade_extratos'],
            feedback_data['relatorios_claros'],
            feedback_data['info_relatorios'],
            feedback_data['recebe_email'],
            feedback_data['email_claro'],
            feedback_data['email_melhorias'],
            feedback_data['importancia_banco'],
            feedback_data['confianca_dados'],
            feedback_data['nota_geral'],
            feedback_data['recomendaria'],
            feedback_data['sugestoes_melhoria'],
            feedback_data['mais_gosta'],
            feedback_data['menos_gosta'],
            feedback_data['continuaria_usando'],
            feedback_data['expansao_futuro'],
            feedback_data['comentarios_adicionais'],
            feedback_data['data_cadastro']
        ))
        
        feedback_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return feedback_id
    
    def carregar_feedbacks(self):
        """Carrega todos os feedbacks do banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM feedback ORDER BY id DESC')
        rows = cursor.fetchall()
        conn.close()
        
        feedbacks = []
        for row in rows:
            feedback = {
                'id': row[0],
                'data_resposta': row[1],
                'facilidade_uso': row[2],
                'layout_intuitivo': row[3],
                'encontrar_funcionalidades': row[4],
                'funcionalidades_usa': row[5],
                'funcionalidade_importante': row[6],
                'funcionalidade_falta': row[7],
                'velocidade_sistema': row[8],
                'atende_necessidades': row[9],
                'tempo_cadastro': row[10],
                'qualidade_extratos': row[11],
                'relatorios_claros': row[12],
                'info_relatorios': row[13],
                'recebe_email': row[14],
                'email_claro': row[15],
                'email_melhorias': row[16],
                'importancia_banco': row[17],
                'confianca_dados': row[18],
                'nota_geral': row[19],
                'recomendaria': row[20],
                'sugestoes_melhoria': row[21],
                'mais_gosta': row[22],
                'menos_gosta': row[23],
                'continuaria_usando': row[24],
                'expansao_futuro': row[25],
                'comentarios_adicionais': row[26],
                'data_cadastro': row[27]
            }
            feedbacks.append(feedback)
        
        return feedbacks
    
    def salvar_viagem(self, viagem_data):
        """Salva uma viagem no banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Converter listas para JSON strings para armazenamento
        comunidade_json = json.dumps(viagem_data['comunidade'])
        municipio_json = json.dumps(viagem_data['municipio'])
        tipo_atividade_json = json.dumps(viagem_data['tipo_atividade'])
        
        orcamento = viagem_data['orcamento']
        
        cursor.execute('''
            INSERT INTO viagens (
                comunidade, municipio, data_inicio, data_fim,
                quantidade_servidores, diarias_por_servidor, dias_totais,
                distancia_rodoviaria, distancia_local, distancia_total,
                tipo_atividade, cadastrante, email_usuario, data_cadastro,
                orcamento_diarias_valor, orcamento_combustivel, orcamento_total_geral,
                orcamento_diarias_servidor, orcamento_litros_rodoviario,
                orcamento_litros_local, orcamento_total_litros,
                orcamento_combustivel_rodoviario, orcamento_combustivel_local
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            comunidade_json, municipio_json,
            viagem_data['data_inicio'], viagem_data['data_fim'],
            viagem_data['quantidade_servidores'],
            viagem_data['diarias_por_servidor'],
            viagem_data['dias_totais'],
            viagem_data['distancia_rodoviaria'],
            viagem_data['distancia_local'],
            viagem_data['distancia_total'],
            tipo_atividade_json,
            viagem_data['cadastrante'],
            viagem_data.get('email_usuario', ''),
            viagem_data['data_cadastro'],
            orcamento['total_diarias_valor'],
            orcamento['total_combustivel'],
            orcamento['total_geral'],
            orcamento['total_diarias_servidor'],
            orcamento['litros_rodoviario'],
            orcamento['litros_local'],
            orcamento['total_litros'],
            orcamento['total_combustivel_rodoviario'],
            orcamento['total_combustivel_local']
        ))
        
        viagem_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        return viagem_id
    
    def atualizar_viagem(self, viagem_id, viagem_data):
        """Atualiza uma viagem existente no banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Converter listas para JSON strings
        comunidade_json = json.dumps(viagem_data['comunidade'])
        municipio_json = json.dumps(viagem_data['municipio'])
        tipo_atividade_json = json.dumps(viagem_data['tipo_atividade'])
        
        orcamento = viagem_data['orcamento']
        
        cursor.execute('''
            UPDATE viagens SET
                comunidade = ?,
                municipio = ?,
                data_inicio = ?,
                data_fim = ?,
                quantidade_servidores = ?,
                diarias_por_servidor = ?,
                dias_totais = ?,
                distancia_rodoviaria = ?,
                distancia_local = ?,
                distancia_total = ?,
                tipo_atividade = ?,
                cadastrante = ?,
                email_usuario = ?,
                data_cadastro = ?,
                orcamento_diarias_valor = ?,
                orcamento_combustivel = ?,
                orcamento_total_geral = ?,
                orcamento_diarias_servidor = ?,
                orcamento_litros_rodoviario = ?,
                orcamento_litros_local = ?,
                orcamento_total_litros = ?,
                orcamento_combustivel_rodoviario = ?,
                orcamento_combustivel_local = ?
            WHERE id = ?
        ''', (
            comunidade_json, municipio_json,
            viagem_data['data_inicio'], viagem_data['data_fim'],
            viagem_data['quantidade_servidores'],
            viagem_data['diarias_por_servidor'],
            viagem_data['dias_totais'],
            viagem_data['distancia_rodoviaria'],
            viagem_data['distancia_local'],
            viagem_data['distancia_total'],
            tipo_atividade_json,
            viagem_data['cadastrante'],
            viagem_data.get('email_usuario', ''),
            viagem_data['data_cadastro'],
            orcamento['total_diarias_valor'],
            orcamento['total_combustivel'],
            orcamento['total_geral'],
            orcamento['total_diarias_servidor'],
            orcamento['litros_rodoviario'],
            orcamento['litros_local'],
            orcamento['total_litros'],
            orcamento['total_combustivel_rodoviario'],
            orcamento['total_combustivel_local'],
            viagem_id
        ))
        
        conn.commit()
        conn.close()
    
    def carregar_viagens(self):
        """Carrega todas as viagens do banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Verificar quais colunas existem na tabela
        cursor.execute("PRAGMA table_info(viagens)")
        colunas = [col[1] for col in cursor.fetchall()]
        
        # Construir SELECT com as colunas que existem
        if 'orcamento_combustivel_local' in colunas:
            cursor.execute('''
                SELECT 
                    id, comunidade, municipio, data_inicio, data_fim,
                    quantidade_servidores, diarias_por_servidor, dias_totais,
                    distancia_rodoviaria, distancia_local, distancia_total,
                    tipo_atividade, cadastrante, email_usuario, data_cadastro,
                    orcamento_diarias_valor, orcamento_combustivel, orcamento_total_geral,
                    orcamento_diarias_servidor, orcamento_litros_rodoviario,
                    orcamento_litros_local, orcamento_total_litros,
                    orcamento_combustivel_rodoviario, orcamento_combustivel_local
                FROM viagens ORDER BY id DESC
            ''')
        else:
            # Fallback para versão antiga da tabela
            cursor.execute('''
                SELECT 
                    id, comunidade, municipio, data_inicio, data_fim,
                    quantidade_servidores, diarias_por_servidor, dias_totais,
                    distancia_rodoviaria, distancia_local, distancia_total,
                    tipo_atividade, cadastrante, email_usuario, data_cadastro,
                    orcamento_diarias_valor, orcamento_combustivel, orcamento_total_geral,
                    orcamento_diarias_servidor, orcamento_litros_rodoviario,
                    orcamento_litros_local, orcamento_total_litros,
                    orcamento_combustivel_rodoviario
                FROM viagens ORDER BY id DESC
            ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        viagens = []
        for row in rows:
            # Converter JSON strings de volta para listas
            comunidade = json.loads(row[1])
            municipio = json.loads(row[2])
            tipo_atividade = json.loads(row[11])
            
            # Verificar quantas colunas foram retornadas
            if len(row) == 24:  # Versão completa
                orcamento = {
                    'total_diarias_valor': row[15],
                    'total_combustivel': row[16],
                    'total_geral': row[17],
                    'total_diarias_servidor': row[18],
                    'litros_rodoviario': row[19],
                    'litros_local': row[20],
                    'total_litros': row[21],
                    'total_combustivel_rodoviario': row[22],
                    'total_combustivel_local': row[23],
                    'dias_totais': row[7],
                    'diarias_por_servidor': row[6],
                    'distancia_rodoviaria': row[8],
                    'distancia_local': row[9],
                    'distancia_total': row[10]
                }
            else:  # Versão antiga (sem orcamento_combustivel_local)
                orcamento = {
                    'total_diarias_valor': row[15],
                    'total_combustivel': row[16],
                    'total_geral': row[17],
                    'total_diarias_servidor': row[18],
                    'litros_rodoviario': row[19],
                    'litros_local': row[20],
                    'total_litros': row[21],
                    'total_combustivel_rodoviario': row[22],
                    'total_combustivel_local': 0.0,  # Valor padrão para versões antigas
                    'dias_totais': row[7],
                    'diarias_por_servidor': row[6],
                    'distancia_rodoviaria': row[8],
                    'distancia_local': row[9],
                    'distancia_total': row[10]
                }
            
            viagem = {
                'id': row[0],
                'comunidade': comunidade,
                'municipio': municipio,
                'data_inicio': row[3],
                'data_fim': row[4],
                'quantidade_servidores': row[5],
                'diarias_por_servidor': row[6],
                'dias_totais': row[7],
                'distancia_rodoviaria': row[8],
                'distancia_local': row[9],
                'distancia_total': row[10],
                'tipo_atividade': tipo_atividade,
                'cadastrante': row[12],
                'email_usuario': row[13],
                'data_cadastro': row[14],
                'orcamento': orcamento
            }
            viagens.append(viagem)
        
        return viagens
    
    def deletar_todas_viagens(self):
        """Deleta todas as viagens do banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM viagens')
        conn.commit()
        conn.close()
    
    def deletar_viagem(self, viagem_id):
        """Deleta uma viagem específica do banco de dados"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM viagens WHERE id = ?', (viagem_id,))
        conn.commit()
        conn.close()

# Inicializar banco de dados
db = Database()

# ==================== FIM BANCO DE DADOS ====================

def comparar_alteracoes(viagem_antiga, viagem_nova):
    """
    Compara duas versões da viagem e retorna um dicionário com as alterações
    """
    alteracoes = []
    
    # Função para converter lista para string
    def list_to_str(valor):
        if isinstance(valor, list):
            return ", ".join(valor)
        return str(valor)
    
    # Campos a serem comparados
    campos = {
        'comunidade': '🏘️ Comunidade',
        'municipio': '📍 Município',
        'data_inicio': '📅 Data Início',
        'data_fim': '📅 Data Fim',
        'quantidade_servidores': '👥 Número de Servidores',
        'diarias_por_servidor': '🏨 Diárias por Servidor',
        'dias_totais': '📆 Dias Totais',
        'distancia_rodoviaria': '🛣️ Distância Rodoviária',
        'distancia_local': '🚙 Distância Local',
        'distancia_total': '📏 Distância Total',
        'tipo_atividade': '📋 Tipo de Atividade',
        'cadastrante': '👤 Cadastrante'
    }
    
    for campo, label in campos.items():
        valor_antigo = viagem_antiga.get(campo, '')
        valor_novo = viagem_nova.get(campo, '')
        
        # Converter listas para string para comparação
        valor_antigo_str = list_to_str(valor_antigo)
        valor_novo_str = list_to_str(valor_novo)
        
        if valor_antigo_str != valor_novo_str:
            alteracoes.append({
                'campo': label,
                'valor_antigo': valor_antigo_str if valor_antigo_str else '(vazio)',
                'valor_novo': valor_novo_str if valor_novo_str else '(vazio)'
            })
    
    # Comparar orçamento
    orc_antigo = viagem_antiga.get('orcamento', {})
    orc_novo = viagem_nova.get('orcamento', {})
    
    campos_orcamento = {
        'total_diarias_valor': '💰 Total Diárias',
        'total_combustivel': '⛽ Total Combustível',
        'total_geral': '💵 Total Geral'
    }
    
    for campo, label in campos_orcamento.items():
        valor_antigo = orc_antigo.get(campo, 0)
        valor_novo = orc_novo.get(campo, 0)
        
        if valor_antigo != valor_novo:
            alteracoes.append({
                'campo': label,
                'valor_antigo': formatar_moeda(valor_antigo),
                'valor_novo': formatar_moeda(valor_novo)
            })
    
    return alteracoes

def enviar_email_confirmacao(viagem_data, orcamento, email_usuario=None):
    """
    Envia email de confirmação REAL quando uma nova viagem é cadastrada
    Pode enviar para o destinatário principal e para o usuário
    """
    try:
        if not EMAIL_ENABLED:
            print("⚠️ Email desabilitado no .env")
            return False, False
        
        if not EMAIL_REMETENTE or not EMAIL_SENHA:
            print("⚠️ Configurações de email incompletas")
            return False, False
        
        def formatar_moeda_html(valor):
            return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Criar corpo do email (MESMO para todos os destinatários)
        html = criar_corpo_email(viagem_data, orcamento, formatar_moeda_html)
        
        # Lista de destinatários (inclui o principal e o usuário)
        destinatarios = []
        if EMAIL_DESTINATARIO:
            destinatarios.append(EMAIL_DESTINATARIO)
        if email_usuario and email_usuario != EMAIL_DESTINATARIO:
            destinatarios.append(email_usuario)
        
        if not destinatarios:
            return False, []
        
        # Enviar o MESMO email para cada destinatário
        enviados = []
        for destinatario in destinatarios:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"✅ Nova Viagem Cadastrada - {viagem_data['comunidade']}"
                msg['From'] = EMAIL_REMETENTE
                msg['To'] = destinatario
                
                # MESMO corpo HTML para todos
                html_part = MIMEText(html, 'html')
                msg.attach(html_part)
                
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(EMAIL_REMETENTE, EMAIL_SENHA)
                server.send_message(msg)
                server.quit()
                
                enviados.append(destinatario)
                print(f"✅ Email enviado para: {destinatario}")
            except Exception as e:
                print(f"❌ Erro ao enviar para {destinatario}: {str(e)}")
        
        return len(enviados) > 0, enviados
        
    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        return False, []

def enviar_email_alteracao(viagem_data, orcamento, email_usuario=None, viagem_antiga=None):
    """
    Envia email de confirmação de ALTERAÇÃO quando uma viagem é editada
    """
    try:
        if not EMAIL_ENABLED:
            print("⚠️ Email desabilitado no .env")
            return False, False
        
        if not EMAIL_REMETENTE or not EMAIL_SENHA:
            print("⚠️ Configurações de email incompletas")
            return False, False
        
        def formatar_moeda_html(valor):
            return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        
        # Comparar alterações
        alteracoes = []
        if viagem_antiga:
            alteracoes = comparar_alteracoes(viagem_antiga, viagem_data)
        
        # Criar corpo do email de ALTERAÇÃO
        html = criar_corpo_email_alteracao(viagem_data, orcamento, formatar_moeda_html, alteracoes)
        
        # Lista de destinatários
        destinatarios = []
        if EMAIL_DESTINATARIO:
            destinatarios.append(EMAIL_DESTINATARIO)
        if email_usuario and email_usuario != EMAIL_DESTINATARIO:
            destinatarios.append(email_usuario)
        
        if not destinatarios:
            return False, []
        
        # Enviar email para cada destinatário
        enviados = []
        for destinatario in destinatarios:
            try:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"✏️ Viagem ALTERADA - {viagem_data['comunidade']}"
                msg['From'] = EMAIL_REMETENTE
                msg['To'] = destinatario
                
                html_part = MIMEText(html, 'html')
                msg.attach(html_part)
                
                server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                server.starttls()
                server.login(EMAIL_REMETENTE, EMAIL_SENHA)
                server.send_message(msg)
                server.quit()
                
                enviados.append(destinatario)
                print(f"✅ Email de alteração enviado para: {destinatario}")
            except Exception as e:
                print(f"❌ Erro ao enviar para {destinatario}: {str(e)}")
        
        return len(enviados) > 0, enviados
        
    except Exception as e:
        print(f"❌ Erro geral: {str(e)}")
        return False, []

def criar_corpo_email(viagem_data, orcamento, formatar_moeda_html):
    """Cria o corpo HTML do email de NOVO CADASTRO"""
    # Converter lista de atividades para string
    atividades = viagem_data['tipo_atividade']
    if isinstance(atividades, list):
        atividades_str = ", ".join(atividades)
    else:
        atividades_str = str(atividades)
    
    # Converter comunidades para string
    comunidades = viagem_data['comunidade']
    if isinstance(comunidades, list):
        comunidades_str = ", ".join(comunidades)
    else:
        comunidades_str = str(comunidades)
    
    # Converter municípios para string
    municipios = viagem_data['municipio']
    if isinstance(municipios, list):
        municipios_str = ", ".join(municipios)
    else:
        municipios_str = str(municipios)
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #2C1810, #4A2F1A); padding: 20px; border-radius: 8px; text-align: center; color: white; margin-bottom: 20px; }}
            .header h1 {{ color: #FFD700; margin: 0; }}
            .header p {{ color: #DAA520; margin: 5px 0 0 0; }}
            .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
            .info-label {{ font-weight: bold; color: #555; }}
            .info-value {{ color: #333; }}
            .total {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center; }}
            .total-value {{ font-size: 28px; color: #2C1810; font-weight: bold; }}
            .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }}
            .badge {{ background: #FFD700; color: #2C1810; padding: 5px 10px; border-radius: 5px; font-weight: bold; display: inline-block; margin: 2px; }}
            .details {{ margin: 20px 0; }}
            .highlight {{ background: #FFF8E1; padding: 15px; border-radius: 8px; border-left: 4px solid #FFD700; }}
            .activity-container {{ margin: 5px 0; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏘️ Divisão Quilombola</h1>
                <p>Sistema de Cadastramento e Orçamento de Viagens</p>
            </div>
            
            <div class="highlight">
                <h2 style="color: #2C1810; margin: 0;">✅ Nova Viagem Cadastrada!</h2>
                <p style="color: #666; margin: 5px 0 0 0;">Uma nova viagem foi registrada no sistema.</p>
            </div>
            
            <div class="details">
                <h3 style="color: #2C1810;">📋 Dados da Viagem</h3>
                
                <div class="info-row">
                    <span class="info-label">🏘️ Comunidade:</span>
                    <span class="info-value"><strong>{comunidades_str}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Município:</span>
                    <span class="info-value">{municipios_str}</span>
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
                <div class="info-row" style="flex-wrap: wrap;">
                    <span class="info-label">📋 Atividade:</span>
                    <span class="info-value"><div class="activity-container">{atividades_str}</div></span>
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
                <h3 style="color: #2C1810;">💰 Orçamento da Viagem</h3>
                <div style="display: flex; justify-content: space-around; margin: 15px 0;">
                    <div>
                        <div style="font-size: 12px; color: #666;">Diárias</div>
                        <div style="font-size: 20px; color: #2C1810; font-weight: bold;">{formatar_moeda_html(orcamento['total_diarias_valor'])}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #666;">Combustível</div>
                        <div style="font-size: 20px; color: #2C1810; font-weight: bold;">{formatar_moeda_html(orcamento['total_combustivel'])}</div>
                    </div>
                </div>
                <hr style="border: 1px solid #eee; margin: 10px 0;">
                <div>
                    <div style="font-size: 14px; color: #666;">TOTAL GERAL</div>
                    <div class="total-value">{formatar_moeda_html(orcamento['total_geral'])}</div>
                </div>
            </div>
            
            <div class="footer">
                <p>📧 Este é um email automático gerado pelo <strong>QuilomboViagens</strong>.</p>
                <p>© 2026 QuilomboViagens - Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """

def criar_corpo_email_alteracao(viagem_data, orcamento, formatar_moeda_html, alteracoes):
    """Cria o corpo HTML do email de ALTERAÇÃO com detalhamento das mudanças"""
    # Converter lista de atividades para string
    atividades = viagem_data['tipo_atividade']
    if isinstance(atividades, list):
        atividades_str = ", ".join(atividades)
    else:
        atividades_str = str(atividades)
    
    # Converter comunidades para string
    comunidades = viagem_data['comunidade']
    if isinstance(comunidades, list):
        comunidades_str = ", ".join(comunidades)
    else:
        comunidades_str = str(comunidades)
    
    # Converter municípios para string
    municipios = viagem_data['municipio']
    if isinstance(municipios, list):
        municipios_str = ", ".join(municipios)
    else:
        municipios_str = str(municipios)
    
    # Criar tabela de alterações
    tabela_alteracoes = ""
    if alteracoes:
        tabela_alteracoes = """
        <h3 style="color: #1a237e; margin-top: 20px;">📝 Detalhamento das Alterações</h3>
        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
            <thead>
                <tr style="background-color: #1a237e; color: white;">
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Campo</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Valor Anterior</th>
                    <th style="padding: 10px; text-align: left; border: 1px solid #ddd;">Novo Valor</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for alteracao in alteracoes:
            tabela_alteracoes += f"""
                <tr>
                    <td style="padding: 8px; border: 1px solid #ddd; font-weight: bold;">{alteracao['campo']}</td>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #f8d7da; color: #721c24;">
                        <del>{alteracao['valor_antigo']}</del>
                    </td>
                    <td style="padding: 8px; border: 1px solid #ddd; background-color: #d4edda; color: #155724;">
                        <strong>{alteracao['valor_novo']}</strong>
                    </td>
                </tr>
            """
        
        tabela_alteracoes += """
            </tbody>
        </table>
        """
    else:
        tabela_alteracoes = """
        <p style="color: #1a237e; font-size: 14px;">
            Nenhuma alteração significativa foi detectada nos campos principais.
        </p>
        """
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; padding: 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ background: linear-gradient(135deg, #1a237e, #283593); padding: 20px; border-radius: 8px; text-align: center; color: white; margin-bottom: 20px; }}
            .header h1 {{ color: #FFD700; margin: 0; }}
            .header p {{ color: #DAA520; margin: 5px 0 0 0; }}
            .info-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #eee; }}
            .info-label {{ font-weight: bold; color: #555; }}
            .info-value {{ color: #333; }}
            .total {{ background: #f8f9fa; padding: 15px; border-radius: 8px; margin-top: 20px; text-align: center; }}
            .total-value {{ font-size: 28px; color: #1a237e; font-weight: bold; }}
            .footer {{ margin-top: 30px; text-align: center; color: #999; font-size: 12px; border-top: 1px solid #eee; padding-top: 20px; }}
            .details {{ margin: 20px 0; }}
            .highlight {{ background: #E8EAF6; padding: 15px; border-radius: 8px; border-left: 6px solid #1a237e; }}
            .activity-container {{ margin: 5px 0; }}
            .badge-alteracao {{ background: #FFD700; color: #1a237e; padding: 5px 15px; border-radius: 20px; font-weight: bold; display: inline-block; }}
            .resumo-alteracoes {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 10px 0; }}
            table {{ font-size: 14px; }}
            td {{ padding: 8px; }}
            del {{ color: #721c24; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🏘️ Divisão Quilombola</h1>
                <p>Sistema de Cadastramento e Orçamento de Viagens</p>
            </div>
            
            <div class="highlight">
                <h2 style="color: #1a237e; margin: 0;">✏️ Viagem ALTERADA!</h2>
                <p style="color: #1a237e; margin: 10px 0 0 0; font-size: 16px;">
                    <span class="badge-alteracao">ALTERAÇÃO REALIZADA</span>
                </p>
                <p style="color: #1a237e; margin: 5px 0 0 0; font-size: 14px;">
                    Os dados da viagem foram atualizados no sistema.
                </p>
                <div class="resumo-alteracoes">
                    <p style="margin: 0; font-weight: bold; color: #1a237e;">
                        📊 Total de alterações: {len(alteracoes)}
                    </p>
                </div>
            </div>
            
            {tabela_alteracoes}
            
            <div class="details">
                <h3 style="color: #1a237e;">📋 Dados Atualizados da Viagem</h3>
                
                <div class="info-row">
                    <span class="info-label">🏘️ Comunidade:</span>
                    <span class="info-value"><strong>{comunidades_str}</strong></span>
                </div>
                <div class="info-row">
                    <span class="info-label">📍 Município:</span>
                    <span class="info-value">{municipios_str}</span>
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
                <div class="info-row" style="flex-wrap: wrap;">
                    <span class="info-label">📋 Atividade:</span>
                    <span class="info-value"><div class="activity-container">{atividades_str}</div></span>
                </div>
                <div class="info-row">
                    <span class="info-label">👤 Cadastrante:</span>
                    <span class="info-value">{viagem_data['cadastrante']}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">🕐 Data Alteração:</span>
                    <span class="info-value">{viagem_data['data_cadastro']}</span>
                </div>
            </div>
            
            <div class="total">
                <h3 style="color: #1a237e;">💰 Orçamento Atualizado</h3>
                <div style="display: flex; justify-content: space-around; margin: 15px 0;">
                    <div>
                        <div style="font-size: 12px; color: #666;">Diárias</div>
                        <div style="font-size: 20px; color: #1a237e; font-weight: bold;">{formatar_moeda_html(orcamento['total_diarias_valor'])}</div>
                    </div>
                    <div>
                        <div style="font-size: 12px; color: #666;">Combustível</div>
                        <div style="font-size: 20px; color: #1a237e; font-weight: bold;">{formatar_moeda_html(orcamento['total_combustivel'])}</div>
                    </div>
                </div>
                <hr style="border: 1px solid #eee; margin: 10px 0;">
                <div>
                    <div style="font-size: 14px; color: #666;">TOTAL GERAL</div>
                    <div class="total-value">{formatar_moeda_html(orcamento['total_geral'])}</div>
                </div>
            </div>
            
            <div class="footer">
                <p>📧 Este é um email automático gerado pelo <strong>QuilomboViagens</strong>.</p>
                <p>© 2026 QuilomboViagens - Todos os direitos reservados.</p>
            </div>
        </div>
    </body>
    </html>
    """

def gerar_pdf_extrato(viagem_data, orcamento):
    """Gera um PDF com o extrato da viagem"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    titulo_style = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#2C1810'),
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    subtitulo_style = ParagraphStyle(
        'Subtitulo',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4A2F1A'),
        alignment=TA_CENTER,
        spaceAfter=20
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#555555'),
        alignment=TA_LEFT
    )
    
    value_style = ParagraphStyle(
        'Value',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        alignment=TA_RIGHT
    )
    
    total_style = ParagraphStyle(
        'Total',
        parent=styles['Normal'],
        fontSize=14,
        textColor=colors.HexColor('#2C1810'),
        alignment=TA_CENTER,
        spaceAfter=10
    )
    
    # Elementos do PDF
    elementos = []
    
    # Título
    elementos.append(Paragraph("🏘️ DIVISÃO QUILOMBOLA", titulo_style))
    elementos.append(Paragraph("Extrato de Viagem", subtitulo_style))
    elementos.append(Spacer(1, 0.5*cm))
    
    # Função para converter lista para string
    def list_to_string(valor):
        if isinstance(valor, list):
            return ", ".join(valor)
        return str(valor)
    
    # Dados da viagem
    dados = [
        ["Comunidade:", list_to_string(viagem_data['comunidade'])],
        ["Município:", list_to_string(viagem_data['municipio'])],
        ["Período:", f"{viagem_data['data_inicio']} a {viagem_data['data_fim']}"],
        ["Dias:", f"{viagem_data['dias_totais']} dia(s)"],
        ["Servidores:", str(viagem_data['quantidade_servidores'])],
        ["Diárias por Servidor:", f"{viagem_data['diarias_por_servidor']:.1f}"],
        ["Distância Rodoviária:", f"{viagem_data['distancia_rodoviaria']:.1f} km"],
        ["Distância Local:", f"{viagem_data['distancia_local']:.1f} km"],
        ["Atividade:", list_to_string(viagem_data['tipo_atividade'])],
        ["Cadastrante:", viagem_data['cadastrante']],
        ["Data Cadastro:", viagem_data['data_cadastro']]
    ]
    
    # Criar tabela de dados
    tabela_dados = []
    for label, value in dados:
        tabela_dados.append([
            Paragraph(label, label_style),
            Paragraph(value, value_style)
        ])
    
    tabela = Table(tabela_dados, colWidths=[4*cm, 8*cm])
    tabela.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
    ]))
    elementos.append(tabela)
    elementos.append(Spacer(1, 1*cm))
    
    # Orçamento
    elementos.append(Paragraph("💰 ORÇAMENTO", styles['Heading3']))
    elementos.append(Spacer(1, 0.3*cm))
    
    orcamento_dados = [
        ["Total Diárias:", f"R$ {orcamento['total_diarias_valor']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
        ["Total Combustível:", f"R$ {orcamento['total_combustivel']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')],
        ["", ""],
        ["TOTAL GERAL:", f"R$ {orcamento['total_geral']:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')]
    ]
    
    tabela_orcamento = Table(orcamento_dados, colWidths=[4*cm, 8*cm])
    tabela_orcamento.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#DDDDDD')),
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#F5F5F5')),
        ('PADDING', (0, 0), (-1, -1), 6),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 3), (1, 3), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 3), (1, 3), 12),
        ('BACKGROUND', (0, 3), (1, 3), colors.HexColor('#FFF8E1')),
    ]))
    elementos.append(tabela_orcamento)
    
    # Rodapé
    elementos.append(Spacer(1, 1*cm))
    elementos.append(Paragraph("Documento gerado automaticamente pelo Sistema QuilomboViagens", styles['Normal']))
    elementos.append(Paragraph(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    
    # Construir PDF
    doc.build(elementos)
    buffer.seek(0)
    return buffer

def calcular_diarias(data_inicio, data_fim):
    if data_fim < data_inicio:
        return 0
    total_dias = (data_fim - data_inicio).days + 1
    if total_dias == 1:
        return 1.0
    else:
        return (total_dias - 1) + 0.5

def calcular_orcamento(quantidade_servidores, data_inicio, data_fim, distancia_rodoviaria, distancia_local):
    diarias_por_servidor = calcular_diarias(data_inicio, data_fim)
    total_diarias_servidor = diarias_por_servidor * quantidade_servidores
    total_diarias_valor = total_diarias_servidor * DIARIA_VALOR
    
    litros_rodoviario = distancia_rodoviaria / CONSUMO_MEDIO if CONSUMO_MEDIO > 0 else 0
    total_combustivel_rodoviario = litros_rodoviario * DIESEL_VALOR
    
    litros_local = distancia_local / CONSUMO_MEDIO if CONSUMO_MEDIO > 0 else 0
    total_combustivel_local = litros_local * DIESEL_VALOR
    
    total_combustivel = total_combustivel_rodoviario + total_combustivel_local
    total_litros = litros_rodoviario + litros_local
    
    total_geral = total_diarias_valor + total_combustivel
    
    return {
        'dias_totais': (data_fim - data_inicio).days + 1,
        'diarias_por_servidor': diarias_por_servidor,
        'total_diarias_servidor': total_diarias_servidor,
        'total_diarias_valor': total_diarias_valor,
        'distancia_rodoviaria': distancia_rodoviaria,
        'distancia_local': distancia_local,
        'distancia_total': distancia_rodoviaria + distancia_local,
        'litros_rodoviario': litros_rodoviario,
        'litros_local': litros_local,
        'total_litros': total_litros,
        'total_combustivel_rodoviario': total_combustivel_rodoviario,
        'total_combustivel_local': total_combustivel_local,
        'total_combustivel': total_combustivel,
        'total_geral': total_geral
    }

def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')

def get_download_link(df, filename):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}">📥 Baixar Relatório CSV</a>'
    return href

# ==================== INICIALIZAÇÃO DA SESSÃO ====================

# Inicializar sessão
if 'viagens' not in st.session_state:
    # Carregar do banco de dados
    st.session_state.viagens = db.carregar_viagens()

# Flag para controlar se já cadastrou
if 'viagem_cadastrada' not in st.session_state:
    st.session_state.viagem_cadastrada = None

# Estado para edição
if 'editando_viagem' not in st.session_state:
    st.session_state.editando_viagem = None

# Estado para email
if 'email_status' not in st.session_state:
    st.session_state.email_status = None

# Estado para feedback
if 'feedback_enviado' not in st.session_state:
    st.session_state.feedback_enviado = False

# ==================== FIM INICIALIZAÇÃO ====================

# Título
st.subheader("🛻 QuilomboViagens")
st.markdown("Sistema de Cadastro e Orçamento de Viagens")

# Sidebar
with st.sidebar:
    st.title("🛻 QuilomboViagens")
    st.markdown("### 📋 Valores Fixos")
    st.info(f"💰 Diária: {formatar_moeda(DIARIA_VALOR)}")
    st.info(f"💰 Meia Diária: {formatar_moeda(MEIA_DIARIA)}")
    st.info(f"⛽ Diesel: {formatar_moeda(DIESEL_VALOR)}/L")
    st.info(f"🚗 Consumo: {CONSUMO_MEDIO} km/L")
    
    st.markdown("---")
    st.markdown("### 📊 Resumo")
    if st.session_state.viagens:
        total_geral = sum(v.get('orcamento', {}).get('total_geral', 0) for v in st.session_state.viagens)
        total_viagens = len(st.session_state.viagens)
        st.metric("Total de Viagens", total_viagens)
        st.metric("Custo Total", formatar_moeda(total_geral))
        
        # Informação do banco de dados
        st.markdown("---")
        st.caption(f"💾 Dados salvos no banco SQLite")

# Abas
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 Nova Viagem", 
    "📋 Lista de Viagens", 
    "📊 Análise e Relatórios", 
    "📄 Meus Extratos", 
    "📝 Feedback",
    "🔄 Sincronização"  # Nova aba
])

with tab1:
    st.markdown("### 📝 Cadastrar Nova Viagem")
    
    col1, col2 = st.columns(2)
    
    with col1:
        comunidade = st.multiselect("🏘️ Comunidade", constantes.COMUNIDADES, placeholder="Digite o nome da comunidade")
        municipio = st.multiselect("📍 Município", constantes.MUNICIPIOS, placeholder="Digite o nome do município")
        
        data_inicio = st.date_input(
            "📅 Data de Início (ida)",
            min_value=datetime.now().date(),
            value=datetime.now().date()
        )
        data_fim = st.date_input(
            "📅 Data de Término (retorno)",
            min_value=data_inicio,
            value=data_inicio + timedelta(days=1)
        )
        
        if data_fim >= data_inicio:
            dias_viagem = (data_fim - data_inicio).days + 1
            diarias_calculadas = calcular_diarias(data_inicio, data_fim)
            st.info(f"📆 Duração: {dias_viagem} dia(s)")
            st.info(f"🏨 Diárias por servidor: {diarias_calculadas:.1f} (último dia = meia diária)")
        else:
            st.error("A data de término deve ser maior ou igual à data de início")
    
    with col2:
        quantidade_servidores = st.number_input(
            "👥 Número de Servidores",
            min_value=1,
            max_value=50,
            value=1,
            step=1
        )
        
        cadastrante = st.text_input("👤 Cadastrado por", placeholder="Digite o nome do servidor responsável")
        
        email_usuario = st.selectbox("📧 Seu Email (opcional)", constantes.EMAILS,
            help="Seu email será usado para enviar a confirmação"
        )
        
        distancia_rodoviaria = st.number_input(
            "🚗 Distância Rodoviária (km) - Ida e Volta",
            min_value=0.0,
            max_value=5000.0,
            value=100.0,
            step=10.0,
            help="Distância da sede ao município de destino"
        )
        
        distancia_local = st.number_input(
            "🚙 Distância Local (km)",
            min_value=0.0,
            max_value=5000.0,
            value=20.0,
            step=5.0,
            help="Deslocamentos internos no município de destino (ex.: visitas às comunidades) durante a viagem"
        )
        
        distancia_total = distancia_rodoviaria + distancia_local
        st.caption(f"📏 Distância total: {distancia_total:.1f} km")
        
        tipo_atividade = st.multiselect(
            "📋 Tipo de Atividade", constantes.TIPO_DE_ATIVIDADE,
            placeholder="Selecione as atividades que serão realizadas durante a viagem"
        )
    
    # Botão de cadastro
    if st.button("✅ Cadastrar Viagem", type="primary", use_container_width=True, key="btn_cadastrar"):
        # Limpar status anterior do email ao iniciar um novo cadastro
        if 'email_status' in st.session_state:
            st.session_state.email_status = None
        
        if not comunidade or not municipio or not cadastrante:
            st.error("❌ Preencha todos os campos obrigatórios")
        elif data_fim < data_inicio:
            st.error("❌ Data de término inválida")
        else:
            orcamento = calcular_orcamento(
                quantidade_servidores,
                data_inicio,
                data_fim,
                distancia_rodoviaria,
                distancia_local
            )
            
            if email_usuario and not '@' in email_usuario:
                st.warning("⚠️ Email inválido. A confirmação não será enviada para este email.")
                email_usuario = None
            
            viagem = {
                'comunidade': comunidade,
                'municipio': municipio,
                'data_inicio': data_inicio.strftime('%d/%m/%Y'),
                'data_fim': data_fim.strftime('%d/%m/%Y'),
                'quantidade_servidores': quantidade_servidores,
                'diarias_por_servidor': orcamento['diarias_por_servidor'],
                'dias_totais': orcamento['dias_totais'],
                'distancia_rodoviaria': distancia_rodoviaria,
                'distancia_local': distancia_local,
                'distancia_total': distancia_total,
                'tipo_atividade': tipo_atividade,
                'cadastrante': cadastrante,
                'email_usuario': email_usuario if email_usuario else '',
                'orcamento': orcamento,
                'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M')
            }
            
            # Salvar no banco de dados
            try:
                viagem_id = db.salvar_viagem(viagem)
                viagem['id'] = viagem_id
                
                # Atualizar sessão
                st.session_state.viagens = db.carregar_viagens()
                st.session_state.viagem_cadastrada = viagem
                
                # Enviar email
                with st.spinner("📧 Enviando email de confirmação..."):
                    email_enviado, destinatarios_enviados = enviar_email_confirmacao(viagem, orcamento, email_usuario)
                
                # Armazenar status do email na sessão
                st.session_state.email_status = {
                    'enviado': email_enviado,
                    'destinatarios': destinatarios_enviados,
                    'email_usuario': email_usuario
                }
                
                st.success("✅ Viagem cadastrada com sucesso!")
                
            except Exception as e:
                st.error(f"❌ Erro ao salvar no banco de dados: {str(e)}")
    
    # Exibir mensagem de confirmação do email (se existir)
    if 'email_status' in st.session_state and st.session_state.email_status is not None:
        status = st.session_state.email_status
        
        st.markdown("---")
        
        if status['enviado']:
            # Mensagem de sucesso com detalhes
            destinatarios_str = ', '.join(status['destinatarios'])
            
            # Container destacado para a mensagem
            st.markdown(f"""
            <div style="
                background-color: #d4edda;
                border-left: 6px solid #28a745;
                padding: 0px;
                border-radius: 8px;
                margin: 0px 0;
            ">
                <p style="color: #155724; margin: 0px 0 0 0; font-size: 16px;">
                    📧 O email de confirmação foi enviado para o(s) endereço(s):
                    <strong>{destinatarios_str}</strong>
                </p>
                <p style="color: #155724; margin: 5px 0 0 0; font-size: 14px;">
                    🕐 Enviado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            # Mensagem de aviso se o email não foi enviado
            st.markdown("""
            <div style="
                background-color: #fff3cd;
                border-left: 6px solid #ffc107;
                padding: 20px;
                border-radius: 8px;
                margin: 10px 0;
            ">
                <h3 style="color: #856404; margin: 0;">⚠️ ATENÇÃO</h3>
                <p style="color: #856404; margin: 10px 0 0 0; font-size: 16px;">
                    Viagem cadastrada com sucesso, mas houve um problema ao enviar o email de confirmação.
                </p>
                <p style="color: #856404; margin: 5px 0 0 0; font-size: 14px;">
                    Verifique as configurações de email no arquivo .env
                </p>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
    
    # Exibir orçamento da última viagem cadastrada
    if st.session_state.viagem_cadastrada:
        viagem = st.session_state.viagem_cadastrada
        orcamento = viagem['orcamento']
        
        st.markdown("### 📊 Orçamento Gerado")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("💰 Total Diárias", formatar_moeda(orcamento['total_diarias_valor']))
        with col2:
            st.metric("⛽ Total Combustível", formatar_moeda(orcamento['total_combustivel']))
        with col3:
            st.metric("💵 Total Geral", formatar_moeda(orcamento['total_geral']))
        
        with st.expander("📋 Detalhamento do Orçamento"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Diárias:**")
                st.write(f"• Dias totais: {orcamento['dias_totais']}")
                st.write(f"• Diárias/servidor: {orcamento['diarias_por_servidor']:.1f}")
                st.write(f"• Total diárias: {orcamento['total_diarias_servidor']:.1f}")
                st.write(f"• Valor: {formatar_moeda(orcamento['total_diarias_valor'])}")
            with col2:
                st.markdown("**Combustível:**")
                st.write(f"• Distância rodoviária: {orcamento['distancia_rodoviaria']:.1f} km")
                st.write(f"• Distância local: {orcamento['distancia_local']:.1f} km")
                st.write(f"• Total litros: {orcamento['total_litros']:.1f} L")
                st.write(f"• Valor: {formatar_moeda(orcamento['total_combustivel'])}")
            
            st.markdown("---")
            st.markdown(f"**💵 TOTAL GERAL: {formatar_moeda(orcamento['total_geral'])}**")
        
        # Botões para download - PDF e HTML lado a lado
        st.markdown("### 📄 Baixar Extrato")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Botão para baixar PDF
            if st.button("📄 Baixar Extrato em PDF", use_container_width=True, key="btn_pdf_cadastro"):
                pdf_buffer = gerar_pdf_extrato(viagem, orcamento)
                st.download_button(
                    label="📥 Clique para baixar o PDF",
                    data=pdf_buffer,
                    file_name=f"extrato_{viagem['comunidade'][0] if isinstance(viagem['comunidade'], list) else viagem['comunidade']}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="download_pdf_cadastro"
                )
        
        with col2:
            # Função para formatar moeda no HTML
            def formatar_moeda_html(valor):
                return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
            
            # Botão para baixar HTML
            html_content = criar_corpo_email(viagem, orcamento, formatar_moeda_html)
            html_bytes = html_content.encode('utf-8')
            b64_html = base64.b64encode(html_bytes).decode()
            
            st.markdown(f"""
            <div style="display: flex; justify-content: center; width: 100%;">
                <a href="data:text/html;base64,{b64_html}" 
                   download="extrato_{viagem['comunidade'][0] if isinstance(viagem['comunidade'], list) else viagem['comunidade']}_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
                   style="
                       background-color: #f0f2f6;
                       color: #262730;
                       padding: 06px 20px;
                       text-decoration: none;
                       border-radius: 5px;
                       border: 1px solid #d1d5db;
                       text-align: center;
                       font-weight: 500;
                       display: inline-block;
                       width: 100%;
                       transition: all 0.2s;
                   "
                   onmouseover="this.style.backgroundColor='#e0e2e6'"
                   onmouseout="this.style.backgroundColor='#f0f2f6'">
                    📧 Baixar Extrato em HTML
                </a>
            </div>
            """, unsafe_allow_html=True)

with tab2:
    st.markdown("### 📋 Viagens Cadastradas")
    
    # Recarregar do banco de dados para garantir dados atualizados
    st.session_state.viagens = db.carregar_viagens()
    
    if not st.session_state.viagens:
        st.info("ℹ️ Nenhuma viagem cadastrada.")
    else:
        # Verificar se está em modo de edição
        if st.session_state.editando_viagem is not None:
            viagem_edit = st.session_state.editando_viagem
            st.markdown("### ✏️ Editando Viagem")
            st.info(f"Editando viagem ID: {viagem_edit['id']}")
            
            col1, col2 = st.columns(2)
            
            with col1:
                comunidade_edit = st.multiselect(
                    "🏘️ Comunidade",
                    constantes.COMUNIDADES,
                    default=viagem_edit['comunidade'],
                    key="edit_comunidade"
                )
                municipio_edit = st.multiselect(
                    "📍 Município",
                    constantes.MUNICIPIOS,
                    default=viagem_edit['municipio'],
                    key="edit_municipio"
                )
                
                data_inicio_edit = st.date_input(
                    "📅 Data de Início",
                    value=datetime.strptime(viagem_edit['data_inicio'], '%d/%m/%Y'),
                    key="edit_data_inicio"
                )
                data_fim_edit = st.date_input(
                    "📅 Data de Término",
                    value=datetime.strptime(viagem_edit['data_fim'], '%d/%m/%Y'),
                    min_value=data_inicio_edit,
                    key="edit_data_fim"
                )
                
                if data_fim_edit >= data_inicio_edit:
                    dias_viagem_edit = (data_fim_edit - data_inicio_edit).days + 1
                    diarias_calculadas_edit = calcular_diarias(data_inicio_edit, data_fim_edit)
                    st.info(f"📆 Duração: {dias_viagem_edit} dia(s)")
                    st.info(f"🏨 Diárias por servidor: {diarias_calculadas_edit:.1f}")
            
            with col2:
                quantidade_servidores_edit = st.number_input(
                    "👥 Número de Servidores",
                    min_value=1,
                    max_value=50,
                    value=viagem_edit['quantidade_servidores'],
                    step=1,
                    key="edit_servidores"
                )
                
                cadastrante_edit = st.text_input(
                    "👤 Cadastrado por",
                    value=viagem_edit['cadastrante'],
                    key="edit_cadastrante"
                )
                
                email_usuario_edit = st.selectbox(
                    "📧 Seu Email",
                    constantes.EMAILS,
                    index=constantes.EMAILS.index(viagem_edit['email_usuario']) if viagem_edit['email_usuario'] in constantes.EMAILS else 0,
                    key="edit_email"
                )
                
                distancia_rodoviaria_edit = st.number_input(
                    "🚗 Distância Rodoviária (km)",
                    min_value=0.0,
                    max_value=5000.0,
                    value=viagem_edit['distancia_rodoviaria'],
                    step=10.0,
                    key="edit_dist_rod"
                )
                
                distancia_local_edit = st.number_input(
                    "🚙 Distância Local (km)",
                    min_value=0.0,
                    max_value=500.0,
                    value=viagem_edit['distancia_local'],
                    step=5.0,
                    key="edit_dist_local"
                )
                
                distancia_total_edit = distancia_rodoviaria_edit + distancia_local_edit
                st.caption(f"📏 Distância total: {distancia_total_edit:.1f} km")
                
                tipo_atividade_edit = st.multiselect(
                    "📋 Tipo de Atividade",
                    constantes.TIPO_DE_ATIVIDADE,
                    default=viagem_edit['tipo_atividade'],
                    key="edit_atividade"
                )
            
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.button("💾 Salvar Alterações", type="primary", use_container_width=True):
                    # Recalcular orçamento
                    orcamento_edit = calcular_orcamento(
                        quantidade_servidores_edit,
                        data_inicio_edit,
                        data_fim_edit,
                        distancia_rodoviaria_edit,
                        distancia_local_edit
                    )
                    
                    viagem_atualizada = {
                        'comunidade': comunidade_edit,
                        'municipio': municipio_edit,
                        'data_inicio': data_inicio_edit.strftime('%d/%m/%Y'),
                        'data_fim': data_fim_edit.strftime('%d/%m/%Y'),
                        'quantidade_servidores': quantidade_servidores_edit,
                        'diarias_por_servidor': orcamento_edit['diarias_por_servidor'],
                        'dias_totais': orcamento_edit['dias_totais'],
                        'distancia_rodoviaria': distancia_rodoviaria_edit,
                        'distancia_local': distancia_local_edit,
                        'distancia_total': distancia_total_edit,
                        'tipo_atividade': tipo_atividade_edit,
                        'cadastrante': cadastrante_edit,
                        'email_usuario': email_usuario_edit if email_usuario_edit else '',
                        'orcamento': orcamento_edit,
                        'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M')
                    }
                    
                    try:
                        # Atualizar no banco
                        db.atualizar_viagem(viagem_edit['id'], viagem_atualizada)
                        st.session_state.viagens = db.carregar_viagens()
                        
                        # Enviar email de alteração
                        with st.spinner("📧 Enviando email de confirmação de alteração..."):
                            email_para_envio = email_usuario_edit if email_usuario_edit else viagem_edit.get('email_usuario', '')
                            email_enviado, destinatarios = enviar_email_alteracao(
                                viagem_atualizada, 
                                orcamento_edit, 
                                email_para_envio
                            )
                        
                        # Limpar estado de edição
                        st.session_state.editando_viagem = None
                        
                        # Mostrar mensagem de sucesso
                        if email_enviado:
                            st.success(f"✅ Viagem atualizada com sucesso! Email de confirmação enviado para: {', '.join(destinatarios)}")
                        else:
                            st.success("✅ Viagem atualizada com sucesso! (Email de confirmação não enviado)")
                        
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Erro ao atualizar: {str(e)}")
            
            with col2:
                if st.button("❌ Cancelar Edição", use_container_width=True):
                    st.session_state.editando_viagem = None
                    st.rerun()
            
            st.markdown("---")
        
        # Lista de viagens
        dados = []
        for viagem in st.session_state.viagens:
            # Converter listas para string
            comunidades = viagem.get('comunidade', '')
            if isinstance(comunidades, list):
                comunidades = ", ".join(comunidades)
            
            municipios = viagem.get('municipio', '')
            if isinstance(municipios, list):
                municipios = ", ".join(municipios)
            
            atividades = viagem.get('tipo_atividade', '')
            if isinstance(atividades, list):
                atividades = ", ".join(atividades)
            
            orcamento = viagem.get('orcamento', {})
            
            dados.append({
                'ID': viagem.get('id', ''),
                'Comunidade': comunidades,
                'Município': municipios,
                'Período': f"{viagem.get('data_inicio', '')} a {viagem.get('data_fim', '')}",
                'Dias': viagem.get('dias_totais', 0),
                'Servidores': viagem.get('quantidade_servidores', 0),
                'Atividade': atividades,
                'Cadastrante': viagem.get('cadastrante', 'Não informado'),
                'Total Diárias': orcamento.get('total_diarias_valor', 0),
                'Total Combustível': orcamento.get('total_combustivel', 0),
                'Total Geral': orcamento.get('total_geral', 0)
            })
        
        df = pd.DataFrame(dados)
        if 'ID' in df.columns:
                    df = df.drop(columns=['ID'])
                    df.index = df.index + 1
        df['Total Diárias'] = df['Total Diárias'].apply(lambda x: formatar_moeda(x))
        df['Total Combustível'] = df['Total Combustível'].apply(lambda x: formatar_moeda(x))
        df['Total Geral'] = df['Total Geral'].apply(lambda x: formatar_moeda(x))
        
        st.dataframe(df, use_container_width=True, height=400)
        
        # Botões de ação - USANDO BOTÕES DIRETOS SEM CHECKBOX
        st.markdown("### 🔧 Gerenciar Viagens")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("**✏️ Editar Viagem**")
            if not st.session_state.editando_viagem:
                ids_disponiveis = [v['id'] for v in st.session_state.viagens]
                id_para_editar = st.selectbox(
                    "Selecione o ID",
                    ids_disponiveis,
                    key="select_editar",
                    label_visibility="collapsed"
                )
                
                if st.button("✏️ Editar Viagem", use_container_width=True, key="btn_editar"):
                    viagem_para_editar = next((v for v in st.session_state.viagens if v['id'] == id_para_editar), None)
                    if viagem_para_editar:
                        st.session_state.editando_viagem = viagem_para_editar
                        st.rerun()
        
        with col2:
            st.markdown("**🗑️ Excluir Viagem**")
            if not st.session_state.editando_viagem:
                ids_disponiveis = [v['id'] for v in st.session_state.viagens]
                id_para_excluir = st.selectbox(
                    "Selecione o ID",
                    ids_disponiveis,
                    key="select_excluir",
                    label_visibility="collapsed"
                )
                
                # Estado de confirmação para exclusão
                if 'confirmar_exclusao' not in st.session_state:
                    st.session_state.confirmar_exclusao = False
                
                if st.button("🗑️ Excluir Viagem", type="secondary", use_container_width=True, key="btn_excluir"):
                    st.session_state.confirmar_exclusao = True
                    st.session_state.id_para_excluir = id_para_excluir
                    st.rerun()
                
                # Mostrar confirmação apenas se confirmar_exclusao for True
                if st.session_state.confirmar_exclusao and st.session_state.id_para_excluir == id_para_excluir:
                    st.warning(f"⚠️ Tem certeza que deseja excluir a viagem ID {id_para_excluir}?")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Sim, excluir", use_container_width=True, key="confirm_excluir"):
                            try:
                                db.deletar_viagem(id_para_excluir)
                                st.session_state.viagens = db.carregar_viagens()
                                st.session_state.confirmar_exclusao = False
                                st.session_state.id_para_excluir = None
                                st.success(f"✅ Viagem ID {id_para_excluir} excluída com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao excluir: {str(e)}")
                    with col_cancel:
                        if st.button("❌ Cancelar", use_container_width=True, key="cancel_excluir"):
                            st.session_state.confirmar_exclusao = False
                            st.session_state.id_para_excluir = None
                            st.rerun()
        
        with col3:
            st.markdown("**🗑️ Limpar Todas**")
            if not st.session_state.editando_viagem:
                # Estado de confirmação para limpar todas
                if 'confirmar_limpar_todas' not in st.session_state:
                    st.session_state.confirmar_limpar_todas = False
                
                if st.button("🗑️ Limpar Todas", type="secondary", use_container_width=True, key="btn_limpar_todas"):
                    st.session_state.confirmar_limpar_todas = True
                    st.rerun()
                
                # Mostrar confirmação apenas se confirmar_limpar_todas for True
                if st.session_state.confirmar_limpar_todas:
                    st.warning("⚠️ ATENÇÃO: Isso irá excluir TODAS as viagens cadastradas!")
                    col_confirm, col_cancel = st.columns(2)
                    with col_confirm:
                        if st.button("✅ Sim, excluir todas", use_container_width=True, key="confirm_limpar_todas"):
                            try:
                                db.deletar_todas_viagens()
                                st.session_state.viagens = []
                                st.session_state.viagem_cadastrada = None
                                st.session_state.confirmar_limpar_todas = False
                                st.success("✅ Todas as viagens foram excluídas com sucesso!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Erro ao excluir: {str(e)}")
                    with col_cancel:
                        if st.button("❌ Cancelar", use_container_width=True, key="cancel_limpar_todas"):
                            st.session_state.confirmar_limpar_todas = False
                            st.rerun()
        
        # Botão para baixar CSV
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col2:
            df_export = pd.DataFrame(dados)
            st.markdown(get_download_link(df_export, "viagens_quilombola.csv"), unsafe_allow_html=True)

with tab3:
    st.markdown("### 📊 Análise e Relatórios")
    
    # Recarregar do banco de dados
    st.session_state.viagens = db.carregar_viagens()
    
    if not st.session_state.viagens:
        st.info("ℹ️ Cadastre algumas viagens para visualizar as análises.")
    else:
        dados_analise = []
        for viagem in st.session_state.viagens:
            # Converter listas para string para análise
            comunidade = viagem.get('comunidade', '')
            if isinstance(comunidade, list):
                comunidade = ", ".join(comunidade)
            
            municipio = viagem.get('municipio', '')
            if isinstance(municipio, list):
                municipio = ", ".join(municipio)
            
            atividade = viagem.get('tipo_atividade', '')
            if isinstance(atividade, list):
                atividade = ", ".join(atividade)
            
            dados_analise.append({
                'Comunidade': comunidade,
                'Município': municipio,
                'Tipo Atividade': atividade,
                'Cadastrante': viagem.get('cadastrante', 'Não informado'),
                'Total Geral': viagem.get('orcamento', {}).get('total_geral', 0),
                'Distância Total': viagem.get('distancia_total', 0.0),
                'Servidores': viagem.get('quantidade_servidores', 0),
                'Dias': viagem.get('dias_totais', 0)
            })
        
        df_analise = pd.DataFrame(dados_analise)
        
        if len(df_analise) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                # Agrupar por Comunidade (agora é string)
                custo_comunidade = df_analise.groupby('Comunidade')['Total Geral'].sum().reset_index()
                fig = px.bar(
                    custo_comunidade,
                    x='Comunidade',
                    y='Total Geral',
                    title='Custo por Comunidade',
                    color='Comunidade',
                    text_auto=True
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # Agrupar por Atividade
                custo_atividade = df_analise.groupby('Tipo Atividade')['Total Geral'].sum().reset_index()
                fig = px.pie(
                    custo_atividade,
                    values='Total Geral',
                    names='Tipo Atividade',
                    title='Distribuição por Atividade'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.markdown("### 📈 Resumo Geral")
            
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("💰 Custo Total", formatar_moeda(df_analise['Total Geral'].sum()))
            with col2:
                st.metric("🛣️ Total KM", f"{df_analise['Distância Total'].sum():,.1f} km".replace(',', '.'))
            with col3:
                st.metric("👥 Total Servidores", df_analise['Servidores'].sum())
            with col4:
                st.metric("📋 Total Viagens", len(df_analise))
            with col5:
                st.metric("📆 Total Dias", df_analise['Dias'].sum())
            
            st.markdown("---")
            st.markdown("### 👤 Análise por Cadastrante")
            
            cadastrante_analise = df_analise.groupby('Cadastrante').agg({
                'Total Geral': 'sum',
                'Servidores': 'sum',
                'Dias': 'sum'
            }).reset_index()
            
            cadastrante_analise.columns = ['Cadastrante', 'Custo Total', 'Total Servidores', 'Total Dias']
            cadastrante_analise['Qtd Viagens'] = df_analise.groupby('Cadastrante').size().values
            cadastrante_analise = cadastrante_analise[['Cadastrante', 'Qtd Viagens', 'Custo Total', 'Total Servidores', 'Total Dias']]
            cadastrante_analise['Custo Total'] = cadastrante_analise['Custo Total'].apply(lambda x: formatar_moeda(x))
            
            st.dataframe(cadastrante_analise, use_container_width=True)

with tab4:
    st.markdown("### 📄 Meus Extratos")
    st.markdown("Consulte aqui os extratos das suas viagens cadastradas.")
    
    # Recarregar do banco de dados
    st.session_state.viagens = db.carregar_viagens()
    
    if not st.session_state.viagens:
        st.info("ℹ️ Nenhuma viagem cadastrada para consultar extratos.")
    else:
        # Filtro por cadastrante
        cadastrantes = list(set([v.get('cadastrante', '') for v in st.session_state.viagens if v.get('cadastrante', '')]))
        cadastrantes.insert(0, "Todos")
        
        filtro_cadastrante = st.selectbox(
            "👤 Filtrar por cadastrante",
            cadastrantes,
            key="filtro_cadastrante_extratos"
        )
        
        # Filtrar viagens
        if filtro_cadastrante == "Todos":
            viagens_filtradas = st.session_state.viagens
        else:
            viagens_filtradas = [v for v in st.session_state.viagens if v.get('cadastrante', '') == filtro_cadastrante]
        
        if not viagens_filtradas:
            st.info("ℹ️ Nenhuma viagem encontrada para este cadastrante.")
        else:
            # Selecionar viagem
            opcoes = []
            for i, v in enumerate(viagens_filtradas):
                comunidade = v.get('comunidade', '')
                if isinstance(comunidade, list):
                    comunidade = ", ".join(comunidade[:2])
                    if len(v.get('comunidade', [])) > 2:
                        comunidade += "..."
                opcoes.append(f"{i+1} - {comunidade} - {v.get('data_inicio', '')} a {v.get('data_fim', '')}")
            
            viagem_selecionada_idx = st.selectbox(
                "Selecione a viagem para visualizar o extrato",
                range(len(opcoes)),
                format_func=lambda x: opcoes[x],
                key="select_viagem_extrato"
            )
            
            if viagem_selecionada_idx is not None:
                viagem = viagens_filtradas[viagem_selecionada_idx]
                orcamento = viagem.get('orcamento', {})
                
                # Mostrar extrato
                st.markdown("---")
                st.markdown("### 📋 Extrato da Viagem")
                
                def formatar_moeda_html(valor):
                    return f"R$ {valor:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
                
                # Botões para download
                col1, col2 = st.columns(2)
                
                with col1:
                    # Botão para baixar PDF
                    if st.button("📄 Baixar Extrato em PDF", use_container_width=True, key="btn_pdf_extrato"):
                        pdf_buffer = gerar_pdf_extrato(viagem, orcamento)
                        st.download_button(
                            label="📥 Clique para baixar o PDF",
                            data=pdf_buffer,
                            file_name=f"extrato_{viagem.get('comunidade', '')[0] if isinstance(viagem.get('comunidade', ''), list) else viagem.get('comunidade', '')}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_pdf_extrato"
                        )
                
                with col2:
                    # Botão para baixar como HTML
                    html_content = criar_corpo_email(viagem, orcamento, formatar_moeda_html)
                    html_bytes = html_content.encode('utf-8')
                    b64_html = base64.b64encode(html_bytes).decode()
                    href_html = f'<a href="data:text/html;base64,{b64_html}" download="extrato_{viagem.get("comunidade", "")}_{datetime.now().strftime("%Y%m%d_%H%M")}.html">📧 Baixar Extrato em HTML</a>'
                    st.markdown(href_html, unsafe_allow_html=True)

with tab5:
    st.markdown("### 📝 Formulário de Feedback")
    #st.markdown("Sua opinião é muito importante para melhorarmos o sistema!")
    #st.markdown("**🔒 Este formulário é totalmente anônimo.**")
    st.markdown("---")
    
    # Inicializar estado do feedback
    if 'feedback_enviado' not in st.session_state:
        st.session_state.feedback_enviado = False
    
    if not st.session_state.feedback_enviado:
        # Seção 1: Usabilidade
        with st.expander("🎯 Facilidade de Uso", expanded=True):
            st.markdown("**1.1** Como você avalia a facilidade de uso do sistema?")
            facilidade_uso = st.radio(
                "Facilidade de uso",
                ["Muito Fácil", "Fácil", "Neutro", "Difícil", "Muito Difícil"],
                index=1,
                key="fb_facilidade",
                label_visibility="collapsed"
            )
            
            st.markdown("**1.2** O layout e a organização das informações são intuitivos?")
            layout_intuitivo = st.radio(
                "Layout intuitivo",
                ["Sim, totalmente", "Sim, em grande parte", "Mais ou menos", "Não, pouco intuitivo", "Não, nada intuitivo"],
                index=1,
                key="fb_layout",
                label_visibility="collapsed"
            )
            
            st.markdown("**1.3** Você conseguiu encontrar facilmente as funcionalidades que precisava?")
            encontrar_funcionalidades = st.radio(
                "Encontrar funcionalidades",
                ["Sempre", "Na maioria das vezes", "Às vezes", "Raramente", "Nunca"],
                index=1,
                key="fb_encontrar",
                label_visibility="collapsed"
            )
        
        # Seção 2: Funcionalidades
        with st.expander("⚙️ Funcionalidades"):
            st.markdown("**2.1** Quais funcionalidades você mais utiliza no sistema?")
            funcionalidades_usa = st.multiselect(
                "Funcionalidades utilizadas",
                [
                    "Cadastrar nova viagem",
                    "Visualizar lista de viagens",
                    "Editar viagens",
                    "Excluir viagens",
                    "Gerar extrato PDF",
                    "Gerar extrato HTML",
                    "Visualizar análises e relatórios",
                    "Receber email de confirmação"
                ],
                key="fb_funcionalidades"
            )
            
            st.markdown("**2.2** Qual funcionalidade você considera mais importante?")
            funcionalidade_importante = st.text_input(
                "Funcionalidade mais importante",
                placeholder="Digite aqui",
                key="fb_importante"
            )
            
            st.markdown("**2.3** Há alguma funcionalidade que você sente falta?")
            funcionalidade_falta = st.text_input(
                "Funcionalidade que falta",
                placeholder="Digite aqui",
                key="fb_falta"
            )
        
        # Seção 3: Desempenho
        with st.expander("🚀 Desempenho e Eficiência"):
            st.markdown("**3.1** Como você avalia a velocidade de resposta do sistema?")
            velocidade_sistema = st.radio(
                "Velocidade",
                ["Muito Rápido", "Rápido", "Aceitável", "Lento", "Muito Lento"],
                index=2,
                key="fb_velocidade",
                label_visibility="collapsed"
            )
            
            st.markdown("**3.2** O sistema atende às suas necessidades de forma eficiente?")
            atende_necessidades = st.radio(
                "Atende necessidades",
                ["Sim, plenamente", "Sim, em grande parte", "Parcialmente", "Pouco", "Não atende"],
                index=1,
                key="fb_atende",
                label_visibility="collapsed"
            )
            
            st.markdown("**3.3** Qual o tempo médio que você gasta para cadastrar uma viagem?")
            tempo_cadastro = st.radio(
                "Tempo de cadastro",
                ["Menos de 2 minutos", "2 a 5 minutos", "5 a 10 minutos", "10 a 15 minutos", "Mais de 15 minutos"],
                index=1,
                key="fb_tempo",
                label_visibility="collapsed"
            )
        
        # Seção 4: Relatórios
        with st.expander("📊 Relatórios e Extratos"):
            st.markdown("**4.1** Como você avalia a qualidade dos extratos gerados (PDF/HTML)?")
            qualidade_extratos = st.radio(
                "Qualidade dos extratos",
                ["Excelente", "Bom", "Regular", "Ruim", "Muito Ruim"],
                index=1,
                key="fb_qualidade",
                label_visibility="collapsed"
            )
            
            st.markdown("**4.2** As informações apresentadas nos relatórios são claras e completas?")
            relatorios_claros = st.radio(
                "Relatórios claros",
                ["Sim, totalmente", "Sim, em grande parte", "Mais ou menos", "Não, são confusas", "Não, faltam informações"],
                index=1,
                key="fb_claros",
                label_visibility="collapsed"
            )
            
            st.markdown("**4.3** Que tipo de informação você gostaria que fosse adicionada aos relatórios?")
            info_relatorios = st.text_area(
                "Informações adicionais",
                placeholder="Digite aqui",
                key="fb_info_relatorios",
                height=80
            )
        
        # Seção 5: Email
        with st.expander("📧 Email de Confirmação"):
            st.markdown("**5.1** Você recebe o email de confirmação após cadastrar uma viagem?")
            recebe_email = st.radio(
                "Recebe email",
                ["Sempre", "Na maioria das vezes", "Às vezes", "Raramente", "Nunca"],
                index=1,
                key="fb_recebe_email",
                label_visibility="collapsed"
            )
            
            st.markdown("**5.2** O email de confirmação é claro e útil?")
            email_claro = st.radio(
                "Email claro",
                ["Sim, muito claro", "Sim, claro", "Mais ou menos", "Não, é confuso", "Não é útil"],
                index=1,
                key="fb_email_claro",
                label_visibility="collapsed"
            )
            
            st.markdown("**5.3** Você gostaria que o email tivesse mais informações? Quais?")
            email_melhorias = st.text_area(
                "Melhorias no email",
                placeholder="Digite aqui",
                key="fb_email_melhorias",
                height=80
            )
        
        # Seção 6: Banco de Dados
        with st.expander("💾 Banco de Dados e Persistência"):
            st.markdown("**6.1** Você considera importante que os dados sejam salvos permanentemente no banco de dados?")
            importancia_banco = st.radio(
                "Importância do banco",
                ["Muito importante", "Importante", "Neutro", "Pouco importante", "Não é importante"],
                index=0,
                key="fb_banco",
                label_visibility="collapsed"
            )
            
            st.markdown("**6.2** Você confia na segurança e integridade dos seus dados?")
            confianca_dados = st.radio(
                "Confiança nos dados",
                ["Confio totalmente", "Confio em grande parte", "Neutro", "Pouco confiável", "Não confio"],
                index=1,
                key="fb_confianca",
                label_visibility="collapsed"
            )
        
        # Seção 7: Satisfação Geral
        with st.expander("⭐ Satisfação Geral"):
            st.markdown("**7.1** Em uma escala de 1 a 10, qual sua nota geral para o sistema?")
            nota_geral = st.slider(
                "Nota geral",
                min_value=1,
                max_value=10,
                value=8,
                step=1,
                key="fb_nota"
            )
            st.caption(f"Nota selecionada: {nota_geral} / 10")
            
            st.markdown("**7.2** Você recomendaria este sistema para outros usuários?")
            recomendaria = st.radio(
                "Recomendaria",
                ["Sim, definitivamente", "Sim, provavelmente", "Talvez", "Provavelmente não", "Não, definitivamente"],
                index=0,
                key="fb_recomendaria",
                label_visibility="collapsed"
            )
        
        # Seção 8: Sugestões
        with st.expander("💡 Sugestões de Melhoria"):
            st.markdown("**8.1** Quais melhorias você sugere para o sistema?")
            sugestoes_melhoria = st.text_area(
                "Sugestões",
                placeholder="Digite aqui suas sugestões",
                key="fb_sugestoes",
                height=100
            )
            
            st.markdown("**8.2** O que você mais gosta no sistema?")
            mais_gosta = st.text_area(
                "O que mais gosta",
                placeholder="Digite aqui",
                key="fb_mais_gosta",
                height=80
            )
            
            st.markdown("**8.3** O que você menos gosta no sistema?")
            menos_gosta = st.text_area(
                "O que menos gosta",
                placeholder="Digite aqui",
                key="fb_menos_gosta",
                height=80
            )
        
        # Seção 9: Uso Futuro
        with st.expander("🔮 Uso Futuro"):
            st.markdown("**9.1** Você continuaria usando este sistema no futuro?")
            continuaria_usando = st.radio(
                "Continuaria usando",
                ["Sim", "Talvez", "Não"],
                index=0,
                key="fb_continuaria",
                label_visibility="collapsed"
            )
            
            st.markdown("**9.2** Você gostaria que o sistema fosse expandido para outras áreas?")
            expansao_futuro = st.text_area(
                "Expansão para outras áreas",
                placeholder="Se sim, sugira quais áreas",
                key="fb_expansao",
                height=80
            )
        
        # Comentários adicionais
        st.markdown("---")
        st.markdown("### 💬 Comentários Adicionais")
        comentarios_adicionais = st.text_area(
            "Deixe aqui qualquer outro comentário ou sugestão",
            placeholder="Digite aqui",
            key="fb_comentarios",
            height=100
        )
        
        # Botão de envio
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            if st.button("📤 Enviar Feedback", type="primary", use_container_width=True):
                # Preparar dados (sem identificação)
                feedback_data = {
                    'data_resposta': datetime.now().strftime('%d/%m/%Y'),
                    'facilidade_uso': facilidade_uso,
                    'layout_intuitivo': layout_intuitivo,
                    'encontrar_funcionalidades': encontrar_funcionalidades,
                    'funcionalidades_usa': ', '.join(funcionalidades_usa) if funcionalidades_usa else '',
                    'funcionalidade_importante': funcionalidade_importante,
                    'funcionalidade_falta': funcionalidade_falta,
                    'velocidade_sistema': velocidade_sistema,
                    'atende_necessidades': atende_necessidades,
                    'tempo_cadastro': tempo_cadastro,
                    'qualidade_extratos': qualidade_extratos,
                    'relatorios_claros': relatorios_claros,
                    'info_relatorios': info_relatorios,
                    'recebe_email': recebe_email,
                    'email_claro': email_claro,
                    'email_melhorias': email_melhorias,
                    'importancia_banco': importancia_banco,
                    'confianca_dados': confianca_dados,
                    'nota_geral': str(nota_geral),
                    'recomendaria': recomendaria,
                    'sugestoes_melhoria': sugestoes_melhoria,
                    'mais_gosta': mais_gosta,
                    'menos_gosta': menos_gosta,
                    'continuaria_usando': continuaria_usando,
                    'expansao_futuro': expansao_futuro,
                    'comentarios_adicionais': comentarios_adicionais,
                    'data_cadastro': datetime.now().strftime('%d/%m/%Y %H:%M')
                }
                
                try:
                    db.salvar_feedback(feedback_data)
                    st.session_state.feedback_enviado = True
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Erro ao enviar feedback: {str(e)}")
    
    else:
        # Mensagem de agradecimento após o envio
        st.markdown("---")
        st.markdown("""
        <div style="
            background-color: #d4edda;
            border-left: 6px solid #28a745;
            padding: 30px;
            border-radius: 8px;
            text-align: center;
            margin: 20px 0;
        ">
            <h1 style="color: #155724; margin: 0;">🙏 MUITO OBRIGADO!</h1>
            <p style="color: #155724; font-size: 18px; margin: 15px 0 0 0;">
                Seu feedback foi enviado com sucesso e é muito importante para nós!
            </p>
            <p style="color: #155724; font-size: 16px; margin: 10px 0 0 0;">
                Sua opinião nos ajuda a melhorar continuamente o sistema.
            </p>
            <p style="color: #155724; font-size: 14px; margin: 10px 0 0 0;">
                🔒 Este feedback é totalmente anônimo.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Botão para enviar novo feedback
        if st.button("📝 Enviar novo feedback", use_container_width=True):
            st.session_state.feedback_enviado = False
            st.rerun()
        
        # Mostrar histórico de feedbacks (apenas para administradores - opcional)
        with st.expander("📊 Ver histórico de feedbacks (Administradores)"):
            feedbacks = db.carregar_feedbacks()
            if feedbacks:
                df_feedback = pd.DataFrame(feedbacks)
                # Selecionar colunas principais para exibir
                colunas_exibir = ['id', 'data_resposta', 'nota_geral', 'data_cadastro']
                df_feedback = df_feedback[colunas_exibir]
                df_feedback.columns = ['ID', 'Data Resposta', 'Nota', 'Data Cadastro']
                st.dataframe(df_feedback, use_container_width=True)
                
                # Estatísticas rápidas
                st.markdown("### 📊 Estatísticas Rápidas")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Total de Feedbacks", len(feedbacks))
                with col2:
                    notas = [int(f.get('nota_geral', 0)) for f in feedbacks if f.get('nota_geral', '').isdigit()]
                    if notas:
                        st.metric("Média de Notas", f"{sum(notas)/len(notas):.1f}")
                with col3:
                    recomendam = [f for f in feedbacks if 'definitivamente' in f.get('recomendaria', '')]
                    if recomendam:
                        st.metric("Recomendam", f"{len(recomendam)} ({len(recomendam)*100//len(feedbacks)}%)")
            else:
                st.info("Nenhum feedback cadastrado ainda.")

# ==================== TAB 6: SINCRONIZAÇÃO ====================

# ==================== TAB 6: SINCRONIZAÇÃO ====================

with tab6:
    st.markdown("### 🔄 Sincronização com GitHub")
    st.markdown("Gerencie a sincronização dos dados com o repositório GitHub.")
    
    # Verificar configuração
    sync = GitHubSync()
    
    # Status da sincronização
    st.markdown("#### 📊 Status do Repositório")
    
    col1, col2 = st.columns(2)
    with col1:
        st.metric("GitHub Habilitado", "✅ Sim" if sync.enabled else "❌ Não")
        st.metric("Modo Teste", "✅ Ativado" if sync.modo_teste else "❌ Desativado")
        st.metric("Token Configurado", "✅ Sim" if sync.token else "❌ Não")
    with col2:
        st.metric("Repositório", sync.repo_path if sync.repo_path else "Não configurado")
        if sync.repo:
            try:
                ultimo_commit = sync.repo.head.commit
                st.metric("Último Commit", ultimo_commit.hexsha[:7])
                st.metric("Autor", f"{ultimo_commit.author.name}")
            except:
                st.metric("Status", "Repositório vazio")
        else:
            st.metric("Status", "Repositório não encontrado")
    
    st.markdown("---")
    
    # Testar Configuração
    st.markdown("#### 🔍 Testar Configuração")
    if st.button("🔍 Testar Configuração do GitHub", use_container_width=True):
        with st.spinner("Testando configuração..."):
            try:
                sync = testar_github()
                st.json({
                    'enabled': sync.enabled,
                    'modo_teste': sync.modo_teste,
                    'repo_path': sync.repo_path,
                    'token_configurado': bool(sync.token),
                    'remote_configurado': bool(sync.remote_url)
                })
                
                # Fazer um commit de teste se possível
                if sync.enabled and sync.repo and sync.token:
                    try:
                        test_file = os.path.join(sync.repo_path, 'teste_automacao.txt')
                        with open(test_file, 'w') as f:
                            f.write(f"Teste automático - {datetime.now()}\n")
                        
                        result = sync.commit_e_push("🔧 Teste de automação")
                        if result['success']:
                            st.success(f"✅ Teste concluído! {result.get('message', '')}")
                        else:
                            st.error(f"❌ Erro no teste: {result.get('error', '')}")
                    except Exception as e:
                        st.error(f"❌ Erro: {str(e)}")
            except Exception as e:
                st.error(f"❌ Erro ao testar: {str(e)}")
    
    st.markdown("---")
    
    # Ações
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📤 Sincronizar Agora", type="primary", use_container_width=True):
            with st.spinner("🔄 Sincronizando com GitHub..."):
                result = sincronizar_github("manual")
                if result['success']:
                    st.success(f"✅ Sincronização concluída! {result.get('message', '')}")
                else:
                    st.error(f"❌ Erro na sincronização: {result.get('error', '')}")
    
    with col2:
        if st.button("📊 Exportar Dados Apenas", use_container_width=True):
            with st.spinner("📊 Exportando dados..."):
                sync = GitHubSync()
                result = sync.exportar_dados()
                if result['success']:
                    st.success(f"✅ Dados exportados! {result['total_viagens']} viagens salvas.")
                    st.info(f"📁 Arquivos salvos em: {sync.repo_path}/dados/")
                else:
                    st.error(f"❌ Erro na exportação: {result.get('error', '')}")
    
    st.markdown("---")
    
    # Configurações
    with st.expander("⚙️ Configurações do GitHub"):
        st.markdown("""
        **Variáveis de ambiente necessárias no .env:**
        
        ```env
        # Configurações do GitHub
        GITHUB_ENABLED=True
        GITHUB_MODO_TESTE=False  # True = testar sem push, False = push real
        GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxx  # Seu token aqui
        GITHUB_REPO_PATH=/home/michael/Quilombo-Viagens-master
        GITHUB_BRANCH=main
        GITHUB_USER_NAME=Michael Cardoso
        GITHUB_USER_EMAIL=michael@email.com
        """)