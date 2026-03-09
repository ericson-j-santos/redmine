#!/usr/bin/env python3
"""
Script para importar tarefas do Proposta Suite para o Redmine
Lê o CSV de tarefas e cria issues organizadas por fase
"""

import csv
import os
from redminelib import Redmine
from redminelib.exceptions import ResourceNotFoundError


# ============================================================================
# CONFIGURAÇÕES - ATUALIZE AQUI!
# ============================================================================

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'  # Obtida em: My Account > API access key

PROJECT_IDENTIFIER = 'proposta-suite'
PROJECT_NAME = 'Proposta Suite'
PROJECT_DESCRIPTION = 'MVP FastAPI + Vue 3 para propostas imobiliárias'

CSV_FILE = 'projeto/proposta_suite_redmine_tasks.csv'

# Mapeamento de Status do CSV para ID do Redmine
STATUS_MAP = {
    'Closed': 5,        # Fechada
    'In Progress': 2,   # Em andamento
    'New': 1            # Nova
}

# Mapeamento de Tracker do CSV para ID do Redmine
TRACKER_MAP = {
    'Task': 2,          # Funcionalidade (padrão do Redmine pt-BR)
    'Feature': 2,       # Funcionalidade
    'Bug': 1            # Defeito
}


# ============================================================================
# FUNÇÕES
# ============================================================================

def connect_redmine():
    """Conecta ao Redmine com a API key"""
    print(f"🔌 Conectando ao Redmine: {REDMINE_URL}")
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    
    # Testa a conexão
    try:
        user = redmine.user.get('current')
        print(f"✅ Conectado como: {user.firstname} {user.lastname}")
        return redmine
    except Exception as e:
        print(f"❌ Erro na conexão: {e}")
        print("\n💡 DICA: Verifique se:")
        print("   1. O servidor Redmine está rodando")
        print("   2. A chave API está correta")
        print("   3. Acesse: http://localhost:3001/my/account")
        raise


def create_project(redmine):
    """Cria o projeto Proposta Suite no Redmine"""
    print(f"\n📁 Criando projeto: {PROJECT_NAME}")
    
    try:
        # Verifica se projeto já existe
        project = redmine.project.get(PROJECT_IDENTIFIER)
        print(f"⚠️  Projeto '{PROJECT_NAME}' já existe!")
        return project
    except ResourceNotFoundError:
        # Projeto não existe, criar
        project = redmine.project.create(
            name=PROJECT_NAME,
            identifier=PROJECT_IDENTIFIER,
            description=PROJECT_DESCRIPTION,
            is_public=True
        )
        print(f"✅ Projeto criado: {project.name} (ID: {project.id})")
        return project


def read_csv_tasks(csv_path):
    """Lê as tarefas do arquivo CSV"""
    print(f"\n📋 Lendo tarefas do CSV: {csv_path}")
    
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Arquivo CSV não encontrado: {csv_path}")
    
    tasks = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            tasks.append(row)
    
    print(f"✅ {len(tasks)} tarefas encontradas")
    return tasks


def import_tasks(redmine, project_id, tasks):
    """Importa as tarefas para o Redmine"""
    print(f"\n🚀 Importando {len(tasks)} tarefas para o projeto...")
    
    created = 0
    skipped = 0
    errors = 0
    
    for idx, task in enumerate(tasks, 1):
        tracker = task.get('Tracker', 'Task')
        subject = task.get('Subject', 'Sem título')
        description = task.get('Description', '')
        status = task.get('Status', 'New')
        fase = task.get('Fase', '')
        
        # Adiciona fase à descrição
        if fase:
            description = f"**Fase:** {fase}\n\n{description}"
        
        try:
            # Mapeia tracker e status
            tracker_id = TRACKER_MAP.get(tracker, 2)  # Default: Task
            status_id = STATUS_MAP.get(status, 1)      # Default: New
            
            # Cria a issue
            issue = redmine.issue.create(
                project_id=project_id,
                subject=subject,
                description=description,
                tracker_id=tracker_id,
                status_id=status_id
            )
            
            print(f"  [{idx}/{len(tasks)}] ✅ #{issue.id}: {subject[:50]}")
            created += 1
            
        except Exception as e:
            print(f"  [{idx}/{len(tasks)}] ❌ Erro: {subject[:50]} - {e}")
            errors += 1
    
    print(f"\n📊 RESUMO DA IMPORTAÇÃO:")
    print(f"   ✅ Criadas: {created}")
    print(f"   ⚠️  Ignoradas: {skipped}")
    print(f"   ❌ Erros: {errors}")
    print(f"   📝 Total: {len(tasks)}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Função principal"""
    print("=" * 70)
    print("🎯 IMPORTAÇÃO PROPOSTA SUITE → REDMINE")
    print("=" * 70)
    
    # Verifica se a API key foi configurada
    if API_KEY == 'COLOQUE_SUA_CHAVE_API_AQUI':
        print("\n❌ ERRO: Você precisa configurar a API_KEY!")
        print("\n📝 COMO OBTER A CHAVE API:")
        print("   1. Acesse: http://localhost:3001")
        print("   2. Login: admin / admin")
        print("   3. Clique em 'My account' (canto superior direito)")
        print("   4. No menu lateral, clique em 'API access key'")
        print("   5. Clique em 'Show' para ver a chave")
        print("   6. Copie a chave e cole na variável API_KEY deste script")
        print("\n💡 Após configurar, execute novamente:")
        print(f"   python3 {__file__}")
        return
    
    try:
        # 1. Conectar ao Redmine
        redmine = connect_redmine()
        
        # 2. Criar projeto
        project = create_project(redmine)
        
        # 3. Ler tarefas do CSV
        tasks = read_csv_tasks(CSV_FILE)
        
        # 4. Importar tarefas
        import_tasks(redmine, project.id, tasks)
        
        print(f"\n✅ IMPORTAÇÃO CONCLUÍDA!")
        print(f"🌐 Acesse: {REDMINE_URL}/projects/{PROJECT_IDENTIFIER}")
        
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
