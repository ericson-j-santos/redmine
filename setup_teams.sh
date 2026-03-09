#!/bin/bash
# Script de setup para integração Teams Webhook

echo "╔══════════════════════════════════════════════════════╗"
echo "║   🚀 Setup - Integração Microsoft Teams Webhook     ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# Verificar se está em venv
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Não está em um ambiente virtual!"
    echo ""
    echo "Opções:"
    echo "  1) Criar e ativar venv:"
    echo "     python3 -m venv .venv"
    echo "     source .venv/bin/activate"
    echo ""
    echo "  2) Usar venv existente do Redmine:"
    if [ -d ".venv-redmine" ]; then
        echo "     source .venv-redmine/bin/activate"
    fi
    echo ""
    read -p "Deseja continuar mesmo assim? (s/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Ss]$ ]]; then
        exit 1
    fi
fi

# Instalar dependências
echo "📦 Instalando dependências..."
pip install -r teams_requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependências instaladas com sucesso!"
else
    echo "❌ Erro ao instalar dependências"
    exit 1
fi

# Verificar variáveis de ambiente
echo ""
echo "⚙️  Verificando configuração..."

if [ -z "$TEAMS_WEBHOOK_URL" ]; then
    echo "⚠️  TEAMS_WEBHOOK_URL não está configurada!"
    echo ""
    echo "Configure com:"
    echo "  export TEAMS_WEBHOOK_URL='https://sua-url-webhook...'"
    echo ""
    echo "Ou crie um arquivo .env com:"
    echo "  TEAMS_WEBHOOK_URL=https://sua-url-webhook..."
else
    echo "✅ TEAMS_WEBHOOK_URL configurada"
fi

# Testar importação
echo ""
echo "🧪 Testando módulo..."
python3 -c "
import sys
sys.path.insert(0, '.')
try:
    from teams_notification import send_notification, AlertLevel
    print('✅ Módulo teams_notification importado com sucesso!')
    print('✅ Funções disponíveis:')
    print('   - send_notification()')
    print('   - send_issue_created_alert()')
    print('   - send_issue_updated_alert()')
    print('   - send_error_alert()')
except Exception as e:
    print(f'❌ Erro ao importar: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo ""
    echo "╔══════════════════════════════════════════════════════╗"
    echo "║           ✅ Setup concluído com sucesso!           ║"
    echo "╚══════════════════════════════════════════════════════╝"
    echo ""
    echo "📝 Próximos passos:"
    echo "  1. Configure TEAMS_WEBHOOK_URL (se ainda não fez)"
    echo "  2. Execute exemplo: python3 teams_notification.py"
    echo "  3. Leia documentação: cat ../TEAMS_WEBHOOK_INTEGRATION.md"
else
    echo "❌ Falha no setup"
    exit 1
fi
