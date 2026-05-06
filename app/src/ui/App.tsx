import React, { useMemo, useRef, useState } from "react";
import { Fornecedores }     from "../pages/Fornecedores";
import { Clientes }         from "../pages/Clientes";
import { Faturados }        from "../pages/Faturados";
import { TiposDespesa }     from "../pages/TiposDespesa";
import { TiposReceita }     from "../pages/TiposReceita";
import { ContasPagarPage }  from "../pages/ContasPagar";
import { ContasReceberPage }from "../pages/ContasReceber";
import { api, AnaliseResult, LancarNfInput } from "../api/client";

// Painel de Análise 
function AnalisePanel({ analise, onLancar, launching, launchError }: {
  analise: AnaliseResult;
  onLancar: () => void;
  launching: boolean;
  launchError: string | null;
}) {
  return (
    <div className="analisePanel">
      <div className="analisePanelTitle">Análise dos Dados</div>

      <div className="analiseEntidade">
        <div className="analiseEntidadeLabel">FORNECEDOR</div>
        <div className="analiseEntidadeNome">{analise.fornecedor.razao_social}</div>
        <div className="analiseEntidadeDoc">CNPJ: {analise.fornecedor.cnpj}</div>
        {analise.fornecedor.existe
          ? <div className="analiseStatus analiseExiste">EXISTE – ID: {analise.fornecedor.id}</div>
          : <div className="analiseStatus analiseNaoExiste">NÃO EXISTE</div>
        }
      </div>

      <div className="analiseEntidade">
        <div className="analiseEntidadeLabel">FATURADO</div>
        <div className="analiseEntidadeNome">{analise.faturado.nome_completo}</div>
        <div className="analiseEntidadeDoc">CPF: {analise.faturado.cpf}</div>
        {analise.faturado.existe
          ? <div className="analiseStatus analiseExiste">EXISTE – ID: {analise.faturado.id}</div>
          : <div className="analiseStatus analiseNaoExiste">NÃO EXISTE</div>
        }
      </div>

      {analise.classificacoes.map((c, i) => (
        <div key={i} className="analiseEntidade">
          <div className="analiseEntidadeLabel">DESPESA</div>
          <div className="analiseEntidadeNome">{c.nome}</div>
          {c.existe
            ? <div className="analiseStatus analiseExiste">EXISTE – ID: {c.id}</div>
            : <div className="analiseStatus analiseNaoExiste">NÃO EXISTE</div>
          }
        </div>
      ))}

      <div className="analiseInfo">
        {[analise.fornecedor, analise.faturado, ...analise.classificacoes].some(e => !e.existe) && (
          <span>Registros inexistentes serão criados automaticamente.</span>
        )}
      </div>

      {launchError && <div className="alertBox">{launchError}</div>}

      <button className="extractBtn" onClick={onLancar} disabled={launching}>
        {launching ? "Lançando..." : "✔ Confirmar e Lançar"}
      </button>
    </div>
  );
}

