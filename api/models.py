from sqlalchemy import Boolean, Column, Date, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from database import Base


# Cadastros

class Fornecedor(Base):
    __tablename__ = "fornecedores"
    id            = Column(Integer, primary_key=True, index=True)
    razao_social  = Column(String(200), nullable=False)
    fantasia      = Column(String(200))
    cnpj          = Column(String(20), unique=True, nullable=False, index=True)
    ativo         = Column(Boolean, default=True, nullable=False)

    contas_pagar  = relationship("ContasPagar", back_populates="fornecedor")


class Cliente(Base):
    __tablename__ = "clientes"
    id        = Column(Integer, primary_key=True, index=True)
    nome      = Column(String(200), nullable=False)
    cpf_cnpj  = Column(String(20), unique=True, nullable=False, index=True)
    email     = Column(String(200))
    telefone  = Column(String(30))
    ativo     = Column(Boolean, default=True, nullable=False)

    contas_receber = relationship("ContasReceber", back_populates="cliente")


class Faturado(Base):
    __tablename__ = "faturados"
    id            = Column(Integer, primary_key=True, index=True)
    nome_completo = Column(String(200), nullable=False)
    cpf           = Column(String(20), unique=True, nullable=False, index=True)
    ativo         = Column(Boolean, default=True, nullable=False)

    contas_pagar  = relationship("ContasPagar", back_populates="faturado")


class TipoDespesa(Base):
    __tablename__ = "tipos_despesa"
    id        = Column(Integer, primary_key=True, index=True)
    nome      = Column(String(100), unique=True, nullable=False)
    descricao = Column(String(300))
    ativo     = Column(Boolean, default=True, nullable=False)

    classificacoes = relationship("ClassificacaoPagar", back_populates="tipo_despesa")


class TipoReceita(Base):
    __tablename__ = "tipos_receita"
    id        = Column(Integer, primary_key=True, index=True)
    nome      = Column(String(100), unique=True, nullable=False)
    descricao = Column(String(300))
    ativo     = Column(Boolean, default=True, nullable=False)

    classificacoes = relationship("ClassificacaoReceber", back_populates="tipo_receita")


# Contas a Pagar

class ContasPagar(Base):
    __tablename__  = "contas_pagar"
    id             = Column(Integer, primary_key=True, index=True)
    numero_nf      = Column(String(50))
    data_emissao   = Column(Date, nullable=False)
    descricao      = Column(Text)
    valor_total    = Column(Float, nullable=False)
    fornecedor_id  = Column(Integer, ForeignKey("fornecedores.id"), nullable=False)
    faturado_id    = Column(Integer, ForeignKey("faturados.id"), nullable=True)
    ativo          = Column(Boolean, default=True, nullable=False)

    fornecedor      = relationship("Fornecedor", back_populates="contas_pagar")
    faturado        = relationship("Faturado", back_populates="contas_pagar")
    parcelas        = relationship("ParcelaPagar",       back_populates="conta", cascade="all, delete-orphan")
    classificacoes  = relationship("ClassificacaoPagar", back_populates="conta", cascade="all, delete-orphan")


class ParcelaPagar(Base):
    __tablename__    = "parcelas_pagar"
    id               = Column(Integer, primary_key=True, index=True)
    conta_id         = Column(Integer, ForeignKey("contas_pagar.id"), nullable=False)
    numero           = Column(Integer, nullable=False, default=1)
    data_vencimento  = Column(Date, nullable=False)
    valor            = Column(Float, nullable=False)
    pago             = Column(Boolean, default=False, nullable=False)

    conta = relationship("ContasPagar", back_populates="parcelas")


class ClassificacaoPagar(Base):
    __tablename__    = "classificacoes_pagar"
    id               = Column(Integer, primary_key=True, index=True)
    conta_id         = Column(Integer, ForeignKey("contas_pagar.id"), nullable=False)
    tipo_despesa_id  = Column(Integer, ForeignKey("tipos_despesa.id"), nullable=False)

    conta        = relationship("ContasPagar",  back_populates="classificacoes")
    tipo_despesa = relationship("TipoDespesa",  back_populates="classificacoes")


# Contas a Receber

class ContasReceber(Base):
    __tablename__ = "contas_receber"
    id            = Column(Integer, primary_key=True, index=True)
    descricao     = Column(Text)
    data_emissao  = Column(Date, nullable=False)
    valor_total   = Column(Float, nullable=False)
    cliente_id    = Column(Integer, ForeignKey("clientes.id"), nullable=False)
    ativo         = Column(Boolean, default=True, nullable=False)

    cliente        = relationship("Cliente",              back_populates="contas_receber")
    parcelas       = relationship("ParcelaReceber",       back_populates="conta", cascade="all, delete-orphan")
    classificacoes = relationship("ClassificacaoReceber", back_populates="conta", cascade="all, delete-orphan")


class ParcelaReceber(Base):
    __tablename__   = "parcelas_receber"
    id              = Column(Integer, primary_key=True, index=True)
    conta_id        = Column(Integer, ForeignKey("contas_receber.id"), nullable=False)
    numero          = Column(Integer, nullable=False, default=1)
    data_vencimento = Column(Date, nullable=False)
    valor           = Column(Float, nullable=False)
    recebido        = Column(Boolean, default=False, nullable=False)

    conta = relationship("ContasReceber", back_populates="parcelas")


class ClassificacaoReceber(Base):
    __tablename__   = "classificacoes_receber"
    id              = Column(Integer, primary_key=True, index=True)
    conta_id        = Column(Integer, ForeignKey("contas_receber.id"), nullable=False)
    tipo_receita_id = Column(Integer, ForeignKey("tipos_receita.id"), nullable=False)

    conta        = relationship("ContasReceber", back_populates="classificacoes")
    tipo_receita = relationship("TipoReceita",   back_populates="classificacoes")
