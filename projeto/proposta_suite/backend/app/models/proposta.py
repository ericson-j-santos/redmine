import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime
from app.db.base_class import Base


class Proposta(Base):
    __tablename__ = "propostas"

    id_proposta = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cpf = Column(String(11), nullable=False, index=True)
    nome_cliente = Column(String(150), nullable=False)
    email = Column(String(150), nullable=False)
    telefone = Column(String(20), nullable=True)
    valor_solicitado = Column(Float, nullable=False)
    prazo_meses = Column(Integer, nullable=False)
    tipo_imovel = Column(String(50), nullable=False)
    tipo_operacao = Column(String(50), nullable=False)
    canal_origem = Column(String(50), nullable=False, default="SITE")
    aceite_lgpd = Column(Boolean, nullable=False, default=False)
    status = Column(String(50), nullable=False, default="PENDENTE_PROCESSAMENTO")
    correlation_id = Column(String(50), nullable=False)
    criado_em = Column(DateTime, default=datetime.utcnow)
    atualizado_em = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
