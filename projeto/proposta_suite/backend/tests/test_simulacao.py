import pytest
from app.services.simulacao_service import calcular_simulacao


@pytest.mark.asyncio
async def test_calcular_simulacao_retorna_parcela_e_comparativo():
    dados_site_a = {
        "cpf": "12345678901",
        "contrato_atual": "123456",
        "parcela_atual": 3550.90,
        "saldo_devedor": 340000.00,
    }
    dados_sistema_b = {
        "taxa_juros_aa": 9.2,
        "taxa_minima": 8.9,
        "taxa_maxima": 9.8,
    }
    valor_solicitado = 350000.0
    prazo_meses = 360
    correlation_id = "teste-correlation"

    resultado = await calcular_simulacao(
        dados_site_a,
        dados_sistema_b,
        valor_solicitado,
        prazo_meses,
        correlation_id,
    )

    assert resultado["valor_financiado"] == valor_solicitado
    assert resultado["prazo_meses"] == prazo_meses
    assert "parcela_aproximada" in resultado
    assert resultado["comparativo_portabilidade"]["parcela_atual"] == 3550.90
    assert "economia_mensal" in resultado["comparativo_portabilidade"]
