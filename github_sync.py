# github_sync.py
import os
import json
import pandas as pd
from datetime import datetime
import git
from git import Repo, Actor
import sqlite3
import subprocess

class GitHubSync:
    """Classe para sincronizar dados com o GitHub usando token"""
    
    def __init__(self):
        self.enabled = os.getenv('GITHUB_ENABLED', 'False').lower() == 'true'
        self.modo_teste = os.getenv('GITHUB_MODO_TESTE', 'False').lower() == 'true'
        self.repo_path = os.getenv('GITHUB_REPO_PATH', '')
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        self.user_name = os.getenv('GITHUB_USER_NAME', 'QuilomboViagens')
        self.user_email = os.getenv('GITHUB_USER_EMAIL', 'quilomboviagens@gmail.com')
        self.token = os.getenv('GITHUB_TOKEN', '')
        
        # Configurar URL com token se disponível
        self.remote_url = None
        if self.token and self.enabled:
            self.remote_url = f"https://{self.token}@github.com/michaeljmcardoso/Quilombo-Viagens-master.git"
        
        if self.enabled and self.repo_path:
            try:
                self.repo = Repo(self.repo_path)
                print(f"✅ Repositório GitHub carregado: {self.repo_path}")
                
                # Configurar remote com token
                if self.remote_url:
                    try:
                        if 'origin' in self.repo.remotes:
                            self.repo.remotes.origin.set_url(self.remote_url)
                        else:
                            self.repo.create_remote('origin', self.remote_url)
                        print(f"✅ Remote configurado com token")
                    except Exception as e:
                        print(f"⚠️ Erro ao configurar remote: {str(e)}")
                        
            except Exception as e:
                print(f"❌ Erro ao carregar repositório: {str(e)}")
                self.repo = None
        else:
            self.repo = None
        
        print(f"📌 Modo teste: {'ATIVADO' if self.modo_teste else 'DESATIVADO'}")
        print(f"📌 Token configurado: {'✅ Sim' if self.token else '❌ Não'}")
    
    def exportar_dados(self, db_file="viagens.db"):
        """Exporta os dados do banco para JSON e CSV"""
        try:
            # Conectar ao banco
            conn = sqlite3.connect(db_file)
            
            # Exportar viagens
            df_viagens = pd.read_sql_query("SELECT * FROM viagens ORDER BY id DESC", conn)
            
            # Exportar feedbacks
            try:
                df_feedback = pd.read_sql_query("SELECT * FROM feedback ORDER BY id DESC", conn)
            except:
                df_feedback = pd.DataFrame()
            
            conn.close()
            
            # Criar diretório de dados se não existir
            data_dir = os.path.join(self.repo_path, 'dados')
            os.makedirs(data_dir, exist_ok=True)
            
            # Salvar como CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Exportar viagens
            csv_path_viagens = os.path.join(data_dir, f'viagens_{timestamp}.csv')
            df_viagens.to_csv(csv_path_viagens, index=False, encoding='utf-8-sig')
            
            # Exportar viagens (versão mais recente sempre)
            csv_path_viagens_latest = os.path.join(data_dir, 'viagens_latest.csv')
            df_viagens.to_csv(csv_path_viagens_latest, index=False, encoding='utf-8-sig')
            
            # Exportar feedbacks se houver
            if not df_feedback.empty:
                csv_path_feedback = os.path.join(data_dir, f'feedback_{timestamp}.csv')
                df_feedback.to_csv(csv_path_feedback, index=False, encoding='utf-8-sig')
                
                csv_path_feedback_latest = os.path.join(data_dir, 'feedback_latest.csv')
                df_feedback.to_csv(csv_path_feedback_latest, index=False, encoding='utf-8-sig')
            
            # Exportar como JSON
            json_path = os.path.join(data_dir, f'dados_{timestamp}.json')
            dados = {
                'data_exportacao': timestamp,
                'total_viagens': len(df_viagens),
                'viagens': df_viagens.to_dict('records'),
                'feedbacks': df_feedback.to_dict('records') if not df_feedback.empty else []
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
            
            # JSON mais recente
            json_path_latest = os.path.join(data_dir, 'dados_latest.json')
            with open(json_path_latest, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
            
            return {
                'success': True,
                'timestamp': timestamp,
                'csv_path': csv_path_viagens,
                'json_path': json_path,
                'total_viagens': len(df_viagens)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def commit_e_push(self, mensagem="Atualização automática do sistema"):
        """Faz commit e push das alterações para o GitHub usando token"""
        if not self.enabled or not self.repo:
            return {
                'success': False,
                'error': 'GitHub não habilitado ou repositório não encontrado'
            }
        
        if not self.token and not self.modo_teste:
            return {
                'success': False,
                'error': 'Token não configurado. Configure GITHUB_TOKEN no .env'
            }
        
        try:
            # Adicionar todas as alterações
            self.repo.index.add('*')
            
            # Verificar se há alterações para commit
            if not self.repo.index.diff('HEAD'):
                return {
                    'success': True,
                    'message': 'Nenhuma alteração para commitar'
                }
            
            # Configurar autor
            author = Actor(self.user_name, self.user_email)
            
            # Fazer commit
            commit_message = f"{mensagem} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.repo.index.commit(commit_message, author=author)
            commit_hash = self.repo.head.commit.hexsha[:7]
            
            # Se for modo teste, não faz push
            if self.modo_teste:
                return {
                    'success': True,
                    'message': f'✅ Commit feito no modo teste (sem push): {commit_message}',
                    'commit_hash': commit_hash,
                    'modo_teste': True
                }
            
            # Fazer push usando subprocess
            print(f"📤 Enviando para GitHub com token...")
            result = subprocess.run(
                ['git', 'push', 'origin', self.branch],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'Commit enviado com sucesso: {commit_message}',
                    'commit_hash': commit_hash,
                    'output': result.stdout
                }
            else:
                return {
                    'success': False,
                    'error': f'Erro no push: {result.stderr}',
                    'output': result.stderr
                }
            
        except Exception as e:
            error_msg = str(e)
            if 'authentication' in error_msg.lower() or '403' in error_msg:
                return {
                    'success': False,
                    'error': 'Erro de autenticação. Verifique o token.',
                    'detalhes': error_msg
                }
            return {
                'success': False,
                'error': error_msg
            }
    
    def sincronizar(self, acao="cadastro", viagem_data=None):
        """Sincroniza os dados com o GitHub"""
        if not self.enabled:
            return {
                'success': False,
                'error': 'GitHub não habilitado'
            }
        
        # Exportar dados
        export_result = self.exportar_dados()
        if not export_result['success']:
            return export_result
        
        # Montar mensagem de commit
        if acao == "cadastro":
            mensagem = f"📝 Nova viagem cadastrada"
            if viagem_data:
                comunidade = viagem_data.get('comunidade', '')
                if isinstance(comunidade, list):
                    comunidade = ", ".join(comunidade)
                mensagem += f" - {comunidade}"
        elif acao == "edicao":
            mensagem = "✏️ Viagem editada"
            if viagem_data:
                comunidade = viagem_data.get('comunidade', '')
                if isinstance(comunidade, list):
                    comunidade = ", ".join(comunidade)
                mensagem += f" - {comunidade}"
        elif acao == "exclusao":
            mensagem = "🗑️ Viagem excluída"
        elif acao == "feedback":
            mensagem = "📝 Novo feedback recebido"
        else:
            mensagem = f"🔄 Sincronização automática - {acao}"
        
        # Fazer commit e push
        return self.commit_e_push(mensagem)

def sincronizar_github(acao="cadastro", viagem_data=None):
    """Função wrapper para sincronizar com GitHub"""
    sync = GitHubSync()
    
    if not sync.enabled:
        return {
            'success': False,
            'error': 'GitHub não habilitado. Configure GITHUB_ENABLED=True no .env'
        }
    
    if not sync.repo:
        return {
            'success': False,
            'error': 'Repositório não encontrado. Verifique GITHUB_REPO_PATH'
        }
    
    return sync.sincronizar(acao, viagem_data)

def testar_github():
    """Testa a configuração do GitHub"""
    sync = GitHubSync()
    
    print("🔍 TESTANDO CONFIGURAÇÃO DO GITHUB")
    print("-" * 40)
    print(f"GitHub Habilitado: {sync.enabled}")
    print(f"Modo Teste: {sync.modo_teste}")
    print(f"Repo Path: {sync.repo_path}")
    print(f"Branch: {sync.branch}")
    print(f"Token Configurado: {'✅ Sim' if sync.token else '❌ Não'}")
    print(f"Remote Configurado: {'✅ Sim' if sync.remote_url else '❌ Não'}")
    
    if sync.repo:
        try:
            status = sync.repo.git.status()
            print(f"Status do Repo:\n{status}")
        except:
            pass
    
    return sync