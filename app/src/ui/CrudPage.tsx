import React, { useEffect, useState } from "react";

export interface Column<T> {
  label: string;
  render: (row: T) => React.ReactNode;
}

interface Props<T extends { id: number; ativo: boolean }> {
  title: string;
  columns: Column<T>[];
  fetchFn: (ativo?: boolean) => Promise<T[]>;
  onNew: () => void;
  onEdit: (row: T) => void;
  onInativar: (id: number) => Promise<unknown>;
  onReativar: (id: number) => Promise<unknown>;
}

export function CrudPage<T extends { id: number; ativo: boolean }>({
  title, columns, fetchFn, onNew, onEdit, onInativar, onReativar,
}: Props<T>) {
  const [rows, setRows] = useState<T[]>([]);
  const [showInativos, setShowInativos] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true); setError(null);
    try { setRows(await fetchFn(showInativos ? undefined : true)); }
    catch (e) {
      setRows([]);
      const msg = e instanceof Error ? e.message : "";
      if (msg && !msg.toLowerCase().includes("failed to fetch")) {
        setError(msg);
      }
    }
    finally { setLoading(false); }
  }

  useEffect(() => { load(); }, [showInativos]);

  async function toggle(row: T) {
    try {
      if (row.ativo) await onInativar(row.id);
      else await onReativar(row.id);
      load();
    } catch (e) { alert(e instanceof Error ? e.message : "Erro."); }
  }

  return (
    <div className="crudPage">
      <div className="crudHeader">
        <h2 className="pageTitle">{title}</h2>
        <div className="crudActions">
          <label className="toggleLabel">
            <input type="checkbox" checked={showInativos} onChange={e => setShowInativos(e.target.checked)} />
            Exibir inativos
          </label>
          <button className="btnPrimary" onClick={onNew}>+ Novo</button>
        </div>
      </div>

      <div className="tableWrap">
        <table className="table">
          <thead>
            <tr>
              {columns.map(c => <th key={c.label}>{c.label}</th>)}
              <th>Status</th>
              <th style={{ width: 120 }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter">Carregando...</td></tr>
            ) : error ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter tdError">{error}</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter">Nenhum registro encontrado.</td></tr>
            ) : rows.map(row => (
              <tr key={row.id} className={row.ativo ? "" : "rowInativo"}>
                {columns.map(c => <td key={c.label}>{c.render(row)}</td>)}
                <td>
                  <span className={`statusBadge ${row.ativo ? "ativo" : "inativo"}`}>
                    {row.ativo ? "Ativo" : "Inativo"}
                  </span>
                </td>
                <td>
                  <div className="rowActions">
                    <button className="btnSm" onClick={() => onEdit(row)}>Editar</button>
                    <button className={`btnSm ${row.ativo ? "btnDanger" : "btnSuccess"}`} onClick={() => toggle(row)}>
                      {row.ativo ? "Inativar" : "Reativar"}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
