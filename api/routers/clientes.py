from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/clientes", tags=["Clientes"])


@router.get("", response_model=List[schemas.ClienteOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.Cliente)
    if ativo is not None:
        q = q.filter(models.Cliente.ativo == ativo)
    return q.order_by(models.Cliente.nome).all()


@router.post("", response_model=schemas.ClienteOut, status_code=201)
def criar(body: schemas.ClienteCreate, db: Session = Depends(get_db)):
    if db.query(models.Cliente).filter(models.Cliente.cpf_cnpj == body.cpf_cnpj).first():
        raise HTTPException(400, "CPF/CNPJ já cadastrado.")
    obj = models.Cliente(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.get("/{id}", response_model=schemas.ClienteOut)
def obter(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Cliente, id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    return obj


@router.put("/{id}", response_model=schemas.ClienteOut)
def atualizar(id: int, body: schemas.ClienteUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Cliente, id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/inativar", response_model=schemas.ClienteOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Cliente, id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    obj.ativo = False
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/reativar", response_model=schemas.ClienteOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Cliente, id)
    if not obj:
        raise HTTPException(404, "Cliente não encontrado.")
    obj.ativo = True
    db.commit(); db.refresh(obj)
    return obj
