#!/usr/bin/env python3
"""
Script para atualizar status das issues conforme CSV original
"""

import csv
from redminelib import Redmine

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_IDENTIFIER = 'proposta-suite'
CSV_FILE = 'projeto/proposta_suite_redmine_tasks.csv'

# Mapeamento de Status
STATUS_MAP = {
    'Closed': 5,        # Fechada
    'In Progress': 2,   # Em andamento
    'New': 1            # Nova
}

def main():
    print("="*70)
    print("🔄 ATUALIZAÇÃO DE STATUS DAS ISSUES")
    print("="*70)
    
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    project = redmine.project.get(PROJECT_IDENTIFIER)
    
    # Ler CSV
    with open(CSV_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        tasks = list(reader)
    
    print(f"\n📋 Lendo {len(tasks)} tarefas do CSV...")
    
    # Mapear issues por subject
    issues = {issue.subject: issue for issue in project.issues}
    
    atualizadas = 0
    erros = 0
    
    for i, task in enumerate(tasks, 1):
        subject = task['Subject']
        status_csv = task['Status']
        status_id = STATUS_MAP.get(status_csv, 1)
        
        if subject in issues:
            issue = issues[subject]
            try:
                # Atualizar apenas se diferente
                if issue.status.id != status_id:
                    redmine.issue.update(
                        issue.id,
                        status_id=status_id,
                        notes=f'Status atualizado automaticamente conforme CSV: {status_csv}'
                    )
                    print(f"  [{i}/{len(tasks)}] ✅ #{issue.id}: {subject[:50]}... → {status_csv}")
                    atualizadas += 1
                else:
                    print(f"  [{i}/{len(tasks)}] ⏭️  #{issue.id}: {subject[:50]}... (já está correto)")
            except Exception as e:
                print(f"  [{i}/{len(tasks)}] ❌ #{issue.id}: {subject[:50]}... → ERRO: {e}")
                erros += 1
        else:
            print(f"  [{i}/{len(tasks)}] ⚠️  Issue não encontrada: {subject}")
    
    print("\n" + "="*70)
    print("📊 RESUMO DA ATUALIZAÇÃO")
    print("="*70)
    print(f"   ✅ Atualizadas: {atualizadas}")
    print(f"   ⏭️  Já corretas: {len(tasks) - atualizadas - erros}")
    print(f"   ❌ Erros: {erros}")
    print(f"   📝 Total: {len(tasks)}")
    print()

if __name__ == '__main__':
    main()
