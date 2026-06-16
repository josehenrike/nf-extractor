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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hasLoaded, setHasLoaded] = useState(false);
  
  const [searchQuery, setSearchQuery] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");

  async function load(forceActiveOnly = false) {
    setLoading(true); setError(null);
    try {
      const activeParam = forceActiveOnly ? true : (showInativos ? undefined : true);
      setRows(await fetchFn(activeParam));
      setHasLoaded(true);
    }
    catch (e) {
      setRows([]);
      const msg = e instanceof Error ? e.message : "";
      if (msg && !msg.toLowerCase().includes("failed to fetch")) {
        setError(msg);
      }
    }
    finally { setLoading(false); }
  }

  useEffect(() => {
    if (hasLoaded) {
      load();
    }
  }, [showInativos]);

  async function toggle(row: T) {
    try {
      if (row.ativo) await onInativar(row.id);
      else await onReativar(row.id);
      load();
    } catch (e) { alert(e instanceof Error ? e.message : "Erro."); }
  }

  function handleSearch() {
    setFilterQuery(searchQuery);
    if (!hasLoaded) {
      load();
    }
  }

  function handleTodos() {
    setSearchQuery("");
    setFilterQuery("");
    setShowInativos(false);
    load(true);
  }

  function handleSort(label: string) {
    if (sortColumn === label) {
      setSortDirection(prev => prev === "asc" ? "desc" : "asc");
    } else {
      setSortColumn(label);
      setSortDirection("asc");
    }
  }

  // Busca por mais de um elemento (busca em qualquer coluna contendo os termos digitados)
  const filteredRows = rows.filter(row => {
    if (!filterQuery.trim()) return true;
    const q = filterQuery.toLowerCase().trim();
    const searchTerms = q.split(/\s+/);
    
    return searchTerms.every(term => {
      return columns.some(col => {
        let val = col.render(row);
        if (React.isValidElement(val)) {
          val = (val.props as any).children ?? "";
        }
        return String(val ?? "").toLowerCase().includes(term);
      });
    });
  });

  // Indexação por coluna na tabela (ordenação)
  const sortedRows = [...filteredRows].sort((a, b) => {
    if (!sortColumn) return 0;
    const col = columns.find(c => c.label === sortColumn);
    if (!col) return 0;
    
    let valA = col.render(a);
    let valB = col.render(b);
    
    if (React.isValidElement(valA)) {
      valA = (valA.props as any).children ?? "";
    }
    if (React.isValidElement(valB)) {
      valB = (valB.props as any).children ?? "";
    }
    
    const strA = String(valA ?? "").toLowerCase().trim();
    const strB = String(valB ?? "").toLowerCase().trim();
    
    const numA = Number(valA);
    const numB = Number(valB);
    if (!isNaN(numA) && !isNaN(numB) && valA !== "" && valB !== "") {
      return sortDirection === "asc" ? numA - numB : numB - numA;
    }
    
    if (strA < strB) return sortDirection === "asc" ? -1 : 1;
    if (strA > strB) return sortDirection === "asc" ? 1 : -1;
    return 0;
  });

  return (
    <div className="crudPage">
      <div className="crudHeader">
        <h2 className="pageTitle">{title}</h2>
        <div className="crudActions">
          <div className="searchBar" style={{ display: "flex", gap: "8px" }}>
            <input
              type="text"
              placeholder="Buscar..."
              className="searchInput"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") {
                  handleSearch();
                }
              }}
              style={{
                padding: "6px 10px",
                border: "1px solid var(--border)",
                borderRadius: "var(--radius-sm)",
                fontSize: "13px",
                outline: "none",
                width: "160px"
              }}
            />
            <button className="btnSecondary btnSm" onClick={handleSearch}>Buscar</button>
            <button className="btnSecondary btnSm" onClick={handleTodos}>Todos</button>
          </div>
          
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
              {columns.map(c => (
                <th
                  key={c.label}
                  onClick={() => handleSort(c.label)}
                  style={{ cursor: "pointer", userSelect: "none" }}
                  title="Clique para ordenar"
                >
                  {c.label} {sortColumn === c.label ? (sortDirection === "asc" ? "▲" : "▼") : "↕"}
                </th>
              ))}
              <th>Status</th>
              <th style={{ width: 150 }}>Ações</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter">Carregando...</td></tr>
            ) : error ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter tdError">{error}</td></tr>
            ) : !hasLoaded ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter">Utilize a busca ou o botão 'Todos' para carregar os registros.</td></tr>
            ) : sortedRows.length === 0 ? (
              <tr><td colSpan={columns.length + 2} className="tdCenter">Nenhum registro encontrado.</td></tr>
            ) : sortedRows.map(row => (
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
                      {row.ativo ? "Excluir" : "Reativar"}
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
