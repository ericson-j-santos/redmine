from app.core.logging_config import get_logger
from app.services.http_resiliente import chamar_com_retry, cb_site_a

logger = get_logger(__name__)


async def _chamada_real_site_a(cpf: str):
    # Aqui entraria HTTPX/Requests em produção.
    return {
        "cpf": cpf,
        "contrato_atual": "123456",
        "parcela_atual": 3550.90,
        "saldo_devedor": 340000.00,
    }


async def consultar_site_a(cpf: str, correlation_id: str):
    return await chamar_com_retry(
        _chamada_real_site_a,
        cpf=cpf,
        correlation_id=correlation_id,
        circuito=cb_site_a,
        descricao="Site A",
    )
