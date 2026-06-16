"""
seed_data.py — Popula o banco com 200 notas fiscais de exemplo.

Execução:
    python seed_data.py

O script usa a mesma DATABASE_URL do .env, respeita as FKs e
cria todas as tabelas auxiliares primeiro (fornecedores, clientes,
faturados, tipos de despesa e receita).
"""

import random
from datetime import date, timedelta
from database import Base, SessionLocal, engine
from models import (
    Fornecedor, Cliente, Faturado,
    TipoDespesa, TipoReceita,
    ContasPagar, ParcelaPagar, ClassificacaoPagar,
    ContasReceber, ParcelaReceber, ClassificacaoReceber,
)

# ─── Dados mestres ────────────────────────────────────────────────────────────

FORNECEDORES = [
    ("Tech Supplies Ltda",          "Tech Supplies",      "12.345.678/0001-90"),
    ("Papelaria Central S.A.",       "Papelaria Central",  "23.456.789/0001-01"),
    ("Gráfica & Print Eireli",       "Gráfica Print",      "34.567.890/0001-12"),
    ("Logística Express ME",         "Log Express",        "45.678.901/0001-23"),
    ("Serv. Limpeza Brilho Ltda",    "Brilho",             "56.789.012/0001-34"),
    ("Energia Solar Sul S.A.",       "Solar Sul",          "67.890.123/0001-45"),
    ("Consultoria TI Plus Ltda",     "TI Plus",            "78.901.234/0001-56"),
    ("Distribuidora Alfa ME",        "Dist. Alfa",         "89.012.345/0001-67"),
    ("Manutenção Predial Norte",     "Manutenção Norte",   "90.123.456/0001-78"),
    ("Telecomunicações Beta S.A.",   "Telecom Beta",       "01.234.567/0001-89"),
    ("Catering Gourmet Ltda",        "Catering Gourmet",   "11.222.333/0001-44"),
    ("Seguros Confiança S.A.",       "Seguros Conf.",      "22.333.444/0001-55"),
    ("Mobília Escritório Ltda",      "Mobília ERP",        "33.444.555/0001-66"),
    ("Água & Higiene ME",            "Água Higiene",       "44.555.666/0001-77"),
    ("Marketing Digital Cia",        "Mkt Digital",        "55.666.777/0001-88"),
]

CLIENTES = [
    ("Indústrias Omega Ltda",    "07.654.321/0001-10", "omega@omega.com.br",    "(11) 99000-0001"),
    ("Comércio Delta S.A.",      "08.765.432/0001-21", "delta@delta.com.br",    "(21) 98000-0002"),
    ("Hospital São Lucas",       "09.876.543/0001-32", "fin@slucas.com.br",     "(51) 97000-0003"),
    ("Escola Futuro Ltda",       "10.987.654/0001-43", "pagto@futuro.edu.br",   "(41) 96000-0004"),
    ("Varejo Expresso ME",       "11.098.765/0001-54", "varejo@expresso.com",   "(31) 95000-0005"),
    ("Construtora Ágil S.A.",    "12.109.876/0001-65", "cia@agil.com.br",       "(61) 94000-0006"),
    ("Fazenda Verde ME",         "13.210.987/0001-76", "faz@verde.agro.br",     "(64) 93000-0007"),
    ("Supermercado BomPreço",    "14.321.098/0001-87", "cfo@bompreco.com.br",   "(71) 92000-0008"),
    ("Clínica Bem Estar Ltda",   "15.432.109/0001-98", "fin@bemstar.med.br",    "(85) 91000-0009"),
    ("Transportes Rápido S.A.",  "16.543.210/0001-09", "pagto@rapido.com.br",   "(62) 90000-0010"),
    ("Padaria & Confeit. Lima",  "17.654.321/0001-20", "lima@padarialima.com",  "(11) 89000-0011"),
    ("Auto Peças Mota Ltda",     "18.765.432/0001-31", "fin@motaap.com.br",     "(31) 88000-0012"),
    ("Livraria Cultura ME",      "19.876.543/0001-42", "cfo@livcultura.com",    "(11) 87000-0013"),
    ("Academia Força Total",     "20.987.654/0001-53", "acad@forcatotal.com",   "(21) 86000-0014"),
    ("Farmácia Saúde Certa",     "21.098.765/0001-64", "cfo@saudecerta.com",    "(41) 85000-0015"),
]

FATURADOS = [
    ("Ana Paula Ferreira",   "111.222.333-44"),
    ("Carlos Eduardo Lima",  "222.333.444-55"),
    ("Fernanda Oliveira",    "333.444.555-66"),
    ("Gustavo Henrique",     "444.555.666-77"),
    ("Isabela Rodrigues",    "555.666.777-88"),
]

TIPOS_DESPESA = [
    ("INSUMOS AGRÍCOLAS",          "Sementes, fertilizantes, defensivos agrícolas e corretivos"),
    ("MANUTENÇÃO E OPERAÇÃO",      "Peças, combustíveis, ferramentas e manutenção de equipamentos"),
    ("RECURSOS HUMANOS",           "Salários, encargos e contratação de mão de obra temporária"),
    ("SERVIÇOS OPERACIONAIS",      "Colheita terceirizada, secagem, frete e pulverização"),
    ("INFRAESTRUTURA E UTILIDADES", "Energia elétrica, arrendamento, construções e materiais"),
    ("ADMINISTRATIVAS",            "Honorários advocatícios/contábeis e tarifas bancárias"),
    ("SEGUROS E PROTEÇÃO",         "Seguro agrícola, seguro de ativos e seguro prestamista"),
    ("IMPOSTOS E TAXAS",           "Impostos (ITR, IPVA, IPTU) e taxas e emolumentos do INCRA"),
    ("INVESTIMENTOS",              "Aquisição de terras, veículos, máquinas e benfeitorias"),
]

TIPOS_RECEITA = [
    ("Venda de Produtos",      "Receita proveniente da venda de mercadorias"),
    ("Prestação de Serviços",  "Receita de serviços prestados"),
    ("Aluguel Recebido",       "Receita de locação de imóveis"),
    ("Consultoria",            "Honorários de consultoria"),
    ("Assinatura Mensal",      "Planos e assinaturas recorrentes"),
    ("Licenciamento",          "Receita de licenças de software ou marca"),
    ("Comissões",              "Comissões sobre vendas"),
    ("Doações",                "Doações recebidas"),
    ("Juros Recebidos",        "Rendimentos financeiros"),
    ("Serviços Educacionais",  "Cursos, treinamentos e workshops"),
]

AGRICULTURAL_DESPESAS = {
    "INSUMOS AGRÍCOLAS": [
        "Compra de sementes (soja, milho, algodão) para o plantio",
        "Aquisição de fertilizantes, adubo e corretivos de solo NPK",
        "Defensivos agrícolas, pesticidas e herbicidas para controle de pragas",
        "Corretivos de solo e calcário para preparo e calagem da terra"
    ],
    "MANUTENÇÃO E OPERAÇÃO": [
        "Compra de combustíveis (óleo diesel) e lubrificantes para tratores",
        "Aquisição de peças, parafusos e componentes mecânicos para tratores",
        "Serviço de manutenção preventiva e corretiva de máquinas e colheitadeiras",
        "Substituição de pneus, filtros e correias de máquinas agrícolas",
        "Compra de ferramentas de oficina e utensílios gerais de manutenção"
    ],
    "RECURSOS HUMANOS": [
        "Contratação de mão de obra temporária para colheita/safra",
        "Pagamento de salários, encargos sociais e trabalhistas dos funcionários"
    ],
    "SERVIÇOS OPERACIONAIS": [
        "Frete e transporte de grãos colhidos e insumos até a fazenda",
        "Serviço de colheita terceirizada de grãos no período da safra",
        "Serviço de secagem e armazenagem de grãos em cooperativa/silo",
        "Pulverização aérea e aplicação terceirizada de defensivos agrícolas"
    ],
    "INFRAESTRUTURA E UTILIDADES": [
        "Fatura de energia elétrica das instalações, poços artesianos e pivôs",
        "Pagamento de arrendamento de terras agrícolas para cultivo",
        "Serviços de construções e reformas nos galpões e alojamentos da fazenda",
        "Compra de materiais de construção para cercas, porteiras e valas"
    ],
    "ADMINISTRATIVAS": [
        "Pagamento de honorários contábeis, advocatícios e assessoria agronômica",
        "Tarifas bancárias, juros de custeio e despesas financeiras administrativas"
    ],
    "SEGUROS E PROTEÇÃO": [
        "Prêmio de seguro agrícola para proteção da lavoura contra intempéries",
        "Seguro de ativos corporativos (máquinas, tratores, colheitadeiras e veículos)",
        "Seguro prestamista associado a financiamento rural"
    ],
    "IMPOSTOS E TAXAS": [
        "Guia de pagamento de impostos municipais/federais (ITR, IPTU, IPVA)",
        "Taxas de regularização ambiental e emolumentos do INCRA-CCIR"
    ],
    "INVESTIMENTOS": [
        "Compra de novas máquinas agrícolas, tratores e implementos modernos",
        "Compra de veículos utilitários e caminhonetes para suporte na fazenda",
        "Aquisição de novos imóveis rurais e expansão de terras cultiváveis",
        "Investimento em melhorias de infraestrutura rural e barracões"
    ]
}

# ─── Helpers ──────────────────────────────────────────────────────────────────

def rand_date(start_year: int = 2024, end_year: int = 2025) -> date:
    start = date(start_year, 1, 1)
    end   = date(end_year, 12, 31)
    return start + timedelta(days=random.randint(0, (end - start).days))


def make_parcelas_pagar(conta_id: int, valor_total: float, n: int, base_date: date):
    parcela_valor = round(valor_total / n, 2)
    parcelas = []
    for i in range(1, n + 1):
        venc = base_date + timedelta(days=30 * i)
        parcelas.append(ParcelaPagar(
            conta_id        = conta_id,
            numero          = i,
            data_vencimento = venc,
            valor           = parcela_valor,
            pago            = random.choice([True, False]),
        ))
    return parcelas


def make_parcelas_receber(conta_id: int, valor_total: float, n: int, base_date: date):
    parcela_valor = round(valor_total / n, 2)
    parcelas = []
    for i in range(1, n + 1):
        venc = base_date + timedelta(days=30 * i)
        parcelas.append(ParcelaReceber(
            conta_id        = conta_id,
            numero          = i,
            data_vencimento = venc,
            valor           = parcela_valor,
            recebido        = random.choice([True, False]),
        ))
    return parcelas


DESCRICOES_RECEBER = [
    "Venda de produtos conforme pedido {nf}",
    "Prestação de serviços de consultoria — projeto {nf}",
    "Mensalidade de assinatura — plano {plano}",
    "Aluguel de espaço comercial — {mes}/{ano}",
    "Licença de uso de plataforma — {mes}/{ano}",
    "Comissão sobre vendas realizadas no período",
    "Curso de capacitação profissional — turma {nf}",
    "Serviços de desenvolvimento de software — fase {nf}",
    "Fornecimento de produtos conforme contrato",
    "Honorários de consultoria financeira",
    "Venda de equipamentos usados",
    "Receita de eventos e workshops",
    "Serviços de auditoria externa",
    "Receita de licenciamento de marca",
    "Serviços de treinamento corporativo — grupo {nf}",
]

MESES = ["Jan","Fev","Mar","Abr","Mai","Jun","Jul","Ago","Set","Out","Nov","Dez"]

