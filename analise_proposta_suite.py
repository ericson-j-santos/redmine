#!/usr/bin/env python3
"""
Script de Análise Completa do Projeto Proposta Suite no Redmine
Gera relatórios, métricas e insights sobre o projeto
"""

import csv
from datetime import datetime
from collections import defaultdict
from redminelib import Redmine


# ============================================================================
# CONFIGURAÇÕES
# ============================================================================

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_IDENTIFIER = 'proposta-suite'


# ============================================================================
# FUNÇÕES DE ANÁLISE
# ============================================================================

def conectar():
    """Conecta ao Redmine"""
    return Redmine(REDMINE_URL, key=API_KEY)


def analise_por_fase(issues):
    """Analisa issues agrupadas por fase"""
    print("\n" + "="*70)
    print("📊 ANÁLISE POR FASE")
    print("="*70)
    
    fases = defaultdict(lambda: {'total': 0, 'fechadas': 0, 'em_andamento': 0, 'novas': 0})
    
    for issue in issues:
        # Extrair fase da descrição
        fase = 'Não categorizada'
        if 'Fase:**' in issue.description:
            fase = issue.description.split('Fase:**')[1].split('\n')[0].strip()
        elif 'Fase:' in issue.description:
            fase = issue.description.split('Fase:')[1].split('\n')[0].strip()
        
        fases[fase]['total'] += 1
        
        if issue.status.name == 'Fechada':
            fases[fase]['fechadas'] += 1
        elif issue.status.name == 'Em andamento':
            fases[fase]['em_andamento'] += 1
        elif issue.status.name == 'Nova':
            fases[fase]['novas'] += 1
    
    for fase, stats in sorted(fases.items()):
        percentual = (stats['fechadas'] / stats['total'] * 100) if stats['total'] > 0 else 0
        print(f"\n🔹 {fase}")
        print(f"   Total: {stats['total']} tarefas")
        print(f"   ✅ Fechadas: {stats['fechadas']} ({percentual:.1f}%)")
        print(f"   🔄 Em andamento: {stats['em_andamento']}")
        print(f"   ⭕ Novas: {stats['novas']}")
        
        # Barra de progresso visual
        barra_completa = int(percentual / 5)  # 20 caracteres max
        barra = '█' * barra_completa + '░' * (20 - barra_completa)
        print(f"   Progresso: [{barra}] {percentual:.1f}%")


def analise_por_status(issues):
    """Analisa distribuição por status"""
    print("\n" + "="*70)
    print("📈 DISTRIBUIÇÃO POR STATUS")
    print("="*70)
    
    status_count = defaultdict(int)
    for issue in issues:
        status_count[issue.status.name] += 1
    
    total = len(issues)
    for status, count in sorted(status_count.items(), key=lambda x: x[1], reverse=True):
        percentual = (count / total * 100)
        barra = '█' * int(percentual / 5)
        print(f"   {status:20s}: {count:3d} ({percentual:5.1f}%) {barra}")


def analise_tracker(issues):
    """Analisa distribuição por tracker"""
    print("\n" + "="*70)
    print("🏷️  DISTRIBUIÇÃO POR TIPO (TRACKER)")
    print("="*70)
    
    tracker_count = defaultdict(int)
    for issue in issues:
        tracker_count[issue.tracker.name] += 1
    
    total = len(issues)
    for tracker, count in sorted(tracker_count.items(), key=lambda x: x[1], reverse=True):
        percentual = (count / total * 100)
        print(f"   {tracker:20s}: {count:3d} ({percentual:5.1f}%)")


def analise_timeline(issues):
    """Analisa linha do tempo das tarefas"""
    print("\n" + "="*70)
    print("⏰ TIMELINE DE CRIAÇÃO")
    print("="*70)
    
    issues_list = list(issues)
    if issues_list:
        primeira = min(issues_list, key=lambda x: x.created_on)
        ultima = max(issues_list, key=lambda x: x.created_on)
        
        print(f"\n   📅 Primeira tarefa criada: {primeira.created_on.strftime('%d/%m/%Y %H:%M')}")
        print(f"      #{primeira.id} - {primeira.subject}")
        print(f"\n   📅 Última tarefa criada: {ultima.created_on.strftime('%d/%m/%Y %H:%M')}")
        print(f"      #{ultima.id} - {ultima.subject}")
        
        if hasattr(primeira, 'updated_on') and hasattr(ultima, 'updated_on'):
            print(f"\n   📅 Última atualização: {ultima.updated_on.strftime('%d/%m/%Y %H:%M')}")


def listar_pendencias(issues):
    """Lista tarefas não concluídas"""
    print("\n" + "="*70)
    print("⚠️  TAREFAS PENDENTES (NÃO FECHADAS)")
    print("="*70)
    
    pendentes = [i for i in issues if i.status.name != 'Fechada']
    
    if not pendentes:
        print("\n   🎉 Parabéns! Todas as tarefas estão concluídas!")
    else:
        print(f"\n   Total de pendências: {len(pendentes)}\n")
        for issue in sorted(pendentes, key=lambda x: x.id):
            print(f"   #{issue.id:3d} [{issue.status.name:15s}] {issue.subject}")


