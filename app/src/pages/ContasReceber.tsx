import React, { useEffect, useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, ContasReceber, Cliente, TipoReceita } from "../api/client";

interface ParcelaForm { numero: number; data_vencimento: string; valor: string; recebido: boolean }

function emptyParcela(n: number): ParcelaForm {
  return { numero: n, data_vencimento: "", valor: "", recebido: false };
}

export function ContasReceberPage() {
  const [isOpen, setIsOpen] = useState(false);
  const [editing, setEditing] = useState<ContasReceber | null>(null);
  const [reload, setReload] = useState(0);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [clientes, setClientes] = useState<Cliente[]>([]);
  const [tiposReceita, setTiposReceita] = useState<TipoReceita[]>([]);

  const [form, setForm] = useState({ descricao: "", data_emissao: "", valor_total: "", cliente_id: "" });
  const [parcelas, setParcelas] = useState<ParcelaForm[]>([emptyParcela(1)]);
  const [tipoIds, setTipoIds] = useState<number[]>([]);

  useEffect(() => {
    api.clientes.listar(true).then(setClientes);
    api.tiposReceita.listar(true).then(setTiposReceita);
  }, []);

  function openNew() {
    setEditing(null);
    setForm({ descricao: "", data_emissao: "", valor_total: "", cliente_id: "" });
    setParcelas([emptyParcela(1)]); setTipoIds([]);
    setErr(null); setIsOpen(true);
  }

  function openEdit(row: ContasReceber) {
    setEditing(row);
    setForm({ descricao: row.descricao ?? "", data_emissao: row.data_emissao, valor_total: String(row.valor_total), cliente_id: String(row.cliente_id) });
    setParcelas(row.parcelas.map(p => ({ numero: p.numero, data_vencimento: p.data_vencimento, valor: String(p.valor), recebido: p.recebido ?? false })));
    setTipoIds(row.tipo_receita_ids);
    setErr(null); setIsOpen(true);
  }

  function toggleTipo(id: number) {
    setTipoIds(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]);
  }

  function setParcela(i: number, k: keyof ParcelaForm, v: string | boolean) {
    setParcelas(prev => prev.map((p, idx) => idx === i ? { ...p, [k]: v } : p));
  }

  async function save() {
    setSaving(true); setErr(null);
    try {
      const data = {
        descricao: form.descricao || null,
        data_emissao: form.data_emissao,
        valor_total: parseFloat(form.valor_total),
        cliente_id: parseInt(form.cliente_id),
        parcelas: parcelas.map(p => ({ numero: p.numero, data_vencimento: p.data_vencimento, valor: parseFloat(p.valor), recebido: p.recebido })),
        tipo_receita_ids: tipoIds,
      };
      if (editing) await api.contasReceber.atualizar(editing.id, data);
      else await api.contasReceber.criar(data);
      setReload(r => r + 1); setIsOpen(false);
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  return (
    <>
      <CrudPage<ContasReceber>
        key={reload} title="Contas a Receber"
        fetchFn={api.contasReceber.listar}
        columns={[
          { label: "Emissão",    render: r => r.data_emissao },
          { label: "Descrição",  render: r => r.descricao ?? "—" },
          { label: "Valor Total",render: r => `R$ ${r.valor_total.toFixed(2)}` },
          { label: "Parcelas",   render: r => r.parcelas.length },
        ]}
        onNew={openNew} onEdit={openEdit}
        onInativar={api.contasReceber.inativar} onReativar={api.contasReceber.reativar}
      />
      {isOpen && (
        <Modal title={editing ? "Editar Conta a Receber" : "Nova Conta a Receber"} onClose={() => setIsOpen(false)}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGrid2">
            <div className="formGroup"><label>Data Emissão *</label><input type="date" value={form.data_emissao} onChange={e => setForm({ ...form, data_emissao: e.target.value })} /></div>
            <div className="formGroup"><label>Valor Total *</label><input type="number" step="0.01" value={form.valor_total} onChange={e => setForm({ ...form, valor_total: e.target.value })} /></div>
            <div className="formGroup"><label>Cliente *</label>
              <select value={form.cliente_id} onChange={e => setForm({ ...form, cliente_id: e.target.value })}>
                <option value="">Selecione...</option>
                {clientes.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
              </select>
            </div>
          </div>
          <div className="formGroup"><label>Descrição</label><textarea value={form.descricao} onChange={e => setForm({ ...form, descricao: e.target.value })} /></div>

          <div className="sectionLabel">Tipos de Receita *</div>
          <div className="checkGrid">
            {tiposReceita.map(t => (
              <label key={t.id} className="checkItem">
                <input type="checkbox" checked={tipoIds.includes(t.id)} onChange={() => toggleTipo(t.id)} />
                {t.nome}
              </label>
            ))}
          </div>

          <div className="sectionLabel">Parcelas *</div>
          {parcelas.map((p, i) => (
            <div key={i} className="parcelaRow">
              <span className="parcelaNum">{p.numero}ª</span>
              <div className="formGroup"><label>Vencimento</label><input type="date" value={p.data_vencimento} onChange={e => setParcela(i, "data_vencimento", e.target.value)} /></div>
              <div className="formGroup"><label>Valor</label><input type="number" step="0.01" value={p.valor} onChange={e => setParcela(i, "valor", e.target.value)} /></div>
              <label className="checkItem"><input type="checkbox" checked={p.recebido} onChange={e => setParcela(i, "recebido", e.target.checked)} />Recebido</label>
              {parcelas.length > 1 && <button className="btnSm btnDanger" onClick={() => setParcelas(prev => prev.filter((_, idx) => idx !== i))}>✕</button>}
            </div>
          ))}
          <button className="btnSm" style={{ marginTop: 6 }} onClick={() => setParcelas(prev => [...prev, emptyParcela(prev.length + 1)])}>+ Parcela</button>

          <div className="modalFooter">
            <button className="btnSecondary" onClick={() => setIsOpen(false)}>Cancelar</button>
            <button className="btnPrimary" onClick={save} disabled={saving}>{saving ? "Salvando..." : "Salvar"}</button>
          </div>
        </Modal>
      )}
    </>
  );
}