def fmt_desc(template: str, i: int) -> str:
    mes  = MESES[i % 12]
    ano  = 2024 + (i // 12) % 2
    return (template
            .replace("{mes}", mes)
            .replace("{ano}", str(ano))
            .replace("{nf}",  str(1000 + i))
            .replace("{plano}", random.choice(["Basic","Pro","Enterprise"])))


# ─── Main ─────────────────────────────────────────────────────────────────────

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Limpeza inicial ──────────────────────────────────────────────────
        print("Limpando dados anteriores...")
        db.query(ClassificacaoPagar).delete()
        db.query(ClassificacaoReceber).delete()
        db.query(ParcelaPagar).delete()
        db.query(ParcelaReceber).delete()
        db.query(ContasPagar).delete()
        db.query(ContasReceber).delete()
        db.query(Fornecedor).delete()
        db.query(Cliente).delete()
        db.query(Faturado).delete()
        db.query(TipoDespesa).delete()
        db.query(TipoReceita).delete()
        db.commit()

        # ── 1. Cadastros auxiliares ──────────────────────────────────────────

        print("Inserindo fornecedores...")
        forn_objs = []
        for razao, fantasia, cnpj in FORNECEDORES:
            existing = db.query(Fornecedor).filter_by(cnpj=cnpj).first()
            if not existing:
                f = Fornecedor(razao_social=razao, fantasia=fantasia, cnpj=cnpj)
                db.add(f)
                forn_objs.append(f)
            else:
                forn_objs.append(existing)
        db.flush()

        print("Inserindo clientes...")
        cli_objs = []
        for nome, cpf_cnpj, email, tel in CLIENTES:
            existing = db.query(Cliente).filter_by(cpf_cnpj=cpf_cnpj).first()
            if not existing:
                c = Cliente(nome=nome, cpf_cnpj=cpf_cnpj, email=email, telefone=tel)
                db.add(c)
                cli_objs.append(c)
            else:
                cli_objs.append(existing)
        db.flush()

        print("Inserindo faturados...")
        fat_objs = []
        for nome_c, cpf in FATURADOS:
            existing = db.query(Faturado).filter_by(cpf=cpf).first()
            if not existing:
                ft = Faturado(nome_completo=nome_c, cpf=cpf)
                db.add(ft)
                fat_objs.append(ft)
            else:
                fat_objs.append(existing)
        db.flush()

        print("Inserindo tipos de despesa...")
        td_objs = []
        for nome, desc in TIPOS_DESPESA:
            existing = db.query(TipoDespesa).filter_by(nome=nome).first()
            if not existing:
                td = TipoDespesa(nome=nome, descricao=desc)
                db.add(td)
                td_objs.append(td)
            else:
                td_objs.append(existing)
        db.flush()

        print("Inserindo tipos de receita...")
        tr_objs = []
        for nome, desc in TIPOS_RECEITA:
            existing = db.query(TipoReceita).filter_by(nome=nome).first()
            if not existing:
                tr = TipoReceita(nome=nome, descricao=desc)
                db.add(tr)
                tr_objs.append(tr)
            else:
                tr_objs.append(existing)
        db.flush()

        # ── 2. 100 Contas a Pagar ────────────────────────────────────────────

        print("Inserindo 100 contas a pagar...")
        for i in range(100):
            valor        = round(random.uniform(150.0, 25000.0), 2)
            emissao      = rand_date()
            num_parcelas = random.choice([1, 1, 1, 2, 3, 4, 6, 12])
            fornecedor   = random.choice(forn_objs)
            faturado     = random.choice(fat_objs) if random.random() > 0.3 else None
            num_nf       = f"NF-{10000 + i:05d}"

            # Seleciona o tipo de despesa primeiro para alinhar a descrição
            tipo_despesa_escolhido = random.choice(td_objs)
            desc_opcoes = AGRICULTURAL_DESPESAS.get(tipo_despesa_escolhido.nome, ["Despesa operacional geral da fazenda"])
            desc_base = random.choice(desc_opcoes)
            
            mes = MESES[i % 12]
            ano = 2024 + (i // 12) % 2
            descricao_final = f"{desc_base} — Ref. {mes}/{ano}"

            cp = ContasPagar(
                numero_nf    = num_nf,
                data_emissao = emissao,
                descricao    = descricao_final,
                valor_total  = valor,
                fornecedor_id= fornecedor.id,
                faturado_id  = faturado.id if faturado else None,
                ativo        = True,
            )
            db.add(cp)
            db.flush()

            # parcelas
            for p in make_parcelas_pagar(cp.id, valor, num_parcelas, emissao):
                db.add(p)

            # classificação correspondente
            db.add(ClassificacaoPagar(conta_id=cp.id, tipo_despesa_id=tipo_despesa_escolhido.id))
            
            # Ocasionalmente adiciona uma segunda classificação relacionada
            if random.random() > 0.8:
                outro_tipo = random.choice([t for t in td_objs if t.id != tipo_despesa_escolhido.id])
                db.add(ClassificacaoPagar(conta_id=cp.id, tipo_despesa_id=outro_tipo.id))

        db.flush()

        # ── 3. 100 Contas a Receber ──────────────────────────────────────────

        print("Inserindo 100 contas a receber...")
        for i in range(100):
            valor        = round(random.uniform(200.0, 50000.0), 2)
            emissao      = rand_date()
            num_parcelas = random.choice([1, 1, 1, 2, 3, 4, 6, 12])
            cliente      = random.choice(cli_objs)
            desc_tmpl    = DESCRICOES_RECEBER[i % len(DESCRICOES_RECEBER)]

            cr = ContasReceber(
                descricao    = fmt_desc(desc_tmpl, i),
                data_emissao = emissao,
                valor_total  = valor,
                cliente_id   = cliente.id,
                ativo        = True,
            )
            db.add(cr)
            db.flush()

            # parcelas
            for p in make_parcelas_receber(cr.id, valor, num_parcelas, emissao):
                db.add(p)

            # classificações (1 ou 2 tipos de receita)
            tipos_escolhidos = random.sample(tr_objs, k=random.choice([1, 1, 2]))
            for tr in tipos_escolhidos:
                db.add(ClassificacaoReceber(conta_id=cr.id, tipo_receita_id=tr.id))

        db.flush()

        db.commit()
        print("\n✅ Seed concluído com sucesso!")
        print("   • 15 Fornecedores")
        print("   • 15 Clientes")
        print("   •  5 Faturados")
        print("   •  9 Tipos de Despesa")
        print("   • 10 Tipos de Receita")
        print("   •100 Contas a Pagar  (com parcelas e classificações)")
        print("   •100 Contas a Receber (com parcelas e classificações)")
        print("   ─────────────────────────────────────────────────────")
        print("   Total de notas: 200")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Erro durante o seed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