def analise_completa(issues):
    """Análise estatística completa"""
    print("\n" + "="*70)
    print("📊 ESTATÍSTICAS GERAIS")
    print("="*70)
    
    total = len(issues)
    fechadas = sum(1 for i in issues if i.status.name == 'Fechada')
    em_andamento = sum(1 for i in issues if i.status.name == 'Em andamento')
    novas = sum(1 for i in issues if i.status.name == 'Nova')
    
    conclusao_geral = (fechadas / total * 100) if total > 0 else 0
    
    print(f"\n   📝 Total de Issues: {total}")
    print(f"   ✅ Concluídas: {fechadas} ({conclusao_geral:.1f}%)")
    print(f"   🔄 Em Andamento: {em_andamento}")
    print(f"   ⭕ Não Iniciadas: {novas}")
    print(f"\n   🎯 Taxa de Conclusão Geral: {conclusao_geral:.1f}%")
    
    # Velocidade (se houver datas de fechamento)
    issues_fechadas = [i for i in issues if i.status.name == 'Fechada' and hasattr(i, 'closed_on')]
    if issues_fechadas and len(issues_fechadas) > 1:
        primeira_fechada = min(issues_fechadas, key=lambda x: x.created_on)
        ultima_fechada = max(issues_fechadas, key=lambda x: getattr(x, 'updated_on', x.created_on))
        
        delta = ultima_fechada.updated_on - primeira_fechada.created_on
        dias = delta.days if delta.days > 0 else 1
        velocidade = len(issues_fechadas) / dias
        
        print(f"\n   ⚡ Velocidade Média: {velocidade:.2f} tarefas/dia")
        print(f"   📅 Período analisado: {dias} dias")


def exportar_relatorio_csv(issues):
    """Exporta relatório detalhado em CSV"""
    filename = f'relatorio_proposta_suite_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([
            'ID', 'Título', 'Status', 'Tracker', 'Criado Em', 
            'Atualizado Em', 'Fase', 'URL'
        ])
        
        for issue in sorted(issues, key=lambda x: x.id):
            fase = 'N/A'
            if 'Fase:**' in issue.description:
                fase = issue.description.split('Fase:**')[1].split('\n')[0].strip()
            elif 'Fase:' in issue.description:
                fase = issue.description.split('Fase:')[1].split('\n')[0].strip()
            
            writer.writerow([
                issue.id,
                issue.subject,
                issue.status.name,
                issue.tracker.name,
                issue.created_on.strftime('%d/%m/%Y %H:%M'),
                issue.updated_on.strftime('%d/%m/%Y %H:%M') if hasattr(issue, 'updated_on') else 'N/A',
                fase,
                f"{REDMINE_URL}/issues/{issue.id}"
            ])
    
    print(f"\n✅ Relatório CSV exportado: {filename}")


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("="*70)
    print("🎯 ANÁLISE COMPLETA - PROJETO PROPOSTA SUITE")
    print("="*70)
    
    redmine = conectar()
    project = redmine.project.get(PROJECT_IDENTIFIER)
    # Buscar TODAS as issues incluindo fechadas
    issues = list(redmine.issue.filter(
        project_id=PROJECT_IDENTIFIER, 
        status_id='*',  # * = todos os status (incluindo fechados)
        limit=1000
    ))
    
    print(f"\n📁 Projeto: {project.name}")
    print(f"🔗 URL: {REDMINE_URL}/projects/{PROJECT_IDENTIFIER}")
    print(f"📊 Total de Issues: {len(issues)}")
    
    # Executar todas as análises
    analise_completa(issues)
    analise_por_status(issues)
    analise_por_fase(issues)
    analise_tracker(issues)
    analise_timeline(issues)
    listar_pendencias(issues)
    
    # Exportar relatório
    print("\n" + "="*70)
    print("📄 EXPORTAÇÃO DE RELATÓRIO")
    print("="*70)
    exportar_relatorio_csv(issues)
    
    print("\n" + "="*70)
    print("✅ ANÁLISE CONCLUÍDA!")
    print("="*70)
    print(f"\n💡 PRÓXIMOS PASSOS RECOMENDADOS:")
    print(f"   1. Revisar tarefas pendentes (se houver)")
    print(f"   2. Atualizar status das tarefas em andamento")
    print(f"   3. Verificar métricas de velocidade para planejamento")
    print(f"   4. Usar o relatório CSV para apresentações")
    print(f"\n🌐 Acesse: {REDMINE_URL}/projects/{PROJECT_IDENTIFIER}/issues")
    print()


if __name__ == '__main__':
    main()
