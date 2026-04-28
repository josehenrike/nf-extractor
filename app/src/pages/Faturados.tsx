import React, { useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, Faturado } from "../api/client";

export function Faturados() {
  const [editing, setEditing] = useState<Faturado | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState({ nome_completo: "", cpf: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  function openNew() { setForm({ nome_completo: "", cpf: "" }); setEditing(null); setIsNew(true); setErr(null); }
  function openEdit(r: Faturado) { setForm({ nome_completo: r.nome_completo, cpf: r.cpf }); setEditing(r); setIsNew(false); setErr(null); }
  function close() { setIsNew(false); setEditing(null); }

  async function save() {
    setSaving(true); setErr(null);
    try {
      if (editing) await api.faturados.atualizar(editing.id, form);
      else await api.faturados.criar(form);
      setReload(r => r + 1); close();
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  return (
    <>
      <CrudPage<Faturado>
        key={reload} title="Faturados"
        fetchFn={api.faturados.listar}
        columns={[
          { label: "Nome Completo", render: r => r.nome_completo },
          { label: "CPF",           render: r => r.cpf },
        ]}
        onNew={openNew} onEdit={openEdit}
        onInativar={api.faturados.inativar} onReativar={api.faturados.reativar}
      />
      {(isNew || editing) && (
        <Modal title={editing ? "Editar Faturado" : "Novo Faturado"} onClose={close}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGroup"><label>Nome Completo *</label><input value={form.nome_completo} onChange={e => setForm({ ...form, nome_completo: e.target.value })} /></div>
          <div className="formGroup"><label>CPF *</label><input value={form.cpf} onChange={e => setForm({ ...form, cpf: e.target.value })} /></div>
          <div className="modalFooter">
            <button className="btnSecondary" onClick={close}>Cancelar</button>
            <button className="btnPrimary" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
