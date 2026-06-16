import React, { useState } from "react";
import { api, RagResponse } from "../api/client";

// Perguntas de exemplo para facilitar o uso
const EXEMPLOS = [
  "Quais fornecedores têm contas a pagar em aberto?",
  "Qual é o total de valores a pagar por fornecedor?",
  "Quais parcelas vencem nos próximos meses?",
  "Quais contas a receber ainda estão em aberto?",
  "Qual é o total de receitas por tipo?",
  "Quais são os clientes com maior valor a receber?",
  "Liste todas as despesas classificadas como MANUTENÇÃO E OPERAÇÃO.",
  "Qual o valor total de contas pagas vs pendentes?",
];

export function ConsultaRAG() {
  const [modo, setModo] = useState<"simples" | "embeddings">("simples");
  const [pergunta, setPergunta] = useState("");
  const [loading, setLoading] = useState(false);
  const [resultado, setResultado] = useState<RagResponse | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  async function perguntar() {
    if (!pergunta.trim()) return;
    setErro(null);
    setResultado(null);
    setLoading(true);
    try {
      const res = modo === "simples"
        ? await api.rag.simples(pergunta)
        : await api.rag.embeddings(pergunta);
      setResultado(res);
    } catch (e) {
      setErro(e instanceof Error ? e.message : "Erro ao consultar.");
    } finally {
      setLoading(false);
    }
  }

  function usarExemplo(ex: string) {
    setPergunta(ex);
    setResultado(null);
    setErro(null);
  }

  return (
    <div className="ragPage">
      {/* Cabeçalho */}
      <div className="ragHeader">
        <div>
          <h2 className="pageTitle">Consulta Inteligente com RAG</h2>
          <p className="ragSubtitle">
            Faça perguntas em linguagem natural sobre os dados financeiros do sistema.
          </p>
        </div>
        {/* Badge de modo */}
        <div className="ragModoBadge">
          <span className={`ragModoChip ${modo === "simples" ? "active" : ""}`}>
            RAG Simples
          </span>
          <span className="ragModoSep">vs</span>
          <span className={`ragModoChip ${modo === "embeddings" ? "active" : ""}`}>
            RAG Embeddings
          </span>
        </div>
      </div>

      {/* Toggle de modo */}
      <div className="ragModoToggle">
        <button
          id="btn-rag-simples"
          className={`ragModoBtn ${modo === "simples" ? "active" : ""}`}
          onClick={() => { setModo("simples"); setResultado(null); setErro(null); }}
        >
          <div className="ragModoBtnTexto">
            <span className="ragModoBtnTitulo">RAG Simples</span>
            <span className="ragModoBtnDesc">Todos os dados como contexto para o LLM</span>
          </div>
        </button>
        <button
          id="btn-rag-embeddings"
          className={`ragModoBtn ${modo === "embeddings" ? "active" : ""}`}
          onClick={() => { setModo("embeddings"); setResultado(null); setErro(null); }}
        >
          <div className="ragModoBtnTexto">
            <span className="ragModoBtnTitulo">RAG Embeddings</span>
            <span className="ragModoBtnDesc">Busca vetorial por similaridade semântica</span>
          </div>
        </button>
      </div>

      {/* Chips de exemplos */}
      <div className="ragExemplos">
        <span className="ragExemplosLabel">Perguntas exemplo:</span>
        <div className="ragChips">
          {EXEMPLOS.map((ex) => (
            <button
              key={ex}
              className="ragChip"
              onClick={() => usarExemplo(ex)}
              title={ex}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      {/* Input de pergunta */}
      <div className="ragInputArea">
        <div className="ragInputWrap">
          <textarea
            id="rag-pergunta-input"
            className="ragTextarea"
            rows={3}
            placeholder="Digite sua pergunta sobre os dados financeiros do sistema..."
            value={pergunta}
            onChange={(e) => setPergunta(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                perguntar();
              }
            }}
          />
          <div className="ragInputFooter">
            <span className="ragInputHint">Enter para enviar · Shift+Enter para nova linha</span>
            <button
              id="btn-rag-perguntar"
              className="extractBtn ragPerguntar"
              onClick={perguntar}
              disabled={!pergunta.trim() || loading}
            >
              {loading ? (
                <>
                  <span className="ragSpinner" />
                  Consultando...
                </>
              ) : (
                <>Perguntar</>
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Erro */}
      {erro && (
        <div className="alertBox ragErro">
          <strong>Erro:</strong> {erro}
        </div>
      )}

      {/* Resultado */}
      {loading && !resultado && (
        <div className="ragLoading">
          <div className="ragLoadingDots">
            <span /><span /><span />
          </div>
          <p>O agente {modo === "embeddings" ? "está calculando embeddings e " : ""}está analisando os dados...</p>
        </div>
      )}

      {resultado && (
        <div className="ragResultado">
          {/* Meta-info */}
          <div className="ragResultMeta">
            <span className={`ragResultModoBadge ragResultModo-${resultado.modo}`}>
              {resultado.modo === "simples" ? "RAG Simples (SQL Direto)" : "RAG Embeddings"}
            </span>
            <span className="ragResultDocs">
              {resultado.modo === "simples"
                ? `${resultado.documentos_usados} registro(s) retornado(s)`
                : `${resultado.documentos_usados} documento(s) consultado(s)`
              }
            </span>
            <span className="ragResultPergunta">
              Pergunta: <em>"{pergunta}"</em>
            </span>
          </div>

          {/* Resposta */}
          <div className="ragResposta">
            <div className="ragRespostaHeader">
              <span className="ragRespostaTitulo">Resposta do Assistente</span>
            </div>
            <div
              className="ragRespostaTexto"
              dangerouslySetInnerHTML={{
                __html: resultado.resposta
                  // Codigos: ```sql ... ``` ou ``` ... ```
                  .replace(/```sql\s*([\s\S]*?)\s*```/g, '<pre class="ragCodeBlock"><code>$1</code></pre>')
                  .replace(/```\s*([\s\S]*?)\s*```/g, '<pre class="ragCodeBlock"><code>$1</code></pre>')
                  // Negrito: **texto**
                  .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
                  // Itálico: *texto*
                  .replace(/(?<!\*)\*(?!\*)(.*?)(?<!\*)\*(?!\*)/g, "<em>$1</em>")
                  // Cabeçalhos: ## Título
                  .replace(/^### (.+)$/gm, "<h4>$1</h4>")
                  .replace(/^## (.+)$/gm, "<h3>$1</h3>")
                  // Listas: - item
                  .replace(/^- (.+)$/gm, "<li>$1</li>")
                  .replace(/(<li>.*<\/li>\n?)+/g, (m) => `<ul>${m}</ul>`)
                  // Quebras de linha
                  .replace(/\n\n/g, "</p><p>")
                  .replace(/\n/g, "<br/>"),
              }}
            />
          </div>

          {/* Nova pergunta */}
          <div className="ragResultFooter">
            <button
              className="btnSecondary"
              onClick={() => { setResultado(null); setPergunta(""); }}
            >
              Nova Pergunta
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
