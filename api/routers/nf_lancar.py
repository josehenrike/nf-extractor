from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
import models

router = APIRouter(prefix="/nf", tags=["Lançamento NF"])


# Schemas de entrada 

class _ParcelaIn(BaseModel):
    data_vencimento: str
    valor: Optional[float] = None


class _FornecedorIn(BaseModel):
    razao_social: str
    fantasia: Optional[str] = None
    cnpj: str


class _FaturadoIn(BaseModel):
    nome_completo: str
    cpf: str


class LancarNfInput(BaseModel):
    fornecedor: _FornecedorIn
    faturado: _FaturadoIn
    numero_nota_fiscal: str
    data_emissao: str
    descricao_produtos: str
    quantidade_parcelas: int
    parcelas: List[_ParcelaIn]
    valor_total: float
    classificacoes_despesa: List[str]


# Schemas de saída 

class FornecedorInfo(BaseModel):
    razao_social: str
    cnpj: str
    existe: bool
    id: Optional[int] = None


class FaturadoInfo(BaseModel):
    nome_completo: str
    cpf: str
    existe: bool
    id: Optional[int] = None


class ClassificacaoInfo(BaseModel):
    nome: str
    existe: bool
    id: Optional[int] = None


class AnaliseResult(BaseModel):
    fornecedor: FornecedorInfo
    faturado: FaturadoInfo
    classificacoes: List[ClassificacaoInfo]


class LancarResult(BaseModel):
    ok: bool
    conta_pagar_id: int


# Endpoints 

@router.post("/analisar", response_model=AnaliseResult)
def analisar(body: LancarNfInput, db: Session = Depends(get_db)):
    forn = db.query(models.Fornecedor).filter(models.Fornecedor.cnpj == body.fornecedor.cnpj).first()
    fat  = db.query(models.Faturado).filter(models.Faturado.cpf == body.faturado.cpf).first()

    classs: List[ClassificacaoInfo] = []
    for nome in body.classificacoes_despesa:
        td = db.query(models.TipoDespesa).filter(models.TipoDespesa.nome == nome).first()
        classs.append(ClassificacaoInfo(nome=nome, existe=td is not None, id=td.id if td else None))

    return AnaliseResult(
        fornecedor=FornecedorInfo(
            razao_social=body.fornecedor.razao_social,
            cnpj=body.fornecedor.cnpj,
            existe=forn is not None,
            id=forn.id if forn else None,
        ),
        faturado=FaturadoInfo(
            nome_completo=body.faturado.nome_completo,
            cpf=body.faturado.cpf,
            existe=fat is not None,
            id=fat.id if fat else None,
        ),
        classificacoes=classs,
    )


@router.post("/lancar", response_model=LancarResult)
def lancar(body: LancarNfInput, db: Session = Depends(get_db)):
    # Fornecedor: busca ou cria
    forn = db.query(models.Fornecedor).filter(models.Fornecedor.cnpj == body.fornecedor.cnpj).first()
    if not forn:
        forn = models.Fornecedor(
            razao_social=body.fornecedor.razao_social,
            fantasia=body.fornecedor.fantasia or None,
            cnpj=body.fornecedor.cnpj,
        )
        db.add(forn)
        db.flush()

    # Faturado: busca ou cria
    fat = db.query(models.Faturado).filter(models.Faturado.cpf == body.faturado.cpf).first()
    if not fat:
        fat = models.Faturado(
            nome_completo=body.faturado.nome_completo,
            cpf=body.faturado.cpf,
        )
        db.add(fat)
        db.flush()

    # Tipos de Despesa: busca ou cria cada um
    tipo_ids: List[int] = []
    for nome in body.classificacoes_despesa:
        td = db.query(models.TipoDespesa).filter(models.TipoDespesa.nome == nome).first()
        if not td:
            td = models.TipoDespesa(nome=nome)
            db.add(td)
            db.flush()
        tipo_ids.append(td.id)

    # Conta a Pagar
    emissao = date.fromisoformat(body.data_emissao)
    conta = models.ContasPagar(
        numero_nf=body.numero_nota_fiscal or None,
        data_emissao=emissao,
        descricao=body.descricao_produtos or None,
        valor_total=body.valor_total,
        fornecedor_id=forn.id,
        faturado_id=fat.id,
    )
    db.add(conta)
    db.flush()

    # Parcelas
    n = len(body.parcelas)
    for i, p in enumerate(body.parcelas, 1):
        valor_parcela = p.valor if p.valor is not None else round(body.valor_total / n, 2)
        parcela = models.ParcelaPagar(
            conta_id=conta.id,
            numero=i,
            data_vencimento=date.fromisoformat(p.data_vencimento),
            valor=valor_parcela,
        )
        db.add(parcela)

    # Classificações
    for tid in tipo_ids:
        cl = models.ClassificacaoPagar(conta_id=conta.id, tipo_despesa_id=tid)
        db.add(cl)

    db.commit()
    return LancarResult(ok=True, conta_pagar_id=conta.id)
