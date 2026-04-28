const BASE = "http://localhost:8001";

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  const ct = res.headers.get("content-type") ?? "";
  const body = ct.includes("application/json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error(body?.detail ?? body ?? "Erro na requisição");
  return body as T;
}

const get  = <T>(path: string) => req<T>(path);
const post = <T>(path: string, data: unknown) => req<T>(path, { method: "POST", body: JSON.stringify(data) });
const put  = <T>(path: string, data: unknown) => req<T>(path, { method: "PUT",  body: JSON.stringify(data) });
const patch = <T>(path: string) => req<T>(path, { method: "PATCH" });

// ─── Tipos ────────────────────────────────────────────────────────────────────
export interface Fornecedor  { id: number; razao_social: string; fantasia: string | null; cnpj: string; ativo: boolean }
export interface Cliente     { id: number; nome: string; cpf_cnpj: string; email: string | null; telefone: string | null; ativo: boolean }
export interface Faturado    { id: number; nome_completo: string; cpf: string; ativo: boolean }
export interface TipoDespesa { id: number; nome: string; descricao: string | null; ativo: boolean }
export interface TipoReceita { id: number; nome: string; descricao: string | null; ativo: boolean }

export interface Parcela     { numero: number; data_vencimento: string; valor: number; pago?: boolean; recebido?: boolean }
export interface ContasPagar {
  id: number; numero_nf: string | null; data_emissao: string; descricao: string | null;
  valor_total: number; fornecedor_id: number; faturado_id: number | null;
  ativo: boolean; parcelas: (Parcela & { id: number })[]; tipo_despesa_ids: number[];
}
export interface ContasReceber {
  id: number; descricao: string | null; data_emissao: string; valor_total: number;
  cliente_id: number; ativo: boolean;
  parcelas: (Parcela & { id: number })[]; tipo_receita_ids: number[];
}

// ─── API calls ────────────────────────────────────────────────────────────────
export const api = {
  fornecedores: {
    listar:   (ativo?: boolean) => get<Fornecedor[]>(`/fornecedores${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: Omit<Fornecedor, "id" | "ativo">) => post<Fornecedor>("/fornecedores", d),
    atualizar:(id: number, d: Partial<Fornecedor>)  => put<Fornecedor>(`/fornecedores/${id}`, d),
    inativar: (id: number) => patch<Fornecedor>(`/fornecedores/${id}/inativar`),
    reativar: (id: number) => patch<Fornecedor>(`/fornecedores/${id}/reativar`),
  },
  clientes: {
    listar:   (ativo?: boolean) => get<Cliente[]>(`/clientes${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: Omit<Cliente, "id" | "ativo">) => post<Cliente>("/clientes", d),
    atualizar:(id: number, d: Partial<Cliente>)  => put<Cliente>(`/clientes/${id}`, d),
    inativar: (id: number) => patch<Cliente>(`/clientes/${id}/inativar`),
    reativar: (id: number) => patch<Cliente>(`/clientes/${id}/reativar`),
  },
  faturados: {
    listar:   (ativo?: boolean) => get<Faturado[]>(`/faturados${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: Omit<Faturado, "id" | "ativo">) => post<Faturado>("/faturados", d),
    atualizar:(id: number, d: Partial<Faturado>)  => put<Faturado>(`/faturados/${id}`, d),
    inativar: (id: number) => patch<Faturado>(`/faturados/${id}/inativar`),
    reativar: (id: number) => patch<Faturado>(`/faturados/${id}/reativar`),
  },
  tiposDespesa: {
    listar:   (ativo?: boolean) => get<TipoDespesa[]>(`/tipos-despesa${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: Omit<TipoDespesa, "id" | "ativo">) => post<TipoDespesa>("/tipos-despesa", d),
    atualizar:(id: number, d: Partial<TipoDespesa>)  => put<TipoDespesa>(`/tipos-despesa/${id}`, d),
    inativar: (id: number) => patch<TipoDespesa>(`/tipos-despesa/${id}/inativar`),
    reativar: (id: number) => patch<TipoDespesa>(`/tipos-despesa/${id}/reativar`),
  },
  tiposReceita: {
    listar:   (ativo?: boolean) => get<TipoReceita[]>(`/tipos-receita${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: Omit<TipoReceita, "id" | "ativo">) => post<TipoReceita>("/tipos-receita", d),
    atualizar:(id: number, d: Partial<TipoReceita>)  => put<TipoReceita>(`/tipos-receita/${id}`, d),
    inativar: (id: number) => patch<TipoReceita>(`/tipos-receita/${id}/inativar`),
    reativar: (id: number) => patch<TipoReceita>(`/tipos-receita/${id}/reativar`),
  },
  contasPagar: {
    listar:   (ativo?: boolean) => get<ContasPagar[]>(`/contas-pagar${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: unknown) => post<ContasPagar>("/contas-pagar", d),
    atualizar:(id: number, d: unknown) => put<ContasPagar>(`/contas-pagar/${id}`, d),
    inativar: (id: number) => patch<ContasPagar>(`/contas-pagar/${id}/inativar`),
    reativar: (id: number) => patch<ContasPagar>(`/contas-pagar/${id}/reativar`),
  },
  contasReceber: {
    listar:   (ativo?: boolean) => get<ContasReceber[]>(`/contas-receber${ativo !== undefined ? `?ativo=${ativo}` : ""}`),
    criar:    (d: unknown) => post<ContasReceber>("/contas-receber", d),
    atualizar:(id: number, d: unknown) => put<ContasReceber>(`/contas-receber/${id}`, d),
    inativar: (id: number) => patch<ContasReceber>(`/contas-receber/${id}/inativar`),
    reativar: (id: number) => patch<ContasReceber>(`/contas-receber/${id}/reativar`),
  },
};
