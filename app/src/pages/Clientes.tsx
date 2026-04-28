import React, { useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, Cliente } from "../api/client";

export function Clientes() {
  const [editing, setEditing] = useState<Cliente | null>(null);
  const [isNew, setIsNew] = useState(false);
  const [form, setForm] = useState({ nome: "", cpf_cnpj: "", email: "", telefone: "" });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [reload, setReload] = useState(0);

  function openNew() { setForm({ nome: "", cpf_cnpj: "", email: "", telefone: "" }); setEditing(null); setIsNew(true); setErr(null); }
  function openEdit(row: Cliente) {
    setForm({ nome: row.nome, cpf_cnpj: row.cpf_cnpj, email: row.email ?? "", telefone: row.telefone ?? "" });
    setEditing(row); setIsNew(false); setErr(null);
  }
  function close() { setIsNew(false); setEditing(null); }

  async function save() {
    setSaving(true); setErr(null);
    try {
      const data = { nome: form.nome, cpf_cnpj: form.cpf_cnpj, email: form.email || null, telefone: form.telefone || null };
      if (editing) await api.clientes.atualizar(editing.id, data);
      else await api.clientes.criar(data);
      setReload(r => r + 1); close();
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  const f = (k: keyof typeof form) => (e: React.ChangeEvent<HTMLInputElement>) => setForm({ ...form, [k]: e.target.value });

  return (
    <>
      <CrudPage<Cliente>
        key={reload}
        title="Clientes"
        fetchFn={api.clientes.listar}
        columns={[
          { label: "Nome",       render: r => r.nome },
          { label: "CPF/CNPJ",  render: r => r.cpf_cnpj },
          { label: "E-mail",    render: r => r.email ?? "—" },
          { label: "Telefone",  render: r => r.telefone ?? "—" },
        ]}
        onNew={openNew} onEdit={openEdit}
        onInativar={api.clientes.inativar} onReativar={api.clientes.reativar}
      />
      {(isNew || editing) && (
        <Modal title={editing ? "Editar Cliente" : "Novo Cliente"} onClose={close}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGroup"><label>Nome *</label><input value={form.nome} onChange={f("nome")} /></div>
          <div className="formGroup"><label>CPF/CNPJ *</label><input value={form.cpf_cnpj} onChange={f("cpf_cnpj")} /></div>
          <div className="formGroup"><label>E-mail</label><input value={form.email} onChange={f("email")} /></div>
          <div className="formGroup"><label>Telefone</label><input value={form.telefone} onChange={f("telefone")} /></div>
          <div className="modalFooter">
            <button className="btnSecondary" onClick={close}>Cancelar</button>
            <button className="btnPrimary" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
