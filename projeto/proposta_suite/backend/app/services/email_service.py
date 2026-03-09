from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def enviar_email_simulacao(email_destino: str, nome: str, simulacao: dict, correlation_id: str):
    logger.info(
        "Enviando e-mail de simulação",
        extra={"correlation_id": correlation_id},
    )
    logger.info(
        f"E-mail para {email_destino} enviado com sucesso (simulado).",
        extra={"correlation_id": correlation_id},
    )
