from sqlalchemy import Column, String, Float, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class Simulacao(Base):
    __tablename__ = "simulacoes"

    id_simulacao = Column(String, primary_key=True)
    id_proposta = Column(String, ForeignKey("propostas.id_proposta"), nullable=False)
    valor_financiado = Column(Float, nullable=False)
    taxa_juros_aa = Column(Float, nullable=False)
    parcela_aproximada = Column(Float, nullable=False)
    prazo_meses = Column(Integer, nullable=False)
    cet_aa = Column(Float, nullable=True)
    comparativo_portabilidade = Column(JSON, nullable=True)

    proposta = relationship("Proposta")
