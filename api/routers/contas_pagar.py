from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models, schemas

router = APIRouter(prefix="/contas-pagar", tags=["Contas a Pagar"])


def _validar_parcelas(parcelas: list) -> None:
    """Datas de vencimento devem ser distintas entre parcelas."""
    datas = [p.data_vencimento if hasattr(p, "data_vencimento") else p["data_vencimento"] for p in parcelas]
    if len(datas) != len(set(datas)):
        raise HTTPException(400, "Cada parcela deve ter uma data de vencimento distinta.")


def _to_out(obj: models.ContasPagar) -> schemas.ContasPagarOut:
    return schemas.ContasPagarOut(
        id=obj.id,
        numero_nf=obj.numero_nf,
        data_emissao=obj.data_emissao,
        descricao=obj.descricao,
        valor_total=obj.valor_total,
        fornecedor_id=obj.fornecedor_id,
        faturado_id=obj.faturado_id,
        ativo=obj.ativo,
        parcelas=[schemas.ParcelaPagarOut.model_validate(p) for p in obj.parcelas],
        tipo_despesa_ids=[c.tipo_despesa_id for c in obj.classificacoes],
    )


def _load(id: int, db: Session) -> models.ContasPagar:
    obj = (
        db.query(models.ContasPagar)
        .options(
            joinedload(models.ContasPagar.parcelas),
            joinedload(models.ContasPagar.classificacoes),
        )
        .filter(models.ContasPagar.id == id)
        .first()
    )
    if not obj:
        raise HTTPException(404, "Conta a pagar não encontrada.")
    return obj


@router.get("", response_model=List[schemas.ContasPagarOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = (
        db.query(models.ContasPagar)
        .options(
            joinedload(models.ContasPagar.parcelas),
            joinedload(models.ContasPagar.classificacoes),
        )
    )
    if ativo is not None:
        q = q.filter(models.ContasPagar.ativo == ativo)
    return [_to_out(o) for o in q.order_by(models.ContasPagar.data_emissao.desc()).all()]


@router.post("", response_model=schemas.ContasPagarOut, status_code=201)
def criar(body: schemas.ContasPagarCreate, db: Session = Depends(get_db)):
    if not db.get(models.Fornecedor, body.fornecedor_id):
        raise HTTPException(400, "Fornecedor não encontrado.")
    if body.faturado_id and not db.get(models.Faturado, body.faturado_id):
        raise HTTPException(400, "Faturado não encontrado.")
    if not body.parcelas:
        raise HTTPException(400, "Informe ao menos uma parcela.")
    if not body.tipo_despesa_ids:
        raise HTTPException(400, "Informe ao menos um tipo de despesa.")
    _validar_parcelas(body.parcelas)

    obj = models.ContasPagar(
        numero_nf=body.numero_nf,
        data_emissao=body.data_emissao,
        descricao=body.descricao,
        valor_total=body.valor_total,
        fornecedor_id=body.fornecedor_id,
        faturado_id=body.faturado_id,
    )
    db.add(obj)
    db.flush()

    for p in body.parcelas:
        db.add(models.ParcelaPagar(conta_id=obj.id, **p.model_dump()))
    for tid in body.tipo_despesa_ids:
        if not db.get(models.TipoDespesa, tid):
            raise HTTPException(400, f"Tipo de despesa {tid} não encontrado.")
        db.add(models.ClassificacaoPagar(conta_id=obj.id, tipo_despesa_id=tid))

    db.commit()
    return _to_out(_load(obj.id, db))


@router.get("/{id}", response_model=schemas.ContasPagarOut)
def obter(id: int, db: Session = Depends(get_db)):
    return _to_out(_load(id, db))


@router.put("/{id}", response_model=schemas.ContasPagarOut)
def atualizar(id: int, body: schemas.ContasPagarUpdate, db: Session = Depends(get_db)):
    obj = _load(id, db)
    data = body.model_dump(exclude_unset=True)

    parcelas = data.pop("parcelas", None)
    tipo_ids = data.pop("tipo_despesa_ids", None)

    for k, v in data.items():
        setattr(obj, k, v)

    if parcelas is not None:
        _validar_parcelas(parcelas)
        for p in obj.parcelas:
            db.delete(p)
        db.flush()
        for p in parcelas:
            db.add(models.ParcelaPagar(conta_id=obj.id, **p))

    if tipo_ids is not None:
        for c in obj.classificacoes:
            db.delete(c)
        db.flush()
        for tid in tipo_ids:
            db.add(models.ClassificacaoPagar(conta_id=obj.id, tipo_despesa_id=tid))

    db.commit()
    return _to_out(_load(obj.id, db))


@router.patch("/{id}/inativar", response_model=schemas.ContasPagarOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = _load(id, db)
    obj.ativo = False
    db.commit()
    return _to_out(_load(id, db))


@router.patch("/{id}/reativar", response_model=schemas.ContasPagarOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = _load(id, db)
    obj.ativo = True
    db.commit()
    return _to_out(_load(id, db))
