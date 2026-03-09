#!/usr/bin/env python3
"""
Script para gerar dashboards HTML customizados com análises avançadas
Cria visualizações interativas com gráficos e métricas
"""

import json
from datetime import datetime, timedelta
from collections import defaultdict
from redminelib import Redmine

REDMINE_URL = 'http://localhost:3001'
API_KEY = '5ebbcb862df64b85779d7d8e2c99cb9ae7a6d3dc'
PROJECT_IDENTIFIER = 'proposta-suite'


def calcular_metricas_avancadas(issues):
    """Calcula métricas avançadas do projeto"""
    
    total = len(issues)
    fechadas = sum(1 for i in issues if i.status.name == 'Fechada')
    em_andamento = sum(1 for i in issues if i.status.name == 'Em andamento')
    novas = sum(1 for i in issues if i.status.name == 'Nova')
    
    # Taxa de conclusão
    taxa_conclusao = (fechadas / total * 100) if total > 0 else 0
    
    # Distribuição por fase
    fases = defaultdict(lambda: {'total': 0, 'fechadas': 0, 'em_andamento': 0, 'novas': 0})
    for issue in issues:
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
    
    # Velocidade (tasks por dia)
    if len(issues) > 0:
        primeira = min(issues, key=lambda x: x.created_on)
        ultima = max(issues, key=lambda x: x.updated_on)
        dias = max((ultima.updated_on - primeira.created_on).days, 1)
        velocidade = fechadas / dias
    else:
        dias = 1
        velocidade = 0
    
    # Lead time médio (tempo de criação até fechamento)
    issues_fechadas = [i for i in issues if i.status.name == 'Fechada']
    if issues_fechadas:
        lead_times = []
        for issue in issues_fechadas:
            if hasattr(issue, 'updated_on'):
                lead_time = (issue.updated_on - issue.created_on).total_seconds() / 3600  # horas
                lead_times.append(lead_time)
        lead_time_medio = sum(lead_times) / len(lead_times) if lead_times else 0
    else:
        lead_time_medio = 0
    
    return {
        'total': total,
        'fechadas': fechadas,
        'em_andamento': em_andamento,
        'novas': novas,
        'taxa_conclusao': taxa_conclusao,
        'fases': dict(fases),
        'velocidade': velocidade,
        'dias_projeto': dias,
        'lead_time_medio': lead_time_medio
    }


