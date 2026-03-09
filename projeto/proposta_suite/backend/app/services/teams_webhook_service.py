"""
Serviço de Notificações Microsoft Teams para Proposta Suite
Envia mensagens formatadas via webhook usando Adaptive Cards
"""

import os
import json
import logging
import httpx
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum

# Configuração de Logging
logger = logging.getLogger(__name__)


class AlertLevel(str, Enum):
    """Níveis de alerta para notificações"""
    CRITICAL = "critical"  # Vermelho - Requer ação imediata
    WARNING = "warning"    # Laranja - Atenção necessária
    INFO = "info"          # Azul - Informativo
    SUCCESS = "success"    # Verde - Sucesso/Confirmação


class TeamsWebhookService:
    """
    Serviço para envio de notificações ao Microsoft Teams via Webhook
    Integrado com Proposta Suite para alertas de propostas, simulações e eventos do sistema
    """
    
    def __init__(self):
        self.webhook_url = os.getenv(
            "TEAMS_WEBHOOK_URL",
            "https://default6d09c88c0617490c8329305e577684.bc.environment.api.powerplatform.com:443/powerautomate/automations/direct/workflows/0e49b601eca8492ea8b3c03d825c1ad9/triggers/manual/paths/invoke/?api-version=1"
        )
        self.enabled = os.getenv("TEAMS_NOTIFICATIONS_ENABLED", "true").lower() == "true"
        self.timeout = int(os.getenv("TEAMS_TIMEOUT_SECONDS", "10"))
        
        if self.enabled and not self.webhook_url:
            logger.warning("⚠️ Teams notifications habilitadas mas TEAMS_WEBHOOK_URL não configurada!")
    
    def _get_theme_color(self, level: AlertLevel) -> str:
        """Retorna cor do tema baseado no nível de alerta"""
        colors = {
            AlertLevel.CRITICAL: "FF0000",  # Vermelho
            AlertLevel.WARNING: "FFA500",   # Laranja
            AlertLevel.INFO: "0078D4",      # Azul Microsoft
            AlertLevel.SUCCESS: "00B050"    # Verde
        }
        return colors.get(level, "0078D4")
    
    def _get_icon(self, level: AlertLevel) -> str:
        """Retorna emoji/ícone baseado no nível"""
        icons = {
            AlertLevel.CRITICAL: "🚨",
            AlertLevel.WARNING: "⚠️",
            AlertLevel.INFO: "ℹ️",
            AlertLevel.SUCCESS: "✅"
        }
        return icons.get(level, "ℹ️")
    
    def build_adaptive_card(
        self,
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
            facts: Lista de fatos (chave/valor) para exibir
            actions: Lista de ações (botões) personalizados
            
        Returns:
            Dicionário com o payload do Adaptive Card
        """
        icon = self._get_icon(level)
        color = self._get_theme_color(level)
        
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
        
        # Ações padrão
        default_actions = actions or [
            {
                "type": "Action.OpenUrl",
                "title": "Ver Dashboard",
                "url": "https://portal.exemplo.com/dashboard"
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
    
    async def send_adaptive_card(self, card_payload: Dict[str, Any]) -> bool:
        """
        Envia o Adaptive Card para o Teams via Webhook de forma assíncrona.
        
        Args:
            card_payload: Payload do Adaptive Card
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        if not self.enabled:
            logger.info("📴 Teams notifications desabilitadas")
            return False
        
        if not self.webhook_url:
            logger.error("❌ TEAMS_WEBHOOK_URL não configurada")
            return False
        
        headers = {"Content-Type": "application/json"}
        
        try:
            logger.info("📤 Enviando Adaptive Card para o Teams...")
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.webhook_url,
                    headers=headers,
                    json=card_payload,
                    timeout=self.timeout
                )
                response.raise_for_status()
            
            logger.info(f"✅ Adaptive Card enviado com sucesso (status {response.status_code})")
            return True
            
        except httpx.HTTPStatusError as err:
            logger.error(f"❌ Erro HTTP ao enviar Adaptive Card: {err.response.status_code} - {err}")
            return False
        except httpx.RequestError as err:
            logger.error(f"❌ Erro de conexão ao enviar Adaptive Card: {err}")
            return False
        except Exception as err:
            logger.error(f"❌ Erro inesperado ao enviar Adaptive Card: {err}")
            return False
    
    async def send_notification(
        self,
        title: str,
        message: str,
        level: AlertLevel = AlertLevel.INFO,
        facts: Optional[List[Dict[str, str]]] = None,
        actions: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Método simplificado para enviar notificação ao Teams.
        
        Args:
            title: Título da notificação
            message: Mensagem principal
            level: Nível de alerta
            facts: Lista de fatos adicionais
            actions: Lista de ações personalizadas
            
        Returns:
            True se enviado com sucesso, False caso contrário
        """
        card = self.build_adaptive_card(
            title=title,
            message=message,
            level=level,
            facts=facts,
            actions=actions
        )
        return await self.send_adaptive_card(card)
    
    # Métodos específicos para Proposta Suite
    
    async def send_proposta_criada_alert(
        self,
        proposta_id: int,
        cliente_nome: str,
        valor: float,
        usuario: str
    ) -> bool:
        """Envia alerta de nova proposta criada"""
        return await self.send_notification(
            title="📋 Nova Proposta Criada",
            message=f"Uma nova proposta foi registrada no sistema.",
            level=AlertLevel.SUCCESS,
            facts=[
                {"title": "ID Proposta", "value": str(proposta_id)},
                {"title": "Cliente", "value": cliente_nome},
                {"title": "Valor", "value": f"R$ {valor:,.2f}"},
                {"title": "Criado por", "value": usuario}
            ]
        )
    
    async def send_proposta_aprovada_alert(
        self,
        proposta_id: int,
        cliente_nome: str,
        valor: float,
        aprovador: str
    ) -> bool:
        """Envia alerta de proposta aprovada"""
        return await self.send_notification(
            title="✅ Proposta Aprovada",
            message=f"A proposta #{proposta_id} foi aprovada!",
            level=AlertLevel.SUCCESS,
            facts=[
                {"title": "ID Proposta", "value": str(proposta_id)},
                {"title": "Cliente", "value": cliente_nome},
                {"title": "Valor", "value": f"R$ {valor:,.2f}"},
                {"title": "Aprovado por", "value": aprovador}
            ]
        )
    
    async def send_proposta_rejeitada_alert(
        self,
        proposta_id: int,
        cliente_nome: str,
        motivo: str,
        usuario: str
    ) -> bool:
        """Envia alerta de proposta rejeitada"""
        return await self.send_notification(
            title="❌ Proposta Rejeitada",
            message=f"A proposta #{proposta_id} foi rejeitada.",
            level=AlertLevel.WARNING,
            facts=[
                {"title": "ID Proposta", "value": str(proposta_id)},
                {"title": "Cliente", "value": cliente_nome},
                {"title": "Motivo", "value": motivo},
                {"title": "Rejeitado por", "value": usuario}
            ]
        )
    
    async def send_simulacao_alert(
        self,
        proposta_id: int,
        cenarios_gerados: int,
        melhor_taxa: float
    ) -> bool:
        """Envia alerta de simulação concluída"""
        return await self.send_notification(
            title="🔬 Simulação Concluída",
            message=f"Simulação da proposta #{proposta_id} processada com sucesso.",
            level=AlertLevel.INFO,
            facts=[
                {"title": "Proposta", "value": str(proposta_id)},
                {"title": "Cenários Gerados", "value": str(cenarios_gerados)},
                {"title": "Melhor Taxa", "value": f"{melhor_taxa}%"}
            ]
        )
    
    async def send_error_alert(
        self,
        error_type: str,
        error_message: str,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Envia alerta de erro do sistema"""
        facts = [
            {"title": "Tipo de Erro", "value": error_type},
            {"title": "Mensagem", "value": error_message[:100]}
        ]
        
        if context:
            for key, value in context.items():
                facts.append({"title": key, "value": str(value)})
        
        return await self.send_notification(
            title="🚨 Erro no Sistema",
            message="Um erro foi detectado no Proposta Suite.",
            level=AlertLevel.CRITICAL,
            facts=facts
        )


# Instância global do serviço
teams_service = TeamsWebhookService()


# Funções auxiliares para facilitar o uso
async def send_custom_message(
    title: str,
    message: str,
    level: AlertLevel = AlertLevel.INFO,
    facts: Optional[List[Dict[str, str]]] = None
) -> bool:
    """Função auxiliar para enviar mensagem customizada"""
    return await teams_service.send_notification(title, message, level, facts)
