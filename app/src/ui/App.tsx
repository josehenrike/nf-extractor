import React, { useMemo, useRef, useState } from "react";

type ExtractResponse = Record<string, unknown>;

const API_BASE = "http://localhost:8001";

function IconUpload() {
  return (
    <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
      <polyline points="17 8 12 3 7 8"/>
      <line x1="12" y1="3" x2="12" y2="15"/>
    </svg>
  );
}

function IconFile() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  );
}

function IconSpark() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 2L9.5 9.5 2 12l7.5 2.5L12 22l2.5-7.5L22 12l-7.5-2.5z"/>
    </svg>
  );
}

function IconCopy() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
    </svg>
  );
}

function IconCheck() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="20 6 9 17 4 12"/>
    </svg>
  );
}

function IconTrash() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="3 6 5 6 21 6"/>
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
      <path d="M10 11v6M14 11v6"/>
    </svg>
  );
}

function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export function App() {
  const [file, setFile] = useState<File | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ExtractResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const fileLabel = useMemo(() => {
    if (!file) return null;
    return `${file.name} · ${Math.round(file.size / 1024)} KB`;
  }, [file]);

  function handleFile(f: File | null | undefined) {
    if (!f) return;
    if (f.type !== "application/pdf") {
      setError("Apenas arquivos PDF são suportados.");
      return;
    }
    setFile(f);
    setError(null);
    setResult(null);
  }

  async function onExtract() {
    setError(null);
    setResult(null);
    if (!file) { setError("Selecione um PDF antes de extrair."); return; }
    setIsLoading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const resp = await fetch(`${API_BASE}/extract`, { method: "POST", body: form });
      const ct = resp.headers.get("content-type") ?? "";
      const payload = ct.includes("application/json") ? await resp.json() : await resp.text();
      if (!resp.ok) {
        const msg = typeof payload === "string" ? payload : (payload?.detail as string) ?? "Erro ao extrair.";
        throw new Error(msg);
      }
      setResult(payload as ExtractResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
    } finally {
      setIsLoading(false);
    }
  }

  function onCopy() {
    if (!result) return;
    navigator.clipboard.writeText(JSON.stringify(result, null, 2)).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function onClear() {
    setFile(null);
    setError(null);
    setResult(null);
    if (inputRef.current) inputRef.current.value = "";
  }

  const jsonText = result ? JSON.stringify(result, null, 2) : "";

  return (
    <div className="page">
      <header className="header">
        <div className="logo">
          <div className="logoIcon"><IconSpark /></div>
          <h1>NF Extractor</h1>
          <span className="subtitle">Extração de notas fiscais com IA</span>
        </div>
      </header>

      <div className="layout">
        <section className="panel">
          <div className="panelTitle">Nota Fiscal</div>

          <div
            className={`dropzone${isDragging ? " dragging" : ""}${file ? " hasFile" : ""}`}
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setIsDragging(false);
              handleFile(e.dataTransfer.files?.[0]);
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept="application/pdf"
              style={{ display: "none" }}
              onChange={(e) => handleFile(e.target.files?.[0])}
            />
            {file ? (
              <div className="fileInfo">
                <div className="fileIcon"><IconFile /></div>
                <div className="fileMeta">
                  <span className="fileName">{file.name}</span>
                  <span className="fileSize">{Math.round(file.size / 1024)} KB</span>
                </div>
              </div>
            ) : (
              <div className="dropContent">
                <div className="dropIcon"><IconUpload /></div>
                <span className="dropLabel">Arraste o PDF aqui</span>
                <span className="dropSub">ou clique para selecionar</span>
              </div>
            )}
          </div>

          {fileLabel && (
            <div className="fileRow">
              <span className="filePill">{fileLabel}</span>
              <button className="iconBtn" onClick={onClear} title="Remover arquivo">
                <IconTrash />
              </button>
            </div>
          )}

          {error && <div className="alert">{error}</div>}

          <button
            className="extractBtn"
            onClick={onExtract}
            disabled={!file || isLoading}
          >
            {isLoading ? (
              <><Spinner /> Extraindo...</>
            ) : (
              <><IconSpark /> Extrair dados</>
            )}
          </button>
        </section>

        <section className="panel resultPanel">
          <div className="resultHeader">
            <div className="panelTitle">Resultado JSON</div>
            {result && (
              <button className="iconBtn iconBtnText" onClick={onCopy}>
                {copied ? <><IconCheck /> Copiado</> : <><IconCopy /> Copiar</>}
              </button>
            )}
          </div>

          {result ? (
            <pre className="json">{jsonText}</pre>
          ) : (
            <div className="emptyState">
              <div className="emptyIcon"><IconSpark /></div>
              <span>O JSON extraído aparecerá aqui</span>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}
