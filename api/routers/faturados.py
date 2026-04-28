from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/faturados", tags=["Faturados"])


@router.get("", response_model=List[schemas.FaturadoOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.Faturado)
    if ativo is not None:
        q = q.filter(models.Faturado.ativo == ativo)
    return q.order_by(models.Faturado.nome_completo).all()


@router.post("", response_model=schemas.FaturadoOut, status_code=201)
def criar(body: schemas.FaturadoCreate, db: Session = Depends(get_db)):
    if db.query(models.Faturado).filter(models.Faturado.cpf == body.cpf).first():
        raise HTTPException(400, "CPF já cadastrado.")
    obj = models.Faturado(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.get("/{id}", response_model=schemas.FaturadoOut)
def obter(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Faturado, id)
    if not obj:
        raise HTTPException(404, "Faturado não encontrado.")
    return obj


@router.put("/{id}", response_model=schemas.FaturadoOut)
def atualizar(id: int, body: schemas.FaturadoUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Faturado, id)
    if not obj:
        raise HTTPException(404, "Faturado não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/inativar", response_model=schemas.FaturadoOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Faturado, id)
    if not obj:
        raise HTTPException(404, "Faturado não encontrado.")
    obj.ativo = False
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/reativar", response_model=schemas.FaturadoOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Faturado, id)
    if not obj:
        raise HTTPException(404, "Faturado não encontrado.")
    obj.ativo = True
    db.commit(); db.refresh(obj)
    return obj
