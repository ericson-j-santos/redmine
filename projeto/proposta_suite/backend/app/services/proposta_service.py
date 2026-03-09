from uuid import uuid4
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.proposta import Proposta
from app.models.simulacao import Simulacao
from app.schemas.proposta_schema import PropostaCreate
from app.services.site_a_service import consultar_site_a
from app.services.sistema_b_service import consultar_sistema_b
from app.services.simulacao_service import calcular_simulacao
from app.services.email_service import enviar_email_simulacao
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def criar_proposta(payload: PropostaCreate, db: AsyncSession, correlation_id: str) -> Proposta:
    proposta = Proposta(
        cpf=payload.cpf,
        nome_cliente=payload.nome_cliente,
        email=payload.email,
        telefone=payload.telefone,
        valor_solicitado=payload.valor_solicitado,
        prazo_meses=payload.prazo_meses,
        tipo_imovel=payload.tipo_imovel,
        tipo_operacao=payload.tipo_operacao,
        canal_origem=payload.canal_origem,
        aceite_lgpd=payload.aceite_lgpd,
        correlation_id=correlation_id,
    )
    db.add(proposta)
    await db.commit()
    await db.refresh(proposta)
    logger.info(
        "Proposta criada",
        extra={"correlation_id": correlation_id},
    )
    return proposta


async def processar_proposta(id_proposta: str, db: AsyncSession, correlation_id: str):
    logger.info(
        f"Iniciando processamento da proposta {id_proposta}",
        extra={"correlation_id": correlation_id},
    )

    stmt = select(Proposta).where(Proposta.id_proposta == id_proposta)
    result = await db.execute(stmt)
    proposta = result.scalar_one()

    proposta.status = "PROCESSANDO"
    await db.commit()
    await db.refresh(proposta)

    dados_site_a = await consultar_site_a(proposta.cpf, correlation_id)
    dados_sistema_b = await consultar_sistema_b(proposta.tipo_operacao, correlation_id)

    dados_simulacao = await calcular_simulacao(
        dados_site_a,
        dados_sistema_b,
        proposta.valor_solicitado,
        proposta.prazo_meses,
        correlation_id,
    )

    sim_id = str(uuid4())
    simulacao = Simulacao(
        id_simulacao=sim_id,
        id_proposta=proposta.id_proposta,
        **dados_simulacao,
    )
    db.add(simulacao)

    proposta.status = "SIMULACAO_ENVIADA"
    proposta.atualizado_em = datetime.utcnow()
    await db.commit()

    await enviar_email_simulacao(
        email_destino=proposta.email,
        nome=proposta.nome_cliente,
        simulacao=dados_simulacao,
        correlation_id=correlation_id,
    )

    logger.info(
        f"Processamento concluído para proposta {id_proposta}",
        extra={"correlation_id": correlation_id},
    )