def gerar_html_dashboard(metricas):
    """Gera HTML do dashboard com Chart.js"""
    
    # Preparar dados para gráficos
    fases_labels = list(metricas['fases'].keys())
    fases_total = [metricas['fases'][f]['total'] for f in fases_labels]
    fases_fechadas = [metricas['fases'][f]['fechadas'] for f in fases_labels]
    fases_andamento = [metricas['fases'][f]['em_andamento'] for f in fases_labels]
    fases_novas = [metricas['fases'][f]['novas'] for f in fases_labels]
    
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - Proposta Suite</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        h1 {{
            color: white;
            text-align: center;
            margin-bottom: 10px;
            font-size: 2.5em;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .subtitle {{
            color: rgba(255,255,255,0.9);
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.1em;
        }}
        
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .metric-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        
        .metric-card:hover {{
            transform: translateY(-5px);
        }}
        
        .metric-label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
        }}
        
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #333;
        }}
        
        .metric-unit {{
            font-size: 0.5em;
            color: #999;
            font-weight: normal;
        }}
        
        .metric-change {{
            margin-top: 10px;
            font-size: 0.85em;
            color: #28a745;
        }}
        
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(500px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .chart-card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        
        .chart-title {{
            font-size: 1.3em;
            margin-bottom: 20px;
            color: #333;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }}
        
        .chart-container {{
            position: relative;
            height: 300px;
        }}
        
        .footer {{
            text-align: center;
            color: rgba(255,255,255,0.8);
            margin-top: 30px;
            font-size: 0.9em;
        }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.75em;
            font-weight: bold;
            margin-top: 5px;
        }}
        
        .status-success {{
            background: #d4edda;
            color: #155724;
        }}
        
        .status-warning {{
            background: #fff3cd;
            color: #856404;
        }}
        
        .status-info {{
            background: #d1ecf1;
            color: #0c5460;
        }}
        
        @media (max-width: 768px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
            
            h1 {{
                font-size: 1.8em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Dashboard - Proposta Suite</h1>
        <p class="subtitle">Atualizado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</p>
        
        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-label">Total de Tarefas</div>
                <div class="metric-value">{metricas['total']}</div>
                <div class="status-badge status-info">4 Fases</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Taxa de Conclusão</div>
                <div class="metric-value">{metricas['taxa_conclusao']:.1f}<span class="metric-unit">%</span></div>
                <div class="status-badge {'status-success' if metricas['taxa_conclusao'] >= 90 else 'status-warning'}">
                    {metricas['fechadas']}/{metricas['total']} concluídas
                </div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Em Andamento</div>
                <div class="metric-value">{metricas['em_andamento']}</div>
                <div class="metric-change">⚡ Ativas agora</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Velocidade</div>
                <div class="metric-value">{metricas['velocidade']:.1f}<span class="metric-unit">tasks/dia</span></div>
                <div class="metric-change">📅 {metricas['dias_projeto']} dias de projeto</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Lead Time Médio</div>
                <div class="metric-value">{metricas['lead_time_medio']:.0f}<span class="metric-unit">horas</span></div>
                <div class="metric-change">⏱️ Tempo médio de resolução</div>
            </div>
            
            <div class="metric-card">
                <div class="metric-label">Tarefas Novas</div>
                <div class="metric-value">{metricas['novas']}</div>
                <div class="metric-change">📝 Aguardando início</div>
            </div>
        </div>
        
        <div class="charts-grid">
            <div class="chart-card">
                <div class="chart-title">📊 Distribuição por Status</div>
                <div class="chart-container">
                    <canvas id="statusChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">🎯 Progresso por Fase</div>
                <div class="chart-container">
                    <canvas id="faseChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">📈 Status Detalhado por Fase</div>
                <div class="chart-container">
                    <canvas id="faseStackedChart"></canvas>
                </div>
            </div>
            
            <div class="chart-card">
                <div class="chart-title">⚡ Métricas de Desempenho</div>
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🔗 <a href="{REDMINE_URL}/projects/{PROJECT_IDENTIFIER}" style="color: white;">Acessar Projeto no Redmine</a></p>
            <p>Dashboard gerado automaticamente • Proposta Suite MVP</p>
        </div>
    </div>
    
    <script>
        // Configuração global dos gráficos
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        Chart.defaults.color = '#666';
        
        // Gráfico de Pizza - Distribuição por Status
        const statusCtx = document.getElementById('statusChart').getContext('2d');
        new Chart(statusCtx, {{
            type: 'doughnut',
            data: {{
                labels: ['Fechadas', 'Em Andamento', 'Novas'],
                datasets: [{{
                    data: [{metricas['fechadas']}, {metricas['em_andamento']}, {metricas['novas']}],
                    backgroundColor: ['#28a745', '#ffc107', '#6c757d'],
                    borderWidth: 0
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom',
                        labels: {{
                            padding: 15,
                            font: {{
                                size: 12
                            }}
                        }}
                    }}
                }}
            }}
        }});
        
        // Gráfico de Barras - Progresso por Fase
        const faseCtx = document.getElementById('faseChart').getContext('2d');
        new Chart(faseCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(fases_labels)},
                datasets: [{{
                    label: 'Total',
                    data: {json.dumps(fases_total)},
                    backgroundColor: '#667eea',
                    borderRadius: 5
                }}, {{
                    label: 'Concluídas',
                    data: {json.dumps(fases_fechadas)},
                    backgroundColor: '#28a745',
                    borderRadius: 5
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            stepSize: 1
                        }}
                    }}
                }}
            }}
        }});
        
        // Gráfico Stacked - Status por Fase
        const faseStackedCtx = document.getElementById('faseStackedChart').getContext('2d');
        new Chart(faseStackedCtx, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(fases_labels)},
                datasets: [{{
                    label: 'Fechadas',
                    data: {json.dumps(fases_fechadas)},
                    backgroundColor: '#28a745'
                }}, {{
                    label: 'Em Andamento',
                    data: {json.dumps(fases_andamento)},
                    backgroundColor: '#ffc107'
                }}, {{
                    label: 'Novas',
                    data: {json.dumps(fases_novas)},
                    backgroundColor: '#6c757d'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }},
                scales: {{
                    x: {{
                        stacked: true
                    }},
                    y: {{
                        stacked: true,
                        beginAtZero: true
                    }}
                }}
            }}
        }});
        
        // Gráfico de Radar - Métricas de Desempenho
        const performanceCtx = document.getElementById('performanceChart').getContext('2d');
        new Chart(performanceCtx, {{
            type: 'radar',
            data: {{
                labels: ['Taxa Conclusão', 'Velocidade', 'Qualidade', 'Eficiência', 'Cobertura'],
                datasets: [{{
                    label: 'Projeto Atual',
                    data: [
                        {metricas['taxa_conclusao']},
                        {min(metricas['velocidade'] * 10, 100)},
                        {100 - (metricas['em_andamento'] / metricas['total'] * 100) if metricas['total'] > 0 else 0},
                        {100 if metricas['lead_time_medio'] < 24 else 50},
                        {(metricas['total'] / 50) * 100}
                    ],
                    backgroundColor: 'rgba(102, 126, 234, 0.2)',
                    borderColor: '#667eea',
                    borderWidth: 2,
                    pointBackgroundColor: '#667eea'
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    legend: {{
                        position: 'bottom'
                    }}
                }},
                scales: {{
                    r: {{
                        beginAtZero: true,
                        max: 100
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""
    
    return html


def main():
    print("="*70)
    print("📊 GERADOR DE DASHBOARD CUSTOMIZADO")
    print("="*70)
    
    redmine = Redmine(REDMINE_URL, key=API_KEY)
    issues = list(redmine.issue.filter(
        project_id=PROJECT_IDENTIFIER,
        status_id='*',
        limit=1000
    ))
    
    print(f"\n📊 Analisando {len(issues)} issues...")
    
    # Calcular métricas
    metricas = calcular_metricas_avancadas(issues)
    
    print("\n📈 Métricas Calculadas:")
    print(f"   • Taxa de Conclusão: {metricas['taxa_conclusao']:.1f}%")
    print(f"   • Velocidade: {metricas['velocidade']:.2f} tasks/dia")
    print(f"   • Lead Time Médio: {metricas['lead_time_medio']:.1f} horas")
    
    # Gerar HTML
    html = gerar_html_dashboard(metricas)
    
    # Salvar arquivo
    filename = f'dashboard_proposta_suite_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Dashboard gerado: {filename}")
    print(f"\n🌐 Abra o arquivo no navegador para visualizar")
    print(f"   file:///home/erics/TEMP/CODIGOS/redmine-6.0.5/{filename}")
    print()


if __name__ == '__main__':
    main()
