#!/bin/bash
# Script para organizar arquivos excessivos no projeto Redmine
# Criado em: 2025-11-27

PROJETO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJETO_DIR"

echo "=================================================="
echo "  ORGANIZADOR DE ARQUIVOS - REDMINE PROJECT"
echo "=================================================="
echo ""
echo "Diretório do projeto: $PROJETO_DIR"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Criar diretório para arquivos arquivados
ARCHIVE_DIR="$PROJETO_DIR/_archived_docs"
mkdir -p "$ARCHIVE_DIR"

echo -e "${BLUE}[INFO]${NC} Criando estrutura de diretórios..."

# Criar subdiretórios no arquivo
mkdir -p "$ARCHIVE_DIR/test_reports"
mkdir -p "$ARCHIVE_DIR/setup_docs"
mkdir -p "$ARCHIVE_DIR/status_reports"

echo ""
echo -e "${YELLOW}[ANÁLISE]${NC} Arquivos encontrados para organização:"
echo ""

# Lista de arquivos de relatórios de teste
TEST_DOCS=(
    "FINAL_TEST_SUMMARY.md"
    "INDICE_TESTES.md"
    "RELATORIO_CONSOLIDACAO.md"
    "RELATORIO_FINAL_TESTES.md"
    "RELATORIO_TESTES.md"
    "RESUMO_FINAL_TESTES.md"
    "RESUMO_TESTES.txt"
    "TEST_EXECUTION_SUMMARY.txt"
    "TEST_RESULTS.md"
    "TESTING_GUIDE.md"
    "TESTING_STRATEGY.md"
)

# Lista de arquivos de setup e status
SETUP_STATUS_DOCS=(
    "CHECKLIST.md"
    "FINAL_SUMMARY.md"
    "NEXT_STEPS.md"
    "REPOSITORY_STATUS.md"
    "RESUMO_FINAL.txt"
    "RUBY_LSP_TROUBLESHOOTING.md"
    "SETUP_COMPLETE.md"
    "STATUS.md"
    "RELATORIO_REPOSITORIOS_ONLINE.md"
)

# Contador
moved_count=0
skipped_count=0

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}MOVENDO RELATÓRIOS DE TESTE${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

for file in "${TEST_DOCS[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} Movendo: $file → _archived_docs/test_reports/"
        mv "$file" "$ARCHIVE_DIR/test_reports/"
        ((moved_count++))
    else
        echo -e "${YELLOW}⊘${NC} Não encontrado: $file"
        ((skipped_count++))
    fi
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}MOVENDO DOCUMENTOS DE SETUP E STATUS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

for file in "${SETUP_STATUS_DOCS[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} Movendo: $file → _archived_docs/setup_docs/"
        mv "$file" "$ARCHIVE_DIR/setup_docs/"
        ((moved_count++))
    else
        echo -e "${YELLOW}⊘${NC} Não encontrado: $file"
        ((skipped_count++))
    fi
done

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}LIMPANDO DIRETÓRIOS TEMPORÁRIOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Limpar coverage se existir
if [ -d "coverage" ]; then
    echo -e "${GREEN}✓${NC} Movendo: coverage/ → _archived_docs/"
    mv coverage "$ARCHIVE_DIR/"
    ((moved_count++))
fi

# Verificar diretório tmp
if [ -d "tmp" ]; then
    tmp_size=$(du -sh tmp 2>/dev/null | cut -f1)
    echo -e "${YELLOW}ℹ${NC} Diretório tmp/ encontrado (tamanho: $tmp_size)"
    echo -e "   ${YELLOW}→${NC} Mantido (usado pelo Rails em desenvolvimento)"
fi

# Verificar diretório log
if [ -d "log" ]; then
    log_count=$(find log -type f -name "*.log" 2>/dev/null | wc -l)
    if [ "$log_count" -gt 0 ]; then
        echo -e "${YELLOW}ℹ${NC} Encontrados $log_count arquivo(s) de log"
        echo -e "   ${YELLOW}→${NC} Para limpar logs, execute: rake log:clear"
    fi
fi

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}CRIANDO ARQUIVO README NO DIRETÓRIO DE ARQUIVOS${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

cat > "$ARCHIVE_DIR/README.md" << 'EOF'
# Documentação Arquivada

Este diretório contém documentação histórica e arquivos de desenvolvimento que não são mais necessários para o uso diário do projeto.

## Estrutura

- **test_reports/** - Relatórios de testes e estratégias de teste
- **setup_docs/** - Documentos de setup, checklists e status de desenvolvimento
- **coverage/** - Relatórios de cobertura de código (se existirem)

## Por que estes arquivos foram movidos?

Estes arquivos foram criados durante o desenvolvimento e testes do projeto, mas não são necessários para:
- Executar a aplicação
- Contribuir com código
- Entender a funcionalidade principal

## Documentação Principal

Para documentação ativa, consulte:
- `README.rdoc` - Documentação principal do Redmine
- `doc/` - Documentação oficial
- `CONTRIBUTING.md` - Guia de contribuição

## Recuperação

Se você precisar de qualquer arquivo movido para cá, eles estão organizados por categoria nos subdiretórios.

---
*Arquivado em: $(date +"%Y-%m-%d")*
EOF

echo -e "${GREEN}✓${NC} Criado: _archived_docs/README.md"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}RESUMO DA ORGANIZAÇÃO${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "📦 Arquivos movidos: $moved_count"
echo "⊘ Arquivos não encontrados: $skipped_count"
echo "📁 Destino: $ARCHIVE_DIR"
echo ""

# Listar estrutura final
echo -e "${BLUE}Estrutura do diretório de arquivos:${NC}"
tree -L 2 "$ARCHIVE_DIR" 2>/dev/null || find "$ARCHIVE_DIR" -maxdepth 2 -type f -o -type d

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ ORGANIZAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Próximos passos sugeridos:${NC}"
echo "  1. Revisar os arquivos em _archived_docs/"
echo "  2. Executar 'git status' para ver as mudanças"
echo "  3. Adicionar _archived_docs/ ao .gitignore se desejar"
echo "  4. Fazer commit das mudanças"
echo ""
