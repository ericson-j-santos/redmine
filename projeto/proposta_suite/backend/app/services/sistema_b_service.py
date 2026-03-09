from app.core.logging_config import get_logger
from app.services.http_resiliente import chamar_com_retry, cb_sistema_b

logger = get_logger(__name__)


async def _chamada_real_sistema_b(tipo_operacao: str):
    # Mock de fonte de taxas
    return {
        "taxa_juros_aa": 9.2,
        "taxa_minima": 8.9,
        "taxa_maxima": 9.8,
    }


async def consultar_sistema_b(tipo_operacao: str, correlation_id: str):
    return await chamar_com_retry(
        _chamada_real_sistema_b,
        tipo_operacao=tipo_operacao,
        correlation_id=correlation_id,
        circuito=cb_sistema_b,
        descricao="Sistema B",
    )
