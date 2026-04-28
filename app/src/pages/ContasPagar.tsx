import React, { useEffect, useState } from "react";
import { CrudPage } from "../ui/CrudPage";
import { Modal } from "../ui/Modal";
import { api, ContasPagar, Fornecedor, Faturado, TipoDespesa } from "../api/client";

interface ParcelaForm { numero: number; data_vencimento: string; valor: string; pago: boolean }

function emptyParcela(n: number): ParcelaForm {
  return { numero: n, data_vencimento: "", valor: "", pago: false };
}

export function ContasPagarPage() {
  const [isOpen, setIsOpen] = useState(false);
  const [editing, setEditing] = useState<ContasPagar | null>(null);
  const [reload, setReload] = useState(0);
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [fornecedores, setFornecedores] = useState<Fornecedor[]>([]);
  const [faturados, setFaturados] = useState<Faturado[]>([]);
  const [tiposDespesa, setTiposDespesa] = useState<TipoDespesa[]>([]);

  const [form, setForm] = useState({
    numero_nf: "", data_emissao: "", descricao: "", valor_total: "",
    fornecedor_id: "", faturado_id: "",
  });
  const [parcelas, setParcelas] = useState<ParcelaForm[]>([emptyParcela(1)]);
  const [tipoIds, setTipoIds] = useState<number[]>([]);

  useEffect(() => {
    api.fornecedores.listar(true).then(setFornecedores);
    api.faturados.listar(true).then(setFaturados);
    api.tiposDespesa.listar(true).then(setTiposDespesa);
  }, []);

  function openNew() {
    setEditing(null);
    setForm({ numero_nf: "", data_emissao: "", descricao: "", valor_total: "", fornecedor_id: "", faturado_id: "" });
    setParcelas([emptyParcela(1)]);
    setTipoIds([]);
    setErr(null); setIsOpen(true);
  }

  function openEdit(row: ContasPagar) {
    setEditing(row);
    setForm({
      numero_nf: row.numero_nf ?? "",
      data_emissao: row.data_emissao,
      descricao: row.descricao ?? "",
      valor_total: String(row.valor_total),
      fornecedor_id: String(row.fornecedor_id),
      faturado_id: row.faturado_id ? String(row.faturado_id) : "",
    });
    setParcelas(row.parcelas.map(p => ({ numero: p.numero, data_vencimento: p.data_vencimento, valor: String(p.valor), pago: p.pago ?? false })));
    setTipoIds(row.tipo_despesa_ids);
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
        numero_nf: form.numero_nf || null,
        data_emissao: form.data_emissao,
        descricao: form.descricao || null,
        valor_total: parseFloat(form.valor_total),
        fornecedor_id: parseInt(form.fornecedor_id),
        faturado_id: form.faturado_id ? parseInt(form.faturado_id) : null,
        parcelas: parcelas.map(p => ({ numero: p.numero, data_vencimento: p.data_vencimento, valor: parseFloat(p.valor), pago: p.pago })),
        tipo_despesa_ids: tipoIds,
      };
      if (editing) await api.contasPagar.atualizar(editing.id, data);
      else await api.contasPagar.criar(data);
      setReload(r => r + 1); setIsOpen(false);
    } catch (e) { setErr(e instanceof Error ? e.message : "Erro."); }
    finally { setSaving(false); }
  }

  return (
    <>
      <CrudPage<ContasPagar>
        key={reload} title="Contas a Pagar"
        fetchFn={api.contasPagar.listar}
        columns={[
          { label: "NF",         render: r => r.numero_nf ?? "—" },
          { label: "Emissão",    render: r => r.data_emissao },
          { label: "Descrição",  render: r => r.descricao ?? "—" },
          { label: "Valor Total",render: r => `R$ ${r.valor_total.toFixed(2)}` },
          { label: "Parcelas",   render: r => r.parcelas.length },
        ]}
        onNew={openNew} onEdit={openEdit}
        onInativar={api.contasPagar.inativar} onReativar={api.contasPagar.reativar}
      />
      {isOpen && (
        <Modal title={editing ? "Editar Conta a Pagar" : "Nova Conta a Pagar"} onClose={() => setIsOpen(false)}>
          {err && <div className="alertBox">{err}</div>}
          <div className="formGrid2">
            <div className="formGroup"><label>Nº NF</label><input value={form.numero_nf} onChange={e => setForm({ ...form, numero_nf: e.target.value })} /></div>
            <div className="formGroup"><label>Data Emissão *</label><input type="date" value={form.data_emissao} onChange={e => setForm({ ...form, data_emissao: e.target.value })} /></div>
            <div className="formGroup"><label>Valor Total *</label><input type="number" step="0.01" value={form.valor_total} onChange={e => setForm({ ...form, valor_total: e.target.value })} /></div>
            <div className="formGroup"><label>Fornecedor *</label>
              <select value={form.fornecedor_id} onChange={e => setForm({ ...form, fornecedor_id: e.target.value })}>
                <option value="">Selecione...</option>
                {fornecedores.map(f => <option key={f.id} value={f.id}>{f.razao_social}</option>)}
              </select>
            </div>
            <div className="formGroup"><label>Faturado</label>
              <select value={form.faturado_id} onChange={e => setForm({ ...form, faturado_id: e.target.value })}>
                <option value="">Selecione...</option>
                {faturados.map(f => <option key={f.id} value={f.id}>{f.nome_completo}</option>)}
              </select>
            </div>
          </div>
          <div className="formGroup"><label>Descrição</label><textarea value={form.descricao} onChange={e => setForm({ ...form, descricao: e.target.value })} /></div>

          <div className="sectionLabel">Tipos de Despesa *</div>
          <div className="checkGrid">
            {tiposDespesa.map(t => (
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
              <label className="checkItem"><input type="checkbox" checked={p.pago} onChange={e => setParcela(i, "pago", e.target.checked)} />Pago</label>
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
