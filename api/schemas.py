from datetime import date
from typing import List, Optional
from pydantic import BaseModel


# Fornecedor

class FornecedorCreate(BaseModel):
    razao_social: str
    fantasia: Optional[str] = None
    cnpj: str

class FornecedorUpdate(BaseModel):
    razao_social: Optional[str] = None
    fantasia: Optional[str] = None
    cnpj: Optional[str] = None

class FornecedorOut(BaseModel):
    id: int
    razao_social: str
    fantasia: Optional[str]
    cnpj: str
    ativo: bool
    model_config = {"from_attributes": True}


# Cliente

class ClienteCreate(BaseModel):
    nome: str
    cpf_cnpj: str
    email: Optional[str] = None
    telefone: Optional[str] = None

class ClienteUpdate(BaseModel):
    nome: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    email: Optional[str] = None
    telefone: Optional[str] = None

class ClienteOut(BaseModel):
    id: int
    nome: str
    cpf_cnpj: str
    email: Optional[str]
    telefone: Optional[str]
    ativo: bool
    model_config = {"from_attributes": True}


# Faturado

class FaturadoCreate(BaseModel):
    nome_completo: str
    cpf: str

class FaturadoUpdate(BaseModel):
    nome_completo: Optional[str] = None
    cpf: Optional[str] = None

class FaturadoOut(BaseModel):
    id: int
    nome_completo: str
    cpf: str
    ativo: bool
    model_config = {"from_attributes": True}


# Tipo de Despesa

class TipoDespesaCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None

class TipoDespesaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None

class TipoDespesaOut(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    ativo: bool
    model_config = {"from_attributes": True}


# Tipo de Receita

class TipoReceitaCreate(BaseModel):
    nome: str
    descricao: Optional[str] = None

class TipoReceitaUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None

class TipoReceitaOut(BaseModel):
    id: int
    nome: str
    descricao: Optional[str]
    ativo: bool
    model_config = {"from_attributes": True}


# Contas a Pagar

class ParcelaPagarIn(BaseModel):
    numero: int = 1
    data_vencimento: date
    valor: float
    pago: bool = False

class ParcelaPagarOut(ParcelaPagarIn):
    id: int
    model_config = {"from_attributes": True}

class ContasPagarCreate(BaseModel):
    numero_nf: Optional[str] = None
    data_emissao: date
    descricao: Optional[str] = None
    valor_total: float
    fornecedor_id: int
    faturado_id: Optional[int] = None
    parcelas: List[ParcelaPagarIn]
    tipo_despesa_ids: List[int]

class ContasPagarUpdate(BaseModel):
    numero_nf: Optional[str] = None
    data_emissao: Optional[date] = None
    descricao: Optional[str] = None
    valor_total: Optional[float] = None
    fornecedor_id: Optional[int] = None
    faturado_id: Optional[int] = None
    parcelas: Optional[List[ParcelaPagarIn]] = None
    tipo_despesa_ids: Optional[List[int]] = None

class ContasPagarOut(BaseModel):
    id: int
    numero_nf: Optional[str]
    data_emissao: date
    descricao: Optional[str]
    valor_total: float
    fornecedor_id: int
    faturado_id: Optional[int]
    ativo: bool
    parcelas: List[ParcelaPagarOut] = []
    tipo_despesa_ids: List[int] = []
    model_config = {"from_attributes": True}


# Contas a Receber

class ParcelaReceberIn(BaseModel):
    numero: int = 1
    data_vencimento: date
    valor: float
    recebido: bool = False

class ParcelaReceberOut(ParcelaReceberIn):
    id: int
    model_config = {"from_attributes": True}

class ContasReceberCreate(BaseModel):
    descricao: Optional[str] = None
    data_emissao: date
    valor_total: float
    cliente_id: int
    parcelas: List[ParcelaReceberIn]
    tipo_receita_ids: List[int]

class ContasReceberUpdate(BaseModel):
    descricao: Optional[str] = None
    data_emissao: Optional[date] = None
    valor_total: Optional[float] = None
    cliente_id: Optional[int] = None
    parcelas: Optional[List[ParcelaReceberIn]] = None
    tipo_receita_ids: Optional[List[int]] = None

class ContasReceberOut(BaseModel):
    id: int
    descricao: Optional[str]
    data_emissao: date
    valor_total: float
    cliente_id: int
    ativo: bool
    parcelas: List[ParcelaReceberOut] = []
    tipo_receita_ids: List[int] = []
    model_config = {"from_attributes": True}
