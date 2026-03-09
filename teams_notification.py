#!/usr/bin/env python3
"""
Módulo de Notificações Microsoft Teams para Redmine
Envia alertas e notificações via webhook usando Adaptive Cards
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

try:
    import httpx
except ImportError:
    print("❌ Módulo 'httpx' não encontrado!")
    print("📦 Instale com: pip install httpx")
    print("   ou em venv: python -m venv .venv && source .venv/bin/activate && pip install httpx")
    import sys
    sys.exit(1)

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Níveis de alerta para notificações"""
    CRITICAL = "critical"  # Vermelho - Requer ação imediata
    WARNING = "warning"    # Laranja - Atenção necessária
    INFO = "info"          # Azul - Informativo
    SUCCESS = "success"    # Verde - Sucesso/Confirmação


def get_theme_color(level: AlertLevel) -> str:
    """Retorna cor do tema baseado no nível de alerta"""
    colors = {
        AlertLevel.CRITICAL: "FF0000",  # Vermelho
        AlertLevel.WARNING: "FFA500",   # Laranja
        AlertLevel.INFO: "0078D4",      # Azul Microsoft
        AlertLevel.SUCCESS: "00B050"    # Verde
    }
    return colors.get(level, "0078D4")


def get_icon(level: AlertLevel) -> str:
    """Retorna emoji/ícone baseado no nível"""
    icons = {
        AlertLevel.CRITICAL: "🚨",
        AlertLevel.WARNING: "⚠️",
        AlertLevel.INFO: "ℹ️",
        AlertLevel.SUCCESS: "✅"
    }
    return icons.get(level, "ℹ️")


def build_adaptive_card(
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    facts: Optional[List[Dict[str, str]]] = None,
    actions: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Monta o payload do Adaptive Card em formato JSON.
    
    Args:
        title: Título da notificação
        message: Mensagem principal
        level: Nível de alerta
        facts: Lista de fatos (title/value) para exibir
        actions: Lista de ações (botões) personalizados
        
    Returns:
        Dicionário com o payload do Adaptive Card
    """
    icon = get_icon(level)
    
    # Corpo do card
    body = [
        {
            "type": "TextBlock",
            "size": "Large",
            "weight": "Bolder",
            "text": f"{icon} {title}",
            "color": "Accent" if level == AlertLevel.INFO else "Attention"
        },
        {
            "type": "TextBlock",
            "text": message,
            "wrap": True,
            "spacing": "Medium"
        }
    ]
    
    # Adicionar facts se fornecidos
    if facts:
        fact_set = {
            "type": "FactSet",
            "facts": [{"title": f["title"], "value": f["value"]} for f in facts],
            "spacing": "Medium"
        }
        body.append(fact_set)
    
    # Timestamp
    body.append({
        "type": "TextBlock",
        "text": f"⏰ {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
        "size": "Small",
        "isSubtle": True,
        "spacing": "Medium"
    })
    
    # Ações padrão ou personalizadas
    default_actions = actions or [
        {
            "type": "Action.OpenUrl",
            "title": "Ver Redmine",
            "url": os.getenv("REDMINE_URL", "http://localhost:3000")
        }
    ]
    
    return {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "msteams": {
                        "width": "Full"
                    },
                    "body": body,
                    "actions": default_actions
                }
            }
        ]
    }


async def send_adaptive_card(webhook_url: str, card_payload: Dict[str, Any], timeout: int = 10) -> bool:
    """
    Envia o Adaptive Card para o Teams via Webhook de forma assíncrona.
    
    Args:
        webhook_url: URL do webhook do Teams
        card_payload: Payload do Adaptive Card
        timeout: Timeout da requisição em segundos
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    headers = {"Content-Type": "application/json"}
    
    try:
        logger.info("📤 Enviando Adaptive Card para o Teams...")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                webhook_url,
                headers=headers,
                json=card_payload,
                timeout=timeout
            )
            response.raise_for_status()
        
        logger.info(f"✅ Adaptive Card enviado com sucesso (status {response.status_code})")
        return True
        
    except httpx.HTTPStatusError as err:
        logger.error(f"❌ Erro HTTP: {err.response.status_code} - {err}")
        return False
    except httpx.RequestError as err:
        logger.error(f"❌ Erro de conexão: {err}")
        return False
    except Exception as err:
        logger.error(f"❌ Erro inesperado: {err}")
        return False


