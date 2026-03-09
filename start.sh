#!/bin/bash

# Script para iniciar o servidor Redmine
# Criado em: 27/11/2025

echo "🚀 Iniciando servidor Redmine..."
echo ""

# Verifica se já existe um processo na porta 3001
if lsof -Pi :3001 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Servidor já está rodando na porta 3001"
    echo ""
    PID=$(lsof -Pi :3001 -sTCP:LISTEN -t)
    echo "PID: $PID"
    echo ""
    read -p "Deseja reiniciar? (s/N): " resposta
    if [[ "$resposta" =~ ^[Ss]$ ]]; then
        echo "Parando servidor anterior..."
        kill $PID
        sleep 2
    else
        echo "Mantendo servidor atual."
        exit 0
    fi
fi

# Inicia o servidor
cd "$(dirname "$0")"
echo "Iniciando Puma na porta 3001..."
echo ""
bundle exec rails server -p 3001

# Se o servidor for interrompido
echo ""
echo "Servidor encerrado."
