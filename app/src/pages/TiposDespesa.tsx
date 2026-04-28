import React, { useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, TipoDespesa } from "../api/client";

export function TiposDespesa() {
  const [editing, setEditing] = useState<TipoDespesa | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState({ nome: "", descricao: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  function openNew() { setForm({ nome: "", descricao: "" }); setEditing(null); setIsNew(true); setErr(null); }
  function openEdit(r: TipoDespesa) { setForm({ nome: r.nome, descricao: r.descricao ?? "" }); setEditing(r); setIsNew(false); setErr(null); }
  function close() { setIsNew(false); setEditing(null); }

  async function save() {
    setSaving(true); setErr(null);
    try {
      const data = { nome: form.nome, descricao: form.descricao || null };
      if (editing) await api.tiposDespesa.atualizar(editing.id, data);
      else await api.tiposDespesa.criar(data);
      setReload(r => r + 1); close();
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  return (
    <>
      <CrudPage<TipoDespesa>
        key={reload} title="Tipos de Despesa"
        fetchFn={api.tiposDespesa.listar}
        columns={[
          { label: "Nome",      render: r => r.nome },
          { label: "Descrição", render: r => r.descricao ?? "—" },
        ]}
        onNew={openNew} onEdit={openEdit}
        onInativar={api.tiposDespesa.inativar} onReativar={api.tiposDespesa.reativar}
      />
      {(isNew || editing) && (
        <Modal title={editing ? "Editar Tipo de Despesa" : "Novo Tipo de Despesa"} onClose={close}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGroup"><label>Nome *</label><input value={form.nome} onChange={e => setForm({ ...form, nome: e.target.value })} /></div>
          <div className="formGroup"><label>Descrição</label><textarea value={form.descricao} onChange={e => setForm({ ...form, descricao: e.target.value })} /></div>
          <div className="modalFooter">
            <button className="btnSecondary" onClick={close}>Cancelar</button>
            <button className="btnPrimary" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
