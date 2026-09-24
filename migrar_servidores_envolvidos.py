# migrar_servidores_envolvidos.py
"""
Script para adicionar a coluna 'servidores_envolvidos' na tabela 'viagens'
do banco de dados SQLite existente, SEM PERDER DADOS.

Execute uma única vez:
    python migrar_servidores_envolvidos.py
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_FILE = "viagens.db"

def backup_banco():
    """Cria um backup do banco antes de qualquer alteração"""
    if os.path.exists(DB_FILE):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_viagens_{timestamp}.db"
        shutil.copy2(DB_FILE, backup_file)
        print(f"✅ Backup criado: {backup_file}")
        return backup_file
    else:
        print(f"❌ Banco de dados '{DB_FILE}' não encontrado!")
        return None

def verificar_coluna_existe(cursor, tabela, coluna):
    """Verifica se uma coluna já existe na tabela"""
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas = [col[1] for col in cursor.fetchall()]
    return coluna in colunas

def adicionar_coluna_servidores_envolvidos():
    """Adiciona a coluna 'servidores_envolvidos' na tabela 'viagens'"""
    
    print("=" * 60)
    print("🔄 MIGRAÇÃO: Adicionar coluna 'servidores_envolvidos'")
    print("=" * 60)
    
    # 1. Backup
    backup = backup_banco()
    if not backup:
        return False
    
    # 2. Conectar ao banco
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        print(f"✅ Conectado ao banco: {DB_FILE}")
    except Exception as e:
        print(f"❌ Erro ao conectar: {str(e)}")
        return False
    
    # 3. Verificar se a coluna já existe
    if verificar_coluna_existe(cursor, 'viagens', 'servidores_envolvidos'):
        print("ℹ️  A coluna 'servidores_envolvidos' JÁ EXISTE. Nada a fazer.")
        conn.close()
        return True
    
    # 4. Verificar estrutura atual
    cursor.execute("PRAGMA table_info(viagens)")
    colunas_antes = [col[1] for col in cursor.fetchall()]
    print(f"\n📋 Colunas atuais ({len(colunas_antes)}):")
    for col in colunas_antes:
        print(f"   • {col}")
    
    # 5. Contar registros antes
    cursor.execute("SELECT COUNT(*) FROM viagens")
    total_registros = cursor.fetchone()[0]
    print(f"\n📊 Total de registros ANTES: {total_registros}")
    
    # 6. Adicionar a coluna DEPOIS de 'quantidade_servidores'
    # SQLite não permite escolher posição diretamente, então usamos ADD COLUMN
    # A coluna será adicionada ao final, mas isso não afeta a funcionalidade
    try:
        cursor.execute("""
            ALTER TABLE viagens 
            ADD COLUMN servidores_envolvidos TEXT DEFAULT ''
        """)
        conn.commit()
        print("\n✅ Coluna 'servidores_envolvidos' adicionada com sucesso!")
    except Exception as e:
        print(f"\n❌ Erro ao adicionar coluna: {str(e)}")
        conn.close()
        return False
    
    # 7. Verificar estrutura após
    cursor.execute("PRAGMA table_info(viagens)")
    colunas_depois = [col[1] for col in cursor.fetchall()]
    print(f"\n📋 Colunas após migração ({len(colunas_depois)}):")
    for col in colunas_depois:
        marcador = " ⭐ NOVA" if col == 'servidores_envolvidos' else ""
        print(f"   • {col}{marcador}")
    
    # 8. Contar registros após
    cursor.execute("SELECT COUNT(*) FROM viagens")
    total_registros_depois = cursor.fetchone()[0]
    print(f"\n📊 Total de registros DEPOIS: {total_registros_depois}")
    
    if total_registros == total_registros_depois:
        print("✅ Nenhum dado foi perdido!")
    else:
        print(f"⚠️  ATENÇÃO: Diferença de registros! {total_registros} → {total_registros_depois}")
    
    # 9. Preencher registros antigos com valor padrão
    try:
        cursor.execute("""
            UPDATE viagens 
            SET servidores_envolvidos = 'Não informado' 
            WHERE servidores_envolvidos IS NULL OR servidores_envolvidos = ''
        """)
        conn.commit()
        registros_atualizados = cursor.rowcount
        print(f"\n✅ {registros_atualizados} registros antigos atualizados com valor padrão")
    except Exception as e:
        print(f"⚠️  Erro ao preencher registros antigos: {str(e)}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ MIGRAÇÃO CONCLUÍDA COM SUCESSO!")
    print(f"📦 Backup salvo em: {backup}")
    print("=" * 60)
    return True

if __name__ == "__main__":
    adicionar_coluna_servidores_envolvidos()