async def send_notification(
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    facts: Optional[List[Dict[str, str]]] = None,
    actions: Optional[List[Dict[str, Any]]] = None,
    webhook_url: Optional[str] = None
) -> bool:
    """
    Método simplificado para enviar notificação ao Teams.
    
    Args:
        title: Título da notificação
        message: Mensagem principal
        level: Nível de alerta
        facts: Lista de fatos adicionais
        actions: Lista de ações personalizadas
        webhook_url: URL do webhook (usa variável de ambiente se não fornecida)
        
    Returns:
        True se enviado com sucesso, False caso contrário
    """
    url = webhook_url or os.getenv(
        "TEAMS_WEBHOOK_URL",
        "https://default6d09c88c0617490c8329305e577684.bc.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/0e49b601eca8492ea8b3c03d825c1ad9/triggers/manual/paths/invoke/?api-version=1"
    )
    
    if not url:
        logger.error("❌ TEAMS_WEBHOOK_URL não configurada")
        return False
    
    card = build_adaptive_card(title, message, level, facts, actions)
    return await send_adaptive_card(url, card)


# ========== Funções Específicas para Redmine ==========

async def send_issue_created_alert(issue_id: int, subject: str, author: str, project: str) -> bool:
    """Envia alerta de nova issue criada"""
    return await send_notification(
        title="📝 Nova Issue Criada",
        message=f"Uma nova issue foi registrada no Redmine.",
        level=AlertLevel.INFO,
        facts=[
            {"title": "Issue ID", "value": f"#{issue_id}"},
            {"title": "Assunto", "value": subject},
            {"title": "Projeto", "value": project},
            {"title": "Autor", "value": author}
        ]
    )


async def send_issue_updated_alert(issue_id: int, subject: str, status: str, updater: str) -> bool:
    """Envia alerta de issue atualizada"""
    return await send_notification(
        title="🔄 Issue Atualizada",
        message=f"A issue #{issue_id} foi modificada.",
        level=AlertLevel.INFO,
        facts=[
            {"title": "Issue ID", "value": f"#{issue_id}"},
            {"title": "Assunto", "value": subject},
            {"title": "Novo Status", "value": status},
            {"title": "Atualizado por", "value": updater}
        ]
    )


async def send_issue_closed_alert(issue_id: int, subject: str, closer: str) -> bool:
    """Envia alerta de issue fechada"""
    return await send_notification(
        title="✅ Issue Fechada",
        message=f"A issue #{issue_id} foi concluída.",
        level=AlertLevel.SUCCESS,
        facts=[
            {"title": "Issue ID", "value": f"#{issue_id}"},
            {"title": "Assunto", "value": subject},
            {"title": "Fechado por", "value": closer}
        ]
    )


async def send_project_created_alert(project_name: str, identifier: str, author: str) -> bool:
    """Envia alerta de novo projeto criado"""
    return await send_notification(
        title="🚀 Novo Projeto Criado",
        message=f"Um novo projeto foi adicionado ao Redmine.",
        level=AlertLevel.SUCCESS,
        facts=[
            {"title": "Nome", "value": project_name},
            {"title": "Identificador", "value": identifier},
            {"title": "Criado por", "value": author}
        ]
    )


async def send_error_alert(error_type: str, error_message: str, context: Optional[Dict[str, Any]] = None) -> bool:
    """Envia alerta de erro do sistema"""
    facts = [
        {"title": "Tipo de Erro", "value": error_type},
        {"title": "Mensagem", "value": error_message[:100]}
    ]
    
    if context:
        for key, value in context.items():
            facts.append({"title": key, "value": str(value)})
    
    return await send_notification(
        title="🚨 Erro no Redmine",
        message="Um erro foi detectado no sistema.",
        level=AlertLevel.CRITICAL,
        facts=facts
    )


# ========== Função Principal de Exemplo ==========

async def main():
    """Exemplo de uso do módulo"""
    
    # Exemplo 1: Notificação customizada
    print("📨 Enviando notificação customizada...")
    await send_notification(
        title="🎉 Sistema Redmine Atualizado",
        message="O Redmine foi atualizado com sucesso para a versão 6.0.5!",
        level=AlertLevel.SUCCESS,
        facts=[
            {"title": "Versão", "value": "6.0.5"},
            {"title": "Data", "value": datetime.now().strftime("%d/%m/%Y")},
            {"title": "Status", "value": "✅ Operacional"}
        ]
    )
    
    await asyncio.sleep(2)
    
    # Exemplo 2: Alerta de nova issue
    print("\n📝 Enviando alerta de nova issue...")
    await send_issue_created_alert(
        issue_id=1234,
        subject="Implementar integração com Teams",
        author="João Silva",
        project="Infraestrutura"
    )
    
    await asyncio.sleep(2)
    
    # Exemplo 3: Alerta de erro
    print("\n🚨 Enviando alerta de erro...")
    await send_error_alert(
        error_type="DatabaseError",
        error_message="Timeout ao conectar com banco de dados",
        context={
            "Database": "redmine_production",
            "Host": "db.exemplo.com",
            "Tentativas": "3"
        }
    )
    
    print("\n✅ Exemplos concluídos!")


if __name__ == "__main__":
    asyncio.run(main())
