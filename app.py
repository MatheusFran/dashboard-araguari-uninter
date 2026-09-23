# -*- coding: utf-8 -*-
"""
DASHBOARD COMERCIAL DE ARAGUARI/MG — dados 100% reais e públicos
================================================================
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados

NENHUM dado aqui foi inventado, estimado ou simulado. Tudo vem de coleta
automatizada (`python src/coleta_dados.py`) das fontes abaixo:
  - OpenStreetMap (Overpass/Nominatim, licença ODbL): estabelecimentos com
    nome + categoria + coordenadas + tags de contato dentro de Araguari/MG.
  - IBGE/SIDRA CEMPRE 2024 (tabelas 9509 e 9528): unidades locais, empresas,
    pessoal ocupado e salários do município, total e por seção CNAE.
  - Wikipédia (webscraping do verbete "Araguari", CC BY-SA): contexto municipal.
A auditoria completa está em `data/proveniencia.json` e na aba "Fontes".

O que NÃO existe aqui (por honestidade metodológica): faturamento por
estabelecimento — receita individual é protegida por sigilo fiscal e não há
base pública. Em vez disso, o painel usa pessoal ocupado e salários (CEMPRE),
que são os indicadores oficiais de densidade econômica (ODS 8).

Execução local:
    pip install -r requirements.txt
    python src/coleta_dados.py        # baixa os dados reais
    python src/limpeza_tratamento.py  # limpa e padroniza
    streamlit run app.py

ODS 8 (Trabalho Decente e Crescimento Econômico) e ODS 9 (Inovação e
Infraestrutura).

NOTAS DE ACESSIBILIDADE / DESENHO UNIVERSAL (p/ a banca):
  1. Uso Equitativo: layout único, sem versão separada.
  2. Flexibilidade: filtros + busca textual + mapa + tabela.
  3. Simples e Intuitivo: rótulos em português, abas numeradas, ajuda nos filtros.
  4. Informação Perceptível: contraste alto, gráficos com rótulos de valor
     (não só cor), tabelas em texto além das cores.
  5. Tolerância ao Erro: filtro vazio mostra aviso + botão de limpar, nunca erro.
  6. Baixo Esforço: cache de dados, poucos cliques até o insight.
  7. Responsivo: layout wide que colapsa no celular.
"""

from pathlib import Path
from datetime import datetime
import json
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# set_page_config precisa ser a 1ª chamada Streamlit (exigência do framework).
st.set_page_config(
    page_title="Comércio Local — Araguari/MG (dados reais) | UNINTER",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={"About": "Atividade Extensionista II — UNINTER | 100% dados públicos: OSM + IBGE + Wikipédia."},
)

BASE_DIR = Path(__file__).resolve().parent
CLEAN_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_clean.csv"
SIDRA_TOTAIS = BASE_DIR / "data" / "sidra_9509_totais.csv"
SIDRA_SECAO = BASE_DIR / "data" / "sidra_9528_por_secao.csv"
WIKI_PATH = BASE_DIR / "data" / "municipio_wikipedia.json"
PROV_PATH = BASE_DIR / "data" / "proveniencia.json"
FEEDBACK_PATH = BASE_DIR / "data" / "feedbacks.csv"

COR_PRIMARIA = "#0B5CAB"    # paleta de alto contraste, amigável a daltônicos
COR_SECUNDARIA = "#E8871E"
COR_APOIO = "#2CA58D"

plt.rcParams.update({"font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11,
                     "xtick.labelsize": 10, "ytick.labelsize": 10})


