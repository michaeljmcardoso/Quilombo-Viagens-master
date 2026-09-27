# github_sync.py
import os
import csv
import json
from datetime import datetime
from urllib.parse import urlparse
import git
from git import Repo, Actor
import sqlite3
import subprocess

def is_streamlit_cloud(app_url=None):
    """Indica se o aplicativo está sendo executado no Streamlit Cloud."""
    cloud_markers = (
        'STREAMLIT_CLOUD',
        'STREAMLIT_SHARING',
        'STREAMLIT_SHARING_MODE',
        'STREAMLIT_RUNTIME',
        'STREAMLIT_RUNTIME_ENV',
        'STREAMLIT_RUNTIME_ENVIRONMENT',
    )
    if any(os.getenv(marker) for marker in cloud_markers):
        return True

    if os.getenv('IS_STREAMLIT_CLOUD', '').strip().lower() in {'1', 'true', 'yes'}:
        return True

    hostname = urlparse(app_url or '').hostname or ''
    return hostname == 'streamlit.io' or hostname.endswith(('.streamlit.io', '.streamlit.app'))

def get_repo_path():
    """Obtém o caminho do repositório automaticamente"""
    # Se estiver no Streamlit Cloud, usa o diretório atual
    if is_streamlit_cloud():
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
        self.repo_path = get_repo_path()
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
        """Atualiza as exportações mais recentes sem criar arquivos históricos."""
        try:
            db_path = os.path.join(self.repo_path, db_file)
            if not os.path.exists(db_path):
                return {
                    'success': False,
                    'error': f'Banco de dados não encontrado: {db_path}'
                }
            
            with sqlite3.connect(db_path) as conn:
                conn.row_factory = sqlite3.Row
                viagens = [
                    dict(row)
                    for row in conn.execute("SELECT * FROM viagens ORDER BY id DESC")
                ]
                tabelas = {
                    row['name']
                    for row in conn.execute(
                        "SELECT name FROM sqlite_master WHERE type = 'table'"
                    )
                }
                feedbacks = []
                if 'feedback' in tabelas:
                    feedbacks = [
                        dict(row)
                        for row in conn.execute("SELECT * FROM feedback ORDER BY id DESC")
                    ]
                colunas_viagens = [
                    row['name']
                    for row in conn.execute("PRAGMA table_info(viagens)")
                ]

            data_dir = os.path.join(self.repo_path, 'dados')
            os.makedirs(data_dir, exist_ok=True)

            csv_path = os.path.join(data_dir, 'viagens_latest.csv')
            with open(csv_path, 'w', newline='', encoding='utf-8-sig') as arquivo_csv:
                writer = csv.DictWriter(arquivo_csv, fieldnames=colunas_viagens)
                writer.writeheader()
                writer.writerows(viagens)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            json_path = os.path.join(data_dir, 'dados_latest.json')
            dados = {
                'data_exportacao': timestamp,
                'total_viagens': len(viagens),
                'viagens': viagens,
                'feedbacks': feedbacks
            }
            with open(json_path, 'w', encoding='utf-8') as arquivo_json:
                json.dump(dados, arquivo_json, ensure_ascii=False, indent=2, default=str)
            
            return {
                'success': True,
                'timestamp': timestamp,
                'total_viagens': len(viagens),
                'csv_path': csv_path,
                'json_path': json_path,
                'files': [
                    os.path.relpath(db_path, self.repo_path),
                    os.path.relpath(csv_path, self.repo_path),
                    os.path.relpath(json_path, self.repo_path)
                ]
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def commit_e_push(self, mensagem="Atualização automática do sistema", arquivos=None):
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
        if not arquivos:
            return {
                'success': False,
                'error': 'Nenhum arquivo foi informado para sincronização'
            }
        
        try:
            self.repo.index.add(arquivos)

            if self.repo.index.diff('HEAD', paths=arquivos):
                author = Actor(self.user_name, self.user_email)
                commit_message = f"{mensagem} - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}"
                commit_result = subprocess.run(
                    [
                        'git', '-c', f'user.name={author.name}',
                        '-c', f'user.email={author.email}',
                        'commit', '--only', '-m', commit_message, '--', *arquivos
                    ],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if commit_result.returncode != 0:
                    return {
                        'success': False,
                        'error': commit_result.stderr.strip() or commit_result.stdout.strip()
                    }
                subprocess.run(
                    ['git', 'reset', '--quiet', 'HEAD', '--', *arquivos],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=30
                )
            else:
                commit_message = None

            commit_hash = self.repo.head.commit.hexsha[:7]
            
            if self.modo_teste:
                return {
                    'success': True,
                    'message': (
                        f'✅ Commit no modo teste: {commit_message}'
                        if commit_message
                        else 'Nenhuma alteração para commitar no modo teste'
                    ),
                    'commit_hash': commit_hash
                }
            
            # Fazer push usando subprocess
            remote_url = f"https://{self.user_name}:{self.token}@github.com/{self.user_name}/Quilombo-Viagens-master.git"
            
            result = subprocess.run(
                ['git', 'push', remote_url, f'HEAD:{self.branch}'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': (
                        f'✅ Commit enviado: {commit_message}'
                        if commit_message
                        else '✅ Sincronização concluída; não havia novas alterações'
                    ),
                    'commit_hash': commit_hash
                }
            else:
                # Tentar com git push normal
                result2 = subprocess.run(
                    ['git', 'push', 'origin', self.branch],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result2.returncode == 0:
                    return {
                        'success': True,
                        'message': (
                            f'✅ Commit enviado (via origin): {commit_message}'
                            if commit_message
                            else '✅ Sincronização concluída via origin; sem novas alterações'
                        ),
                        'commit_hash': commit_hash
                    }
                else:
                    return {
                        'success': False,
                        'error': result2.stderr.strip() or result.stderr.strip()
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
            if viagem_data:
                comunidade = viagem_data.get('comunidade', '')
                if isinstance(comunidade, list):
                    comunidade = ", ".join(comunidade)
                if comunidade:
                    mensagem += f" - {comunidade}"
        elif acao == "exclusao":
            mensagem = "🗑️ Viagem excluída"
        elif acao == "feedback":
            mensagem = "📝 Novo feedback recebido"
        else:
            mensagem = f"🔄 Sincronização - {acao}"
        
        return self.commit_e_push(mensagem, export_result['files'])

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