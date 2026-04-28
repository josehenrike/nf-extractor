import React, { useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, Fornecedor } from "../api/client";

export function Fornecedores() {
  const [editing, setEditing] = useState<Fornecedor | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState({ razao_social: "", fantasia: "", cnpj: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  function openNew() {
    setForm({ razao_social: "", fantasia: "", cnpj: "" });
    setEditing(null); setIsNew(true); setErr(null);
  }
  function openEdit(row: Fornecedor) {
    setForm({ razao_social: row.razao_social, fantasia: row.fantasia ?? "", cnpj: row.cnpj });
    setEditing(row); setIsNew(false); setErr(null);
  }
  function close() { setIsNew(false); setEditing(null); }

  async function save() {
    setSaving(true); setErr(null);
    try {
      const data = { razao_social: form.razao_social, fantasia: form.fantasia || null, cnpj: form.cnpj };
      if (editing) await api.fornecedores.atualizar(editing.id, data);
      else await api.fornecedores.criar(data);
      setReload(r => r + 1); close();
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  return (
    <>
      <CrudPage<Fornecedor>
        key={reload}
        title="Fornecedores"
        fetchFn={api.fornecedores.listar}
        columns={[
          { label: "Razão Social", render: r => r.razao_social },
          { label: "Fantasia",     render: r => r.fantasia ?? "—" },
          { label: "CNPJ",         render: r => r.cnpj },
        ]}
        onNew={openNew}
        onEdit={openEdit}
        onInativar={api.fornecedores.inativar}
        onReativar={api.fornecedores.reativar}
      />
      {(isNew || editing) && (
        <Modal title={editing ? "Editar Fornecedor" : "Novo Fornecedor"} onClose={close}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGroup">
            <label>Razão Social *</label>
            <input value={form.razao_social} onChange={e => setForm({ ...form, razao_social: e.target.value })} />
          </div>
          <div className="formGroup">
            <label>Fantasia</label>
            <input value={form.fantasia} onChange={e => setForm({ ...form, fantasia: e.target.value })} />
          </div>
          <div className="formGroup">
            <label>CNPJ *</label>
            <input value={form.cnpj} onChange={e => setForm({ ...form, cnpj: e.target.value })} />
          </div>
          <div className="modalFooter">
            <button className="btnSecondary" onClick={close}>Cancelar</button>
            <button className="btnPrimary" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
