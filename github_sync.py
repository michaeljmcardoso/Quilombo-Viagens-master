# github_sync.py - Versão para Streamlit Cloud
import os
import json
import pandas as pd
from datetime import datetime
import git
from git import Repo, Actor
import sqlite3
import subprocess
import tempfile

def get_repo_path():
    """Obtém o caminho do repositório automaticamente"""
    # Se estiver no Streamlit Cloud, usa o diretório atual
    if 'STREAMLIT_CLOUD' in os.environ or 'STREAMLIT_SHARING' in os.environ:
        return os.getcwd()
    # Caso contrário, usa o caminho do .env
    env_path = os.getenv('GITHUB_REPO_PATH', '')
    if env_path:
        return env_path
    return os.getcwd()

class GitHubSync:
    """Classe para sincronizar dados com o GitHub usando token"""
    
    def __init__(self):
        self.enabled = os.getenv('GITHUB_ENABLED', 'False').lower() == 'true'
        self.modo_teste = os.getenv('GITHUB_MODO_TESTE', 'False').lower() == 'true'
        self.repo_path = get_repo_path()  # Caminho automático
        self.branch = os.getenv('GITHUB_BRANCH', 'main')
        self.user_name = os.getenv('GITHUB_USER_NAME', 'QuilomboViagens')
        self.user_email = os.getenv('GITHUB_USER_EMAIL', 'quilomboviagens@gmail.com')
        self.token = os.getenv('GITHUB_TOKEN', '').strip()
        
        print(f"📁 Repositório path: {self.repo_path}")
        print(f"📌 Modo teste: {'ATIVADO' if self.modo_teste else 'DESATIVADO'}")
        print(f"📌 Token configurado: {'✅ Sim' if self.token else '❌ Não'}")
        
        # Verificar se o diretório é um repositório Git
        self.repo = None
        if self.enabled and self.repo_path:
            try:
                # Verificar se é um repositório Git
                git_dir = os.path.join(self.repo_path, '.git')
                if os.path.exists(git_dir):
                    self.repo = Repo(self.repo_path)
                    print(f"✅ Repositório GitHub carregado: {self.repo_path}")
                    
                    # Configurar autor para commits
                    if self.repo:
                        with self.repo.config_writer() as config:
                            config.set_value('user', 'name', self.user_name)
                            config.set_value('user', 'email', self.user_email)
                else:
                    print(f"⚠️ Não é um repositório Git: {self.repo_path}")
                    print("   Inicializando repositório...")
                    self.repo = Repo.init(self.repo_path)
                    print(f"✅ Repositório inicializado: {self.repo_path}")
                    
                    # Criar README
                    readme_path = os.path.join(self.repo_path, 'README.md')
                    if not os.path.exists(readme_path):
                        with open(readme_path, 'w') as f:
                            f.write("# QuilomboViagens - Dados\n\nRepositório automático para dados do sistema.")
                        self.repo.index.add(['README.md'])
                        self.repo.index.commit("Initial commit")
                        
            except Exception as e:
                print(f"❌ Erro ao carregar repositório: {str(e)}")
                self.repo = None
    
    def exportar_dados(self, db_file="viagens.db"):
        """Exporta os dados do banco para JSON e CSV"""
        try:
            # Verificar se o banco existe
            if not os.path.exists(db_file):
                return {
                    'success': False,
                    'error': f'Banco de dados não encontrado: {db_file}'
                }
            
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
            
            # Criar diretório de dados
            data_dir = os.path.join(self.repo_path, 'dados')
            os.makedirs(data_dir, exist_ok=True)
            
            # Salvar como CSV
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            # Exportar viagens
            csv_path_viagens = os.path.join(data_dir, f'viagens_{timestamp}.csv')
            df_viagens.to_csv(csv_path_viagens, index=False, encoding='utf-8-sig')
            
            csv_path_viagens_latest = os.path.join(data_dir, 'viagens_latest.csv')
            df_viagens.to_csv(csv_path_viagens_latest, index=False, encoding='utf-8-sig')
            
            # Exportar feedbacks
            if not df_feedback.empty:
                csv_path_feedback = os.path.join(data_dir, f'feedback_{timestamp}.csv')
                df_feedback.to_csv(csv_path_feedback, index=False, encoding='utf-8-sig')
                
                csv_path_feedback_latest = os.path.join(data_dir, 'feedback_latest.csv')
                df_feedback.to_csv(csv_path_feedback_latest, index=False, encoding='utf-8-sig')
            
            # Exportar JSON
            json_path = os.path.join(data_dir, f'dados_{timestamp}.json')
            dados = {
                'data_exportacao': timestamp,
                'total_viagens': len(df_viagens),
                'viagens': df_viagens.to_dict('records'),
                'feedbacks': df_feedback.to_dict('records') if not df_feedback.empty else []
            }
            
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
            
            json_path_latest = os.path.join(data_dir, 'dados_latest.json')
            with open(json_path_latest, 'w', encoding='utf-8') as f:
                json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
            
            return {
                'success': True,
                'timestamp': timestamp,
                'total_viagens': len(df_viagens)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def commit_e_push(self, mensagem="Atualização automática do sistema"):
        """Faz commit e push das alterações para o GitHub"""
        if not self.enabled or not self.repo:
            return {
                'success': False,
                'error': 'GitHub não habilitado ou repositório não encontrado'
            }
        
        if not self.token and not self.modo_teste:
            return {
                'success': False,
                'error': 'Token não configurado'
            }
        
        try:
            # Adicionar todas as alterações
            self.repo.index.add('*')
            
            # Verificar se há alterações
            if not self.repo.index.diff('HEAD'):
                return {
                    'success': True,
                    'message': 'Nenhuma alteração para commitar'
                }
            
            # Fazer commit
            author = Actor(self.user_name, self.user_email)
            commit_message = f"{mensagem} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
            self.repo.index.commit(commit_message, author=author)
            commit_hash = self.repo.head.commit.hexsha[:7]
            
            if self.modo_teste:
                return {
                    'success': True,
                    'message': f'✅ Commit no modo teste: {commit_message}',
                    'commit_hash': commit_hash
                }
            
            # Fazer push usando subprocess
            remote_url = f"https://{self.user_name}:{self.token}@github.com/{self.user_name}/Quilombo-Viagens-master.git"
            
            result = subprocess.run(
                ['git', 'push', remote_url, f'HEAD:{self.branch}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'✅ Commit enviado: {commit_message}',
                    'commit_hash': commit_hash
                }
            else:
                # Tentar com git push normal
                result2 = subprocess.run(
                    ['git', 'push', 'origin', self.branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result2.returncode == 0:
                    return {
                        'success': True,
                        'message': f'✅ Commit enviado (via origin): {commit_message}',
                        'commit_hash': commit_hash
                    }
                else:
                    return {
                        'success': False,
                        'error': result2.stderr
                    }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
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
        
        # Montar mensagem
        if acao == "cadastro":
            mensagem = "📝 Nova viagem cadastrada"
            if viagem_data:
                comunidade = viagem_data.get('comunidade', '')
                if isinstance(comunidade, list):
                    comunidade = ", ".join(comunidade)
                if comunidade:
                    mensagem += f" - {comunidade}"
        elif acao == "edicao":
            mensagem = "✏️ Viagem editada"
        elif acao == "exclusao":
            mensagem = "🗑️ Viagem excluída"
        elif acao == "feedback":
            mensagem = "📝 Novo feedback recebido"
        else:
            mensagem = f"🔄 Sincronização - {acao}"
        
        return self.commit_e_push(mensagem)

def sincronizar_github(acao="cadastro", viagem_data=None):
    """Função wrapper para sincronizar com GitHub"""
    sync = GitHubSync()
    
    if not sync.enabled:
        return {
            'success': False,
            'error': 'GitHub não habilitado'
        }
    
    if not sync.repo:
        return {
            'success': False,
            'error': 'Repositório não encontrado'
        }
    
    return sync.sincronizar(acao, viagem_data)

def testar_github():
    """Testa a configuração do GitHub"""
    sync = GitHubSync()
    
    return {
        'enabled': sync.enabled,
        'modo_teste': sync.modo_teste,
        'repo_path': sync.repo_path,
        'token_configurado': bool(sync.token),
        'repo_carregado': bool(sync.repo)
    }