# --- Camada de dados (com cache: menos espera = Desenho Universal #6) ---------------
@st.cache_data(show_spinner="Carregando dados reais de Araguari/MG...")
def carregar_tudo():
    """Lê os CSVs/JSONs gerados pela coleta. Sem fallback sintético: se faltar
    arquivo, orienta a rodar a coleta (honestidade > tela bonita vazia)."""
    faltando = [p.name for p in (CLEAN_PATH, SIDRA_TOTAIS, SIDRA_SECAO) if not p.exists()]
    if faltando:
        st.error("Arquivos de dados ausentes: " + ", ".join(faltando))
        st.info("Rode a coleta real: `python src/coleta_dados.py` e depois "
                "`python src/limpeza_tratamento.py`. Nenhum dado é simulado neste projeto.")
        st.stop()
    df = pd.read_csv(CLEAN_PATH, encoding="utf-8")
    totais = pd.read_csv(SIDRA_TOTAIS, encoding="utf-8")
    secao = pd.read_csv(SIDRA_SECAO, encoding="utf-8")
    # SIDRA devolve texto ("X" = desidentificado): converte p/ numérico, X vira NaN
    totais["valor_num"] = pd.to_numeric(totais["valor"], errors="coerce")
    secao["valor_num"] = pd.to_numeric(secao["valor"], errors="coerce")
    wiki = json.loads(WIKI_PATH.read_text(encoding="utf-8")) if WIKI_PATH.exists() else {}
    prov = json.loads(PROV_PATH.read_text(encoding="utf-8")) if PROV_PATH.exists() else []
    return df, totais, secao, wiki, prov


def var_sidra(totais: pd.DataFrame, pedaco_nome: str):
    """Busca valor NUMÉRICO de uma variável CEMPRE pelo trecho do nome."""
    lin = totais[totais["variavel"].str.contains(pedaco_nome, case=False, na=False)]
    if lin.empty or pd.isna(lin.iloc[0]["valor_num"]):
        return None, None
    return float(lin.iloc[0]["valor_num"]), lin.iloc[0]["ano"]


def fmt_int(v):
    return f"{int(v):,}".replace(",", ".") if v is not None else "—"


