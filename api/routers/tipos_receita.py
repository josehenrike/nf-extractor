from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/tipos-receita", tags=["Tipos de Receita"])


@router.get("", response_model=List[schemas.TipoReceitaOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.TipoReceita)
    if ativo is not None:
        q = q.filter(models.TipoReceita.ativo == ativo)
    return q.order_by(models.TipoReceita.nome).all()


@router.post("", response_model=schemas.TipoReceitaOut, status_code=201)
def criar(body: schemas.TipoReceitaCreate, db: Session = Depends(get_db)):
    if db.query(models.TipoReceita).filter(models.TipoReceita.nome == body.nome).first():
        raise HTTPException(400, "Tipo de receita já cadastrado.")
    obj = models.TipoReceita(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.get("/{id}", response_model=schemas.TipoReceitaOut)
def obter(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoReceita, id)
    if not obj:
        raise HTTPException(404, "Tipo de receita não encontrado.")
    return obj


@router.put("/{id}", response_model=schemas.TipoReceitaOut)
def atualizar(id: int, body: schemas.TipoReceitaUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.TipoReceita, id)
    if not obj:
        raise HTTPException(404, "Tipo de receita não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/inativar", response_model=schemas.TipoReceitaOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoReceita, id)
    if not obj:
        raise HTTPException(404, "Tipo de receita não encontrado.")
    obj.ativo = False
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/reativar", response_model=schemas.TipoReceitaOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.TipoReceita, id)
    if not obj:
        raise HTTPException(404, "Tipo de receita não encontrado.")
    obj.ativo = True
    db.commit(); db.refresh(obj)
    return obj
