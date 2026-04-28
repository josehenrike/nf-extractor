from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/tipos-despesa", tags=["Tipos de Despesa"])


@router.get("", response_model=List[schemas.TipoDespesaOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.TipoDespesa)
    if ativo is not None:
        q = q.filter(models.TipoDespesa.ativo == ativo)
    return q.order_by(models.TipoDespesa.nome).all()


@router.post("", response_model=schemas.TipoDespesaOut, status_code=201)
def criar(body: schemas.TipoDespesaCreate, db: Session = Depends(get_db)):
    if db.query(models.TipoDespesa).filter(models.TipoDespesa.nome == body.nome).first():
        raise HTTPException(400, "Tipo de despesa já cadastrado.")
    obj = models.TipoDespesa(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.get("/{id}", response_model=schemas.TipoDespesaOut)
def obter(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoDespesa, id)
    if not obj:
        raise HTTPException(404, "Tipo de despesa não encontrado.")
    return obj


@router.put("/{id}", response_model=schemas.TipoDespesaOut)
def atualizar(id: int, body: schemas.TipoDespesaUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.TipoDespesa, id)
    if not obj:
        raise HTTPException(404, "Tipo de despesa não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/inativar", response_model=schemas.TipoDespesaOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoDespesa, id)
    if not obj:
        raise HTTPException(404, "Tipo de despesa não encontrado.")
    obj.ativo = False
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/reativar", response_model=schemas.TipoDespesaOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoDespesa, id)
    if not obj:
        raise HTTPException(404, "Tipo de despesa não encontrado.")
    obj.ativo = True
    db.commit(); db.refresh(obj)
    return obj
