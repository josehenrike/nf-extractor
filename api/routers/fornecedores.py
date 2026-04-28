from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models, schemas

router = APIRouter(prefix="/fornecedores", tags=["Fornecedores"])


@router.get("", response_model=List[schemas.FornecedorOut])
def listar(ativo: Optional[bool] = None, db: Session = Depends(get_db)):
    q = db.query(models.Fornecedor)
    if ativo is not None:
        q = q.filter(models.Fornecedor.ativo == ativo)
    return q.order_by(models.Fornecedor.razao_social).all()


@router.post("", response_model=schemas.FornecedorOut, status_code=201)
def criar(body: schemas.FornecedorCreate, db: Session = Depends(get_db)):
    if db.query(models.Fornecedor).filter(models.Fornecedor.cnpj == body.cnpj).first():
        raise HTTPException(400, "CNPJ já cadastrado.")
    obj = models.Fornecedor(**body.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj


@router.get("/{id}", response_model=schemas.FornecedorOut)
def obter(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Fornecedor, id)
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado.")
    return obj


@router.put("/{id}", response_model=schemas.FornecedorOut)
def atualizar(id: int, body: schemas.FornecedorUpdate, db: Session = Depends(get_db)):
    obj = db.get(models.Fornecedor, id)
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado.")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(obj, k, v)
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/inativar", response_model=schemas.FornecedorOut)
def inativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Fornecedor, id)
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado.")
    obj.ativo = False
    db.commit(); db.refresh(obj)
    return obj


@router.patch("/{id}/reativar", response_model=schemas.FornecedorOut)
def reativar(id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Fornecedor, id)
    if not obj:
        raise HTTPException(404, "Fornecedor não encontrado.")
    obj.ativo = True
    db.commit(); db.refresh(obj)
    return obj
