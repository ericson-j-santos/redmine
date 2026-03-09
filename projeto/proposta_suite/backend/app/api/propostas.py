from fastapi import APIRouter, BackgroundTasks, Depends, Request, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import uuid4

from app.db.session import get_db
from app.models.proposta import Proposta
from app.models.simulacao import Simulacao
from app.schemas.proposta_schema import (
    PropostaCreate,
    PropostaResponse,
    PropostaStatusResponse,
    SimulacaoResumo,
    PropostaDetalheResponse,
)
from app.services.proposta_service import criar_proposta, processar_proposta
from app.core.logging_config import get_logger
from app.core.rbac import assert_role

router = APIRouter(prefix="/propostas", tags=["propostas"])
logger = get_logger(__name__)


@router.post("/", response_model=PropostaResponse, status_code=201)
async def criar_e_disparar_proposta(
    payload: PropostaCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(lambda x_user_role=Depends(assert_role(["analista", "gestor", "admin"])): x_user_role),
):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())

    proposta = await criar_proposta(payload, db, correlation_id)

    background_tasks.add_task(processar_proposta, proposta.id_proposta, db, correlation_id)

    return PropostaResponse(
        id_proposta=proposta.id_proposta,
        status_inicial=proposta.status,
        correlation_id=correlation_id,
        mensagem="Proposta recebida para processamento.",
    )


@router.get("/{id_proposta}/status", response_model=PropostaStatusResponse)
async def obter_status_proposta(
    id_proposta: str,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _role: str = Depends(lambda x_user_role=Depends(assert_role(["analista", "gestor", "admin"])): x_user_role),
):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())

    stmt = select(Proposta).where(Proposta.id_proposta == id_proposta)
    result = await db.execute(stmt)
    proposta = result.scalar_one_or_none()
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    stmt_sim = select(Simulacao).where(Simulacao.id_proposta == id_proposta)
    result_sim = await db.execute(stmt_sim)
    simulacao = result_sim.scalar_one_or_none()

    resumo = None
    if simulacao:
        resumo = SimulacaoResumo(
            valor_financiado=simulacao.valor_financiado,
            taxa_juros_aa=simulacao.taxa_juros_aa,
            parcela_aproximada=simulacao.parcela_aproximada,
            prazo_meses=simulacao.prazo_meses,
            cet_aa=simulacao.cet_aa,
            comparativo_portabilidade=simulacao.comparativo_portabilidade,
        )

    return PropostaStatusResponse(
        id_proposta=proposta.id_proposta,
        status=proposta.status,
        resumo_simulacao=resumo,
        ultimo_update=proposta.atualizado_em.isoformat() if proposta.atualizado_em else None,
        correlation_id=correlation_id,
    )


@router.get("/{id_proposta}/detalhes", response_model=PropostaDetalheResponse)
async def obter_detalhes_proposta(
    id_proposta: str,
    db: AsyncSession = Depends(get_db),
    request: Request = None,
    _role: str = Depends(lambda x_user_role=Depends(assert_role(["gestor", "admin"])): x_user_role),
):
    correlation_id = request.headers.get("x-correlation-id") or str(uuid4())

    stmt = select(Proposta).where(Proposta.id_proposta == id_proposta)
    result = await db.execute(stmt)
    proposta = result.scalar_one_or_none()
    if not proposta:
        raise HTTPException(status_code=404, detail="Proposta não encontrada")

    stmt_sim = select(Simulacao).where(Simulacao.id_proposta == id_proposta)
    result_sim = await db.execute(stmt_sim)
    simulacao = result_sim.scalar_one_or_none()

    resumo = None
    if simulacao:
        resumo = SimulacaoResumo(
            valor_financiado=simulacao.valor_financiado,
            taxa_juros_aa=simulacao.taxa_juros_aa,
            parcela_aproximada=simulacao.parcela_aproximada,
            prazo_meses=simulacao.prazo_meses,
            cet_aa=simulacao.cet_aa,
            comparativo_portabilidade=simulacao.comparativo_portabilidade,
        )

    return PropostaDetalheResponse(
        id_proposta=proposta.id_proposta,
        cpf=proposta.cpf,
        nome_cliente=proposta.nome_cliente,
        email=proposta.email,
        telefone=proposta.telefone,
        valor_solicitado=proposta.valor_solicitado,
        prazo_meses=proposta.prazo_meses,
        tipo_imovel=proposta.tipo_imovel,
        tipo_operacao=proposta.tipo_operacao,
        canal_origem=proposta.canal_origem,
        status=proposta.status,
        resumo_simulacao=resumo,
        correlation_id=correlation_id,
    )
