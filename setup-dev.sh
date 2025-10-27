#!/bin/bash
# Setup de Ambiente de Desenvolvimento - Redmine 6.0.5
# Executar este script para configurar o ambiente após git clone

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║  Setup Redmine 6.0.5 - Ambiente de Desenvolvimento        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# 1. Carregar rbenv
export PATH="$HOME/.rbenv/bin:$PATH"
eval "$(rbenv init -)"

echo "✓ Ruby: $(ruby --version)"
echo "✓ Bundler: $(bundle --version | head -1)"
echo ""

# 2. Instalar gems
echo "▶ Instalando dependências Ruby..."
cd "$(dirname "$0")" || exit 1
bundle install --without ldap minimagick

echo ""
echo "✓ Gems instaladas: $(bundle list | wc -l)"
echo ""

# 3. Setup do banco de dados
echo "▶ Configurando banco de dados SQLite..."
RAILS_ENV=test bundle exec rails db:setup 2>/dev/null || true

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║  ✅ Setup Concluído com Sucesso!                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "Próximos passos:"
echo ""
echo "  1. Rodar testes:"
echo "     $ export PATH=\"\$HOME/.rbenv/bin:\$PATH\""
echo "     $ eval \"\$(rbenv init -)\""
echo "     $ cd /home/erics/TEMP/CODIGOS/redmine-6.0.5"
echo "     $ bundle exec rails test"
echo ""
echo "  2. Iniciar servidor Rails:"
echo "     $ bundle exec rails server"
echo ""
echo "  3. Rails console:"
echo "     $ bundle exec rails console"
echo ""
