# salve como: corrigir_banco.py
import sqlite3
import os

def corrigir_banco():
    db_file = "viagens.db"
    
    # Verificar se o banco existe
    if not os.path.exists(db_file):
        print(f"❌ Banco de dados {db_file} não encontrado!")
        return
    
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    
    # Verificar se a tabela feedback existe
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='feedback'")
    tabela_existe = cursor.fetchone()
    
    if tabela_existe:
        print("✅ Tabela feedback já existe")
        
        # Verificar estrutura
        cursor.execute("PRAGMA table_info(feedback)")
        colunas = [col[1] for col in cursor.fetchall()]
        print(f"Colunas existentes: {colunas}")
        
        if 'data_resposta' not in colunas:
            print("⚠️ Estrutura incorreta. Recriando tabela...")
            cursor.execute("DROP TABLE feedback")
            tabela_existe = False
    
    if not tabela_existe:
        # Criar tabela
        cursor.execute('''
            CREATE TABLE feedback (
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
        print("✅ Tabela feedback criada com sucesso!")
    
    conn.commit()
    conn.close()
    print("✅ Correção concluída!")

if __name__ == "__main__":
    corrigir_banco()