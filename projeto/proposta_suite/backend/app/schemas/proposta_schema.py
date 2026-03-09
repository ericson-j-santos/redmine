from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Dict, Any


class PropostaCreate(BaseModel):
    cpf: str = Field(..., min_length=11, max_length=11)
    nome_cliente: str
    email: EmailStr
    telefone: Optional[str] = None
    valor_solicitado: float
    prazo_meses: int
    tipo_imovel: str
    tipo_operacao: str
    canal_origem: str = "SITE"
    aceite_lgpd: bool


class PropostaResponse(BaseModel):
    id_proposta: str
    status_inicial: str
    correlation_id: str
    mensagem: str


class SimulacaoResumo(BaseModel):
    valor_financiado: float
    taxa_juros_aa: float
    parcela_aproximada: float
    prazo_meses: int
    cet_aa: Optional[float] = None
    comparativo_portabilidade: Optional[Dict[str, Any]] = None


class PropostaStatusResponse(BaseModel):
    id_proposta: str
    status: str
    resumo_simulacao: Optional[SimulacaoResumo] = None
    ultimo_update: Optional[str] = None
    correlation_id: str


class PropostaDetalheResponse(BaseModel):
    id_proposta: str
    cpf: str
    nome_cliente: str
    email: EmailStr
    telefone: Optional[str]
    valor_solicitado: float
    prazo_meses: int
    tipo_imovel: str
    tipo_operacao: str
    canal_origem: str
    status: str
    resumo_simulacao: Optional[SimulacaoResumo]
    correlation_id: str