// Página de Extração NF
function ExtracaoNF() {
  const [file, setFile]           = useState<File | null>(null);
  const [isDragging, setDrag]     = useState(false);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [result, setResult]       = useState<LancarNfInput | null>(null);
  const [copied, setCopied]       = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [analise, setAnalise]     = useState<AnaliseResult | null>(null);
  const [analiseErr, setAnaliseErr] = useState<string | null>(null);

  const [launching, setLaunching] = useState(false);
  const [launchErr, setLaunchErr] = useState<string | null>(null);
  const [success, setSuccess]     = useState<number | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);

  const fileLabel = useMemo(() => file ? `${file.name} · ${Math.round(file.size / 1024)} KB` : null, [file]);

  function handleFile(f?: File | null) {
    if (!f) return;
    if (f.type !== "application/pdf") { setError("Apenas arquivos PDF."); return; }
    setFile(f); setError(null); setResult(null); setAnalise(null); setSuccess(null);
  }

  function reset() {
    setFile(null); setResult(null); setError(null); setAnalise(null);
    setAnaliseErr(null); setLaunchErr(null); setSuccess(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  async function extract() {
    if (!file) { setError("Selecione um PDF."); return; }
    setError(null); setResult(null); setAnalise(null); setSuccess(null); setLoading(true);
    try {
      const form = new FormData(); form.append("file", file);
      const res = await fetch("http://localhost:8001/extract", { method: "POST", body: form });
      const ct = res.headers.get("content-type") ?? "";
      const body = ct.includes("application/json") ? await res.json() : await res.text();
      if (!res.ok) throw new Error(body?.detail ?? body);
      setResult(body as LancarNfInput);
    } catch (e) { setError(e instanceof Error ? e.message : "Erro."); }
    finally { setLoading(false); }
  }

  async function analisar() {
    if (!result) return;
    setAnaliseErr(null); setAnalise(null); setSuccess(null); setLaunchErr(null); setAnalyzing(true);
    try {
      const res = await api.nf.analisar(result);
      setAnalise(res);
    } catch (e) { setAnaliseErr(e instanceof Error ? e.message : "Erro na análise."); }
    finally { setAnalyzing(false); }
  }

  async function lancar() {
    if (!result) return;
    setLaunchErr(null); setLaunching(true);
    try {
      const res = await api.nf.lancar(result);
      setSuccess(res.conta_pagar_id);
    } catch (e) { setLaunchErr(e instanceof Error ? e.message : "Erro ao lançar."); }
    finally { setLaunching(false); }
  }

  function copy() {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true); setTimeout(() => setCopied(false), 2000);
  }

  return (
    <div className="extractPage">
      {/* Coluna esquerda: upload */}
      <div className="extractLeft">
        <div className="panelTitle">Nota Fiscal</div>
        <div
          className={`dropzone${isDragging ? " dragging" : ""}${file ? " hasFile" : ""}`}
          onClick={() => inputRef.current?.click()}
          onDragOver={e => { e.preventDefault(); setDrag(true); }}
          onDragLeave={() => setDrag(false)}
          onDrop={e => { e.preventDefault(); setDrag(false); handleFile(e.dataTransfer.files?.[0]); }}
        >
          <input ref={inputRef} type="file" accept="application/pdf" style={{ display: "none" }} onChange={e => handleFile(e.target.files?.[0])} />
          {file ? (
            <div className="fileInfo">
              <div className="fileIcon">📄</div>
              <div className="fileMeta"><span className="fileName">{file.name}</span><span className="fileSize">{Math.round(file.size / 1024)} KB</span></div>
            </div>
          ) : (
            <div className="dropContent">
              <div className="dropIcon">⬆</div>
              <span className="dropLabel">Arraste o PDF aqui</span>
              <span className="dropSub">ou clique para selecionar</span>
            </div>
          )}
        </div>
        {fileLabel && (
          <div className="fileRow">
            <span className="filePill">{fileLabel}</span>
            <button className="iconBtn" onClick={reset}>✕</button>
          </div>
        )}
        {error && <div className="alertBox">{error}</div>}
        <button className="extractBtn" onClick={extract} disabled={!file || loading}>
          {loading ? "Extraindo..." : "✦ Extrair dados"}
        </button>
      </div>

      {/* Coluna direita: JSON + Análise empilhados verticalmente */}
      <div className="extractRightCol">
        <div className="extractRight">
          <div className="resultHeader">
            <div className="panelTitle">Dados Extraídos</div>
            {result && <button className="iconBtn iconBtnText" onClick={copy}>{copied ? "✓ Copiado" : "Copiar"}</button>}
          </div>

          {success !== null ? (
            <div className="successBox">
              <div className="successIcon">✔</div>
              <div className="successTitle">Lançado com Sucesso!</div>
              <div className="successSub">Conta a Pagar criada com ID <strong>#{success}</strong></div>
              <button className="btnSecondary" style={{ marginTop: 12 }} onClick={reset}>Nova Extração</button>
            </div>
          ) : result ? (
            <>
              <pre className="json">{JSON.stringify(result, null, 2)}</pre>
              {!analise && (
                <>
                  {analiseErr && <div className="alertBox">{analiseErr}</div>}
                  <button className="extractBtn analiseBtn" onClick={analisar} disabled={analyzing}>
                    {analyzing ? "Analisando..." : "⟳ Analisar e Lançar"}
                  </button>
                </>
              )}
            </>
          ) : (
            <div className="emptyState"><div className="emptyIcon">✦</div><span>O JSON extraído aparecerá aqui</span></div>
          )}
        </div>

        {/* Painel de análise abaixo do JSON */}
        {analise && success === null && (
          <AnalisePanel
            analise={analise}
            onLancar={lancar}
            launching={launching}
            launchError={launchErr}
          />
        )}
      </div>
    </div>
  );
}

// Navegação 

type Page = "extracao" | "fornecedores" | "clientes" | "faturados" | "tipos-despesa" | "tipos-receita" | "contas-pagar" | "contas-receber";

const NAV: { group: string; items: { id: Page; label: string }[] }[] = [
  {
    group: "Extração",
    items: [{ id: "extracao", label: "Extração de NF" }],
  },
  {
    group: "Cadastros",
    items: [
      { id: "fornecedores", label: "Fornecedores" },
      { id: "clientes", label: "Clientes" },
      { id: "faturados", label: "Faturados" },
      { id: "tipos-despesa", label: "Tipos de Despesa" },
      { id: "tipos-receita", label: "Tipos de Receita" },
    ],
  },
  {
    group: "Financeiro",
    items: [
      { id: "contas-pagar", label: "Contas a Pagar" },
      { id: "contas-receber", label: "Contas a Receber" },
    ],
  },
];

export function App() {
  const [page, setPage] = useState<Page>("extracao");

  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="sidebarLogo">
          <div className="logoIconSm">NF</div>
          <span>NF Extractor</span>
        </div>
        <nav className="sidebarNav">
          {NAV.map(g => (
            <div key={g.group} className="navGroup">
              <div className="navGroupLabel">{g.group}</div>
              {g.items.map(item => (
                <button
                  key={item.id}
                  className={`navItem${page === item.id ? " active" : ""}`}
                  onClick={() => setPage(item.id)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          ))}
        </nav>
      </aside>
      <main className="content">
        {page === "extracao" && <ExtracaoNF />}
        {page === "fornecedores" && <Fornecedores />}
        {page === "clientes" && <Clientes />}
        {page === "faturados" && <Faturados />}
        {page === "tipos-despesa" && <TiposDespesa />}
        {page === "tipos-receita" && <TiposReceita />}
        {page === "contas-pagar" && <ContasPagarPage />}
        {page === "contas-receber" && <ContasReceberPage />}
      </main>
    </div>
  );
}
