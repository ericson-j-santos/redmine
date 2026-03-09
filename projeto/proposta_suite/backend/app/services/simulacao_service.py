from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def calcular_simulacao(
    dados_site_a: dict,
    dados_sistema_b: dict,
    valor_solicitado: float,
    prazo_meses: int,
    correlation_id: str,
):
    logger.info(
        "Executando motor de simulação",
        extra={"correlation_id": correlation_id},
    )
    taxa_aa = dados_sistema_b["taxa_juros_aa"]
    taxa_am = (1 + taxa_aa / 100) ** (1 / 12) - 1
    p = valor_solicitado
    i = taxa_am
    n = prazo_meses
    parcela = p * (i * (1 + i) ** n) / ((1 + i) ** n - 1)

    comparativo = {
        "parcela_atual": dados_site_a["parcela_atual"],
        "economia_mensal": round(dados_site_a["parcela_atual"] - parcela, 2),
    }

    return {
        "valor_financiado": valor_solicitado,
        "taxa_juros_aa": round(taxa_aa, 2),
        "parcela_aproximada": round(parcela, 2),
        "prazo_meses": prazo_meses,
        "cet_aa": round(taxa_aa + 0.9, 2),
        "comparativo_portabilidade": comparativo,
    }
