from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from database import get_db
import models, schemas

router = APIRouter(prefix="/contas-receber", tags=["Contas a Receber"])


def _validar_parcelas(parcelas: list) -> None:
    """Datas de vencimento devem ser distintas entre parcelas."""
    datas = [p.data_vencimento if hasattr(p, "data_vencimento") else p["data_vencimento"] for p in parcelas]
    if len(datas) != len(set(datas)):
        raise HTTPException(400, "Cada parcela deve ter uma data de vencimento distinta.")


def _to_out(obj: models.ContasReceber) -> schemas.ContasReceberOut:
    return schemas.ContasReceberOut(
        id=obj.id,
        descricao=obj.descricao,
        data_emissao=obj.data_emissao,
        valor_total=obj.valor_total,
        cliente_id=obj.cliente_id,
        ativo=obj.ativo,
        parcelas=[schemas.ParcelaReceberOut.model_validate(p) for p in obj.parcelas],
        tipo_receita_ids=[c.tipo_receita_id for c in obj.classificacoes],
    )


def _load(id: int, db: Session) -> models.ContasReceber:
    obj = (
        db.query(models.ContasReceber)
        .options(
            joinedload(models.ContasReceber.parcelas),
            joinedload(models.ContasReceber.classificacoes),
        )
        .filter(models.ContasReceber.id == id)
        .first()
    )
    if not obj:
        raise HTTPException(404, "Conta a receber não encontrada.")
    return obj


@router.get("", response_model=List[schemas.ContasReceberOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = (
        db.query(models.ContasReceber)
        .options(
            joinedload(models.ContasReceber.parcelas),
            joinedload(models.ContasReceber.classificacoes),
        )
    )
    if ativo is not None:
        q = q.filter(models.ContasReceber.ativo == ativo)
    return [_to_out(o) for o in q.order_by(models.ContasReceber.data_emissao.desc()).all()]


@router.post("", response_model=schemas.ContasReceberOut, status_code=201)
def criar(body: schemas.ContasReceberCreate, db: Session = Depends(get_db)):
    if not db.get(models.Cliente, body.cliente_id):
        raise HTTPException(400, "Cliente não encontrado.")
    if not body.parcelas:
        raise HTTPException(400, "Informe ao menos uma parcela.")
    if not body.tipo_receita_ids:
        raise HTTPException(400, "Informe ao menos um tipo de receita.")
    _validar_parcelas(body.parcelas)

    obj = models.ContasReceber(
        descricao=body.descricao,
        data_emissao=body.data_emissao,
        valor_total=body.valor_total,
        cliente_id=body.cliente_id,
    )
    db.add(obj)
    db.flush()

    for p in body.parcelas:
        db.add(models.ParcelaReceber(conta_id=obj.id, **p.model_dump()))
    for tid in body.tipo_receita_ids:
        if not db.get(models.TipoReceita, tid):
            raise HTTPException(400, f"Tipo de receita {tid} não encontrado.")
        db.add(models.ClassificacaoReceber(conta_id=obj.id, tipo_receita_id=tid))

    db.commit()
    return _to_out(_load(obj.id, db))


@router.get("/{id}", response_model=schemas.ContasReceberOut)
def obter(id: int, db: Session = Depends(get_db)):
    return _to_out(_load(id, db))


@router.put("/{id}", response_model=schemas.ContasReceberOut)
def atualizar(id: int, body: schemas.ContasReceberUpdate, db: Session = Depends(get_db)):
    obj = _load(id, db)
    data = body.model_dump(exclude_unset=True)

    parcelas = data.pop("parcelas", None)
    tipo_ids = data.pop("tipo_receita_ids", None)

    for k, v in data.items():
        setattr(obj, k, v)

    if parcelas is not None:
        _validar_parcelas(parcelas)
        for p in obj.parcelas:
            db.delete(p)
        db.flush()
        for p in parcelas:
            db.add(models.ParcelaReceber(conta_id=obj.id, **p))

    if tipo_ids is not None:
        for c in obj.classificacoes:
            db.delete(c)
        db.flush()
        for tid in tipo_ids:
            db.add(models.ClassificacaoReceber(conta_id=obj.id, tipo_receita_id=tid))

    db.commit()
    return _to_out(_load(obj.id, db))


@router.patch("/{id}/inativar", response_model=schemas.ContasReceberOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = _load(id, db)
    obj.ativo = False
    db.commit()
    return _to_out(_load(id, db))


@router.patch("/{id}/reativar", response_model=schemas.ContasReceberOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = _load(id, db)
    obj.ativo = True
    db.commit()
    return _to_out(_load(id, db))