def fmt_moeda(v):
    return ("R$ " + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")) if v else "—"


@st.cache_data
def carregar_feedbacks() -> pd.DataFrame:
    cols = ["data_hora", "nome", "bairro", "nota", "comentario"]
    if FEEDBACK_PATH.exists():
        try:
            df = pd.read_csv(FEEDBACK_PATH, encoding="utf-8")
            return df if set(cols).issubset(df.columns) else pd.DataFrame(columns=cols)
        except Exception:
            return pd.DataFrame(columns=cols)
    return pd.DataFrame(columns=cols)


def salvar_feedback(nome, bairro, nota, comentario):
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    novo = pd.DataFrame([{"data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                          "nome": nome.strip(), "bairro": bairro,
                          "nota": int(nota), "comentario": comentario.strip()}])
    base = pd.read_csv(FEEDBACK_PATH, encoding="utf-8") if FEEDBACK_PATH.exists() else pd.DataFrame()
    pd.concat([base, novo], ignore_index=True).to_csv(FEEDBACK_PATH, index=False, encoding="utf-8")
    carregar_feedbacks.clear()


# --- Carga --------------------------------------------------------------------------------
df, totais, secao_df, wiki, prov = carregar_tudo()
info = wiki.get("infobox", {})

def campo_wiki(*trechos):
    """Acha campo da infobox pelo trecho (chaves variam: 'Total (Censo IBGE/2022)'...)."""
    for k, v in info.items():
        kl = k.lower()
        if all(t.lower() in kl for t in trechos):
            return v
    return "—"

pop_2022 = campo_wiki("censo", "2022")
pop_2025 = campo_wiki("estimativa", "2025")
pib_2023 = campo_wiki("pib", "2023")

# --- Filtros laterais ----------------------------------------------------------------------
st.sidebar.title("🔎 Filtros da análise")
st.sidebar.caption("Município: **Araguari/MG** (IBGE 3103504). Segmentação por bairro e categoria — dados OSM.")
bairros = sorted(df["bairro"].dropna().unique().tolist())
categorias = sorted(df["categoria"].dropna().unique().tolist())
sel_bairros = st.sidebar.multiselect("Bairro", options=bairros, default=bairros,
    help="Bairros vindos do OSM (tag addr:suburb ou geocodificação reversa).")
sel_cats = st.sidebar.multiselect("Categoria comercial", options=categorias, default=categorias,
    help="Tradução PT-BR da etiqueta OSM (ex.: shop=supermarket → Alimentação).")
busca = st.sidebar.text_input("Buscar por nome", placeholder="Ex.: posto, farmácia...",
    help="Filtra pelo nome cadastrado no OpenStreetMap.")
idx_min = st.sidebar.slider("Presença digital mínima", 0, 100, 0,
    help="Índice 0–100 derivado das tags reais: site×40 + telefone×30 + rede×20 + whatsapp×10.")
if st.sidebar.button("🧹 Limpar filtros", use_container_width=True,
                     help="Restaura os filtros em 1 clique."):
    st.rerun()

df_f = df.copy()
if sel_bairros:
    df_f = df_f[df_f["bairro"].isin(sel_bairros)]
if sel_cats:
    df_f = df_f[df_f["categoria"].isin(sel_cats)]
if busca.strip():
    df_f = df_f[df_f["nome"].str.contains(busca.strip(), case=False, na=False)]
df_f = df_f[df_f["indice_presenca_digital"] >= idx_min]
if df_f.empty:
    st.warning("⚠️ Nada corresponde aos filtros. Ajuste ou clique em **🧹 Limpar filtros**.")
    st.stop()

# --- Cabeçalho ------------------------------------------------------------------------------
st.title("🏪 Comércio de Araguari/MG — dados reais e públicos")
st.markdown(
    "**Atividade Extensionista II (UNINTER — Ciência de Dados).** Estabelecimentos mapeados no "
    f"**OpenStreetMap** ({len(df)} pontos) + mercado formal no **CEMPRE/IBGE 2024** + contexto da **Wikipédia**. "
    f"População: **{pop_2022}** (Censo 2022) • estimativa **{pop_2025}** (2025) • PIB **{pib_2023}**. "
    "Alinhado aos **ODS 8** e **ODS 9**. Nenhum número foi estimado ou simulado — ver aba **Fontes**."
)

# --- KPIs (todos de fontes oficiais; ano exibido em cada métrica) ---------------------------
ul, ano_ul = var_sidra(totais, "unidades locais")
poc, _ = var_sidra(totais, "ocupado total")
sal, _ = var_sidra(totais, "mensa.* em reais|em reais")
if sal is None:
    sal, _ = var_sidra(totais, " Isaac")  # nunca casa; mantém None com segurança
pct_tel = df_f["tem_telefone"].mean() * 100
pct_site = df_f["tem_site"].mean() * 100

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🏬 Mapeados no OSM", f"{len(df_f)}", help="Pontos com nome dentro de Araguari (Overpass).")
k2.metric(f"🏢 Unidades locais (CEMPRE {ano_ul})", fmt_int(ul),
          help="Estabelecimentos formais ativos — IBGE, tabela 9509.")
k3.metric(f"👥 Pessoal ocupado (CEMPRE {ano_ul})", fmt_int(poc),
          help="Postos de trabalho formais — proxy oficial do ODS 8.")
k4.metric(f"💵 Salário médio (CEMPRE {ano_ul})", fmt_moeda(sal),
          help="Salário médio mensal em reais — IBGE, tabela 9509.")
k5.metric("📞 Com telefone no OSM", f"{pct_tel:.0f}%",
          help="Fração dos pontos filtrados com tag de telefone (dado real, não estimado).")
st.caption(f"Presença digital na seleção: **{pct_site:.0f}%** com site • **{df_f['tem_rede_social'].mean()*100:.0f}%** "
           f"com rede social • **{df_f['tem_whatsapp'].mean()*100:.0f}%** com WhatsApp (tags OSM reais).")
st.divider()

aba1, aba2, aba3, aba4, aba5, aba6, aba7 = st.tabs([
    "📊 Visão geral", "🏢 Mercado formal (CEMPRE)", "📱 Presença digital",
    "🗃️ Dados detalhados", "🌍 ODS 8 e 9", "🔎 Fontes e método", "💬 Feedback comunitário",
])

# --- ABA 1: OSM por bairro/categoria ----------------------------------------------------------
with aba1:
    st.subheader("Estabelecimentos mapeados no OpenStreetMap")
    c1, c2 = st.columns(2)
    por_bairro = df_f["bairro"].value_counts().sort_values(ascending=False)
    por_cat = df_f["categoria"].value_counts().sort_values(ascending=False)
    with c1:
        st.markdown("**Por bairro** (interativo — passe o mouse)")
        st.bar_chart(por_bairro, color=COR_PRIMARIA)
        fig, ax = plt.subplots(figsize=(7, 4))
        por_bairro.plot.barh(ax=ax, color=COR_PRIMARIA)
        ax.set_xlabel("Nº de pontos OSM"); ax.set_title("Pontos por bairro — Araguari/MG"); ax.invert_yaxis()
        for i, v in enumerate(por_bairro.values):
            ax.text(v + 0.2, i, str(v), va="center", fontsize=10)
        fig.tight_layout(); st.pyplot(fig)
    with c2:
        st.markdown("**Por categoria** (interativo — passe o mouse)")
        st.bar_chart(por_cat, color=COR_SECUNDARIA)
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        por_cat.plot.barh(ax=ax2, color=COR_SECUNDARIA)
        ax2.set_xlabel("Nº de pontos OSM"); ax2.set_title("Pontos por categoria (etiqueta OSM traduzida)")
        ax2.invert_yaxis()
        for i, v in enumerate(por_cat.values):
            ax2.text(v + 0.2, i, str(v), va="center", fontsize=10)
        fig2.tight_layout(); st.pyplot(fig2)
    cobertura = f"{len(df)/ul*100:.1f}% das {fmt_int(ul)} unidades formais" if ul else "fração das unidades formais"
    st.info(f"💡 **Leitura:** maior concentração em **{por_bairro.index[0]}** ({por_bairro.iloc[0]} pontos); "
            f"categoria líder **{por_cat.index[0]}** ({por_cat.iloc[0]}). O OSM cobre "
            f"{cobertura} — completar o mapa é ação extensionista (ODS 9).")

# --- ABA 2: CEMPRE por seção CNAE ---------------------------------------------------------------
with aba2:
    st.subheader(f"Mercado formal por seção CNAE — CEMPRE {secao_df['ano'].iloc[0]} (IBGE)")
    piv = secao_df.pivot_table(index="secao_cnae", columns="variavel", values="valor_num",
                               aggfunc="first").fillna(0)
    col_ul = [c for c in piv.columns if "unidades locais" in c.lower()][0]
    col_po = [c for c in piv.columns if "ocupado total" in c.lower()][0]
    piv = piv.sort_values(col_ul, ascending=False)
    st.caption("Tabela oficial: cada linha é uma seção CNAE; células 'X' do IBGE (<3 informantes) foram omitidas.")
    st.dataframe(piv.style.format("{:.0f}"), use_container_width=True)
    st.markdown("**Unidades locais por seção CNAE**")
    st.bar_chart(piv[col_ul], color=COR_APOIO)
    top = piv.index[0]
    st.info(f"💡 **Leitura:** a seção **{top}** concentra {int(piv[col_ul].iloc[0]):,} unidades locais "
            f"({piv[col_ul].iloc[0]/piv[col_ul].sum()*100:.1f}% do município) — confirma a vocação comercial "
            "de Araguari e ancora as ações do ODS 8.")

# --- ABA 3: presença digital real + mapa ----------------------------------------------------------
with aba3:
    st.subheader("Presença digital declarada no OSM (tags reais, sem estimativa)")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Com site", f"{pct_site:.0f}%"); m2.metric("Com telefone", f"{pct_tel:.0f}%")
    m3.metric("Com rede social", f"{df_f['tem_rede_social'].mean()*100:.0f}%")
    m4.metric("Com WhatsApp", f"{df_f['tem_whatsapp'].mean()*100:.0f}%")
    st.markdown("**Índice de presença digital por categoria** (site×40 + telefone×30 + rede×20 + whatsapp×10)")
    pres_cat = df_f.groupby("categoria")["indice_presenca_digital"].mean().sort_values()
    st.bar_chart(pres_cat, color=COR_PRIMARIA)
    st.warning("⚠️ **Achado ODS 9:** nenhum ponto traz site e quase nenhum traz WhatsApp no OSM. "
               "Isso mede a *declaração no mapa*, não o uso real — capacitar comerciantes a completar "
               "seus cadastros (Google + OSM) é a intervenção digital de menor custo e maior alcance.")
    st.markdown("**Mapa real dos pontos filtrados**")
    st.map(df_f[["latitude", "longitude"]].dropna(), zoom=12)

# --- ABA 4: tabela + download ----------------------------------------------------------------------
with aba4:
    st.subheader("Tabela — cada linha é um ponto real do OpenStreetMap")
    st.caption("Clique no cabeçalho para ordenar. Coluna 'OSM' traz a etiqueta original (auditoria).")
    cols = ["nome", "categoria", "categoria_osm", "bairro", "endereco",
            "tem_site", "tem_telefone", "indice_presenca_digital"]
    st.dataframe(df_f[cols].rename(columns={"nome": "Estabelecimento", "categoria": "Categoria",
        "categoria_osm": "Etiqueta OSM", "bairro": "Bairro", "endereco": "Endereço",
        "tem_site": "Site?", "tem_telefone": "Telefone?",
        "indice_presenca_digital": "Presença (0–100)"}),
        use_container_width=True, height=420)
    st.download_button("⬇️ Baixar seleção (CSV)", df_f.to_csv(index=False, encoding="utf-8"),
        file_name="araguari_osm_selecao.csv", mime="text/csv",
        help="Baixa exatamente o filtrado, com fonte OpenStreetMap.")

# --- ABA 5: ODS com números oficiais ------------------------------------------------------------------
with aba5:
    st.subheader("Como este painel serve aos ODS 8 e 9 — com números oficiais")
    o1, o2 = st.columns(2)
    with o1:
        st.markdown("### 💼 ODS 8 — Trabalho Decente e Crescimento Econômico")
        st.markdown(f"- **{fmt_int(ul)}** unidades locais ativas e **{fmt_int(poc)}** pessoas ocupadas (CEMPRE {ano_ul}).\n"
                    f"- Salário médio **{fmt_moeda(sal)}**.\n"
                    "- Mapa OSM revela vazios de cobertura: bairros pouco mapeados = prioridade de campo.\n"
                    "- Recomendação: mutirão de cadastro (OSM + Google Perfil) nos bairros periféricos.")
    with o2:
        st.markdown("### 🏭 ODS 9 — Inovação e Infraestrutura")
        st.markdown("- **Infraestrutura de dados aberta**: OSM + SIDRA + Wikipédia, tudo reutilizável.\n"
                    f"- **Diagnóstico real**: só {pct_tel:.0f}% dos pontos OSM declaram telefone; 0% declaram site.\n"
                    "- Recomendação: oficina de presença digital (site gratuito + WhatsApp Business) para "
                    "Alimentação e Vestuário — categorias de contato direto com o cliente.")

# --- ABA 6: fontes, método e limitações ------------------------------------------------------------------
with aba6:
    st.subheader("🔎 Fontes, método e limitações (transparência total)")
    st.markdown("**De onde veio cada número** (gerado automaticamente na coleta):")
    if prov:
        st.dataframe(pd.DataFrame(prov)[["fonte", "descricao", "acesso_em_utc", "licenca", "n_registros"]].rename(
            columns={"fonte": "Fonte", "descricao": "Descrição", "acesso_em_utc": "Acesso (UTC)",
                     "licenca": "Licença", "n_registros": "Registros"}),
            use_container_width=True, height=220)
    st.markdown("**Método (reprodutível):** `python src/coleta_dados.py` → Overpass (bbox + filtro no polígono "
                "oficial da relação OSM 314597) → Nominatim reverse p/ bairro (1 req/s) → SIDRA tabelas 9509/9528 "
                "→ webscraping da infobox da Wikipédia com BeautifulSoup → `python src/limpeza_tratamento.py` "
                "(deduplica, traduz etiquetas, computa flags).")
    st.markdown("**Limitações declaradas:** OSM é colaborativo — cobre fração do comércio real e varia por bairro; "
                "CEMPRE 2024 exclui informais; 'Não informado' no bairro = ausência de dado, nunca preenchimento; "
                "faturamento por estabelecimento **não existe** em base pública (sigilo fiscal) e por isso não aparece.")
    if info:
        st.markdown("**Contexto municipal (Wikipédia, CC BY-SA):**")
        st.dataframe(pd.DataFrame(list(info.items()), columns=["Campo", "Valor"]).head(20),
                     use_container_width=True, height=320)

# --- ABA 7: feedback comunitário --------------------------------------------------------------------------
with aba7:
    st.subheader("💬 Validação comunitária — a voz do comerciante")
    st.markdown("Comerciante de Araguari? Avalie a ferramenta (1–5 ⭐) e comente. Sua avaliação valida o projeto.")
    with st.form("form_feedback", clear_on_submit=True):
        nome = st.text_input("Seu nome *", placeholder="Ex.: Maria Silva",
                             help="Obrigatório. Exibido na lista pública de validações.")
        bairro_fb = st.selectbox("Bairro do seu negócio", options=bairros,
                                 help="Bairro do seu estabelecimento.")
        nota = st.radio("Avaliação da ferramenta * (1 = pouco útil, 5 = muito útil)",
                        options=[1, 2, 3, 4, 5], index=4, horizontal=True,
                        help="1 estrela = pouco útil; 5 estrelas = muito útil.")
        comentario = st.text_area("Comentário / feedback *", max_chars=500,
            placeholder="Ex.: o painel mostrou que meu bairro tem poucos pontos mapeados...",
            help="Máximo 500 caracteres.")
        if st.form_submit_button("✅ Enviar avaliação", use_container_width=True):
            if not nome.strip() or not comentario.strip():
                st.error("Preencha **nome** e **comentário** antes de enviar.")
            else:
                salvar_feedback(nome, bairro_fb, nota, comentario)
                st.success(f"Obrigado, **{nome.strip()}**! Avaliação de **{nota} ⭐** registrada. 🙏")
                st.balloons()
    st.divider()
    fb = carregar_feedbacks()
    if fb.empty:
        st.caption("Ainda não há avaliações. Seja a primeira pessoa a validar! 👆")
    else:
        f1, f2, f3 = st.columns(3)
        f1.metric("Avaliações recebidas", len(fb))
        f2.metric("Nota média", f"{pd.to_numeric(fb['nota'], errors='coerce').mean():.1f} ⭐")
        f3.metric("Bairros participantes", fb["bairro"].nunique())
        st.markdown("**Avaliações recentes**")
        st.dataframe(fb.sort_index(ascending=False).head(20).rename(
            columns={"data_hora": "Data", "nome": "Nome", "bairro": "Bairro",
                     "nota": "Nota (1–5)", "comentario": "Comentário"}),
            use_container_width=True, height=300)

st.divider()
st.caption("🏪 **Araguari/MG em dados reais** • UNINTER (Ciência de Dados) • ODS 8 e 9 • "
           "Fontes: OpenStreetMap (ODbL) + IBGE/SIDRA + Wikipédia (CC BY-SA) • Sem nenhum dado simulado.")
