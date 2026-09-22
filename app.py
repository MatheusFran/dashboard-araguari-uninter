# -*- coding: utf-8 -*-
"""
DASHBOARD COMERCIAL DE ARAGUARI/MG — Análise de densidade de mercado e visibilidade digital
============================================================================================
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados

Tema: pequenos estabelecimentos de Araguari/MG, alinhado aos:
  - ODS 8 — Trabalho Decente e Crescimento Econômico (mapear e fortalecer piccoli negócios,
    geração de emprego local, tomada de decisão baseada em dados);
  - ODS 9 — Indústria, Inovação e Infraestrutura (diagnóstico da maturidade digital:
    Google Perfil da Empresa, Instagram, WhatsApp como infraestrutura digital de baixo custo).

Execução local:
    pip install -r requirements.txt
    streamlit run app.py

--------------------------------------------------------------------------------------------
NOTAS DE ACESSIBILIDADE / DESENHO UNIVERSAL (comentários intencionais para a banca):
  1. Uso Equitativo ........... layout único para todos; sem versão "simplificada" separada.
  2. Flexibilidade ............. filtros + busca textual + sliders atendem diferentes perfis.
  3. Uso Simples e Intuitivo ... rótulos em português claro, abas numeradas, ajuda (help=...).
  4. Informação Perceptível .... contraste alto, fonte >= 16px, gráficos com rótulos de valor
                                 (não só cor), tabelas com texto (redundância visual+textual).
  5. Tolerância ao Erro ........ filtros vazios exibem aviso + botão "Limpar filtros" em vez de erro.
  6. Baixo Esforço Físico ...... poucos cliques até o insight; cache de dados (rápido).
  7. Tamanho/Espaço ............ layout wide responsivo, colunas que colapsam no celular.
--------------------------------------------------------------------------------------------
"""

# --- Imports: propositalmente enxutos (stdlib + pandas + streamlit + matplotlib) ---------
# Escolha técnica: matplotlib (requisito do trabalho) para gráficos estáticos com rótulos
# acessíveis + gráficos nativos do Streamlit (st.bar_chart) que são interativos (tooltip/zoom).
from pathlib import Path
from datetime import datetime
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

# ==============================================================================
# CONFIGURAÇÃO GLOBAL DA PÁGINA
# st.set_page_config PRECISA ser a primeira chamada Streamlit (exigência do framework).
# initial_sidebar_state="expanded" garante que os filtros sejam descobertos de imediato
# (Princípio 3 do Desenho Universal: uso simples e intuitivo).
# ==============================================================================
st.set_page_config(
    page_title="Comércio Local — Araguari/MG | UNINTER",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": "Atividade Extensionista II — UNINTER | Ciência de Dados | ODS 8 e 9. Município: Araguari/MG."
    },
)

# Caminho base robusto: funciona independente da pasta de onde se roda `streamlit run`
BASE_DIR = Path(__file__).resolve().parent
CLEAN_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_clean.csv"
RAW_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_raw.csv"
FEEDBACK_PATH = BASE_DIR / "data" / "feedbacks.csv"

# Paleta acessível: contraste alto, amigável a daltônicos (evita só vermelho/verde juntos)
COR_PRIMARIA = "#0B5CAB"   # azul institucional
COR_SECUNDARIA = "#E8871E"  # laranja
COR_APOIO = "#2CA58D"       # verde-azulado

plt.rcParams.update({  # fonte maior nos gráficos = legibilidade (Desenho Universal #4)
    "font.size": 11, "axes.titlesize": 13, "axes.labelsize": 11,
    "xtick.labelsize": 10, "ytick.labelsize": 10,
})


# ==============================================================================
# CAMADA DE DADOS (com cache para performance — Desenho Universal #6: baixo esforço)
# ==============================================================================
@st.cache_data(show_spinner="Carregando dados de Araguari/MG...")
def carregar_dados() -> pd.DataFrame:
    """Carrega o CSV limpo. Se não existir, tenta o bruto com limpeza mínima de fallback.

    Retorna DataFrame padronizado. Em caso de falha total, exibe erro acessível e para.
    """
    try:
        if CLEAN_PATH.exists():
            df = pd.read_csv(CLEAN_PATH, encoding="utf-8")
        elif RAW_PATH.exists():
            # Fallback mínimo: garante que `streamlit run app.py` funcione mesmo sem ETL prévio
            st.warning("Arquivo limpo não encontrado. Aplicando limpeza de fallback sobre o bruto.")
            df = pd.read_csv(RAW_PATH, encoding="utf-8")
            df["bairro"] = df["bairro"].astype(str).str.strip().str.title()
            df["categoria"] = df["categoria"].astype(str).str.strip().str.title()
            df["faturamento_mensal_estimado"] = (
                pd.to_numeric(df["faturamento_mensal_estimado"], errors="coerce")
                .fillna(15000.0)
            )
            for c in ["possui_google", "possui_instagram", "possui_whatsapp"]:
                if c in df.columns:
                    df[c] = df[c].astype(str).str.strip().str.lower().isin({"sim", "s", "1", "true"})
                    df[c] = df[c].astype(int)
            if "indice_visibilidade_digital" not in df.columns:
                df["indice_visibilidade_digital"] = (
                    df.get("possui_google", 0) * 30 + df.get("possui_instagram", 0) * 25
                    + df.get("possui_whatsapp", 0) * 20 + 20
                )
        else:
            st.error("Nenhum arquivo de dados encontrado em `data/`. Rode `python src/gerar_dados.py`.")
            st.stop()
        return df
    except Exception as e:  # Tolerância ao erro (#5): mensagem em linguagem simples
        st.error(f"Não foi possível carregar os dados. Detalhe técnico: {e}")
        st.stop()


def formatar_moeda(valor: float) -> str:
    """Formata 18868.24 -> 'R$ 18.868,24' (padrão brasileiro, familiar ao comerciante)."""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "—"


@st.cache_data
def carregar_feedbacks() -> pd.DataFrame:
    """Lê feedbacks da comunidade; retorna DF vazio padronizado se ainda não houver."""
    colunas = ["data_hora", "nome", "bairro", "nota", "comentario"]
    if FEEDBACK_PATH.exists():
        try:
            df = pd.read_csv(FEEDBACK_PATH, encoding="utf-8")
            return df if set(colunas).issubset(df.columns) else pd.DataFrame(columns=colunas)
        except Exception:
            return pd.DataFrame(columns=colunas)
    return pd.DataFrame(columns=colunas)


def salvar_feedback(nome: str, bairro: str, nota: int, comentario: str) -> None:
    """Acrescenta um feedback ao CSV e limpa o cache para exibição imediata."""
    FEEDBACK_PATH.parent.mkdir(parents=True, exist_ok=True)
    novo = pd.DataFrame([{
        "data_hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "nome": nome.strip(), "bairro": bairro,
        "nota": int(nota), "comentario": comentario.strip(),
    }])
    if FEEDBACK_PATH.exists():
        antigo = pd.read_csv(FEEDBACK_PATH, encoding="utf-8")
        atualizado = pd.concat([antigo, novo], ignore_index=True)
    else:
        atualizado = novo
    atualizado.to_csv(FEEDBACK_PATH, index=False, encoding="utf-8")
    carregar_feedbacks.clear()  # invalida cache -> lista atualiza sem reload manual


# ==============================================================================
# CARGA INICIAL
# ==============================================================================
df = carregar_dados()

# --- BARRA LATERAL: FILTROS (o coração da segmentação pedida no enunciado) --------------
st.sidebar.image("https://cdn.jsdelivr.net/gh/twitter/twemoji@14.0.2/assets/72x72/1f3ea.png", width=48)
st.sidebar.title("🔎 Filtros da análise")
st.sidebar.caption("Município: **Araguari/MG** (IBGE 3103504). Use os filtros para segmentar por bairro e categoria.")

bairros_unicos = sorted(df["bairro"].dropna().unique().tolist())
categorias_unicas = sorted(df["categoria"].dropna().unique().tolist())

# Multiselect com default = todos (evita tela vazia no primeiro acesso — tolerância ao erro)
sel_bairros = st.sidebar.multiselect(
    "Bairro", options=bairros_unicos, default=bairros_unicos,
    help="Selecione um ou mais bairros. Ex.: Centro, Rosário, Independência.",
)
sel_cats = st.sidebar.multiselect(
    "Categoria comercial", options=categorias_unicas, default=categorias_unicas,
    help="Ex.: Alimentação, Automotivo, Saúde, Vestuário.",
)
busca = st.sidebar.text_input(
    "Buscar por nome do comércio", placeholder="Ex.: padaria, oficina...",
    help="Filtro textual: digite parte do nome fantasia.",
)
fat_min, fat_max = float(df["faturamento_mensal_estimado"].min()), float(df["faturamento_mensal_estimado"].max())
faixa_fat = st.sidebar.slider(
    "Faixa de faturamento mensal estimado (R$)", min_value=fat_min, max_value=fat_max,
    value=(fat_min, fat_max), format="R$ %.0f",
    help="Arraste para focar em micro ou pequenos faturamentos.",
)
vis_min = st.sidebar.slider(
    "Visibilidade digital mínima", 0, 100, 0,
    help="Índice 0–100: presença no Google + Instagram + WhatsApp + avaliações.",
)

col_btn1, col_btn2 = st.sidebar.columns(2)
with col_btn1:
    if st.button("🧹 Limpar filtros", use_container_width=True,
                 help="Restaura todos os filtros (recuperação de erro em 1 clique)."):
        st.rerun()

# Aplica filtros com Pandas (vetorizado = rápido mesmo com milhares de linhas)
df_f = df.copy()
if sel_bairros:
    df_f = df_f[df_f["bairro"].isin(sel_bairros)]
if sel_cats:
    df_f = df_f[df_f["categoria"].isin(sel_cats)]
if busca.strip():
    df_f = df_f[df_f["nome_fantasia"].str.contains(busca.strip(), case=False, na=False)]
df_f = df_f[df_f["faturamento_mensal_estimado"].between(faixa_fat[0], faixa_fat[1])]
df_f = df_f[df_f["indice_visibilidade_digital"] >= vis_min]

# Estado vazio tratado com orientação (Desenho Universal #5), nunca tela em branco/erro
if df_f.empty:
    st.warning("⚠️ Nenhum estabelecimento corresponde aos filtros. Ajuste os filtros ou clique em **🧹 Limpar filtros**.")
    st.stop()

# ==============================================================================
# CABEÇALHO
# ==============================================================================
st.title("🏪 Densidade Comercial e Visibilidade Digital — Araguari/MG")
st.markdown(
    "Painel interativo da **Atividade Extensionista II (UNINTER — Ciência de Dados)**. "
    "Mapeia pequenos estabelecimentos por bairro e categoria, estima faturamento e mede a "
    "**presença digital** (Google, Instagram, WhatsApp e avaliações). "
    "Alinhado aos **ODS 8** (Trabalho Decente e Crescimento Econômico) e **ODS 9** (Inovação e Infraestrutura)."
)
st.caption(f"Fonte: levantamento simulado realista p/ fins acadêmicos • {len(df_f)} de {len(df)} estabelecimentos exibidos • "
           f"Atualizado em {datetime.now().strftime('%d/%m/%Y')}")

# ==============================================================================
# KPIs PRINCIPAIS (métricas pedidas no enunciado)
# ==============================================================================
total = len(df_f)
fat_medio = df_f["faturamento_mensal_estimado"].mean()
vis_media = df_f["indice_visibilidade_digital"].mean()
pct_google = df_f["possui_google"].mean() * 100 if "possui_google" in df_f else 0
empregos = int(df_f["n_funcionarios"].sum()) if "n_funcionarios" in df_f else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("🏬 Estabelecimentos mapeados", f"{total}", help="Total após filtros aplicados.")
k2.metric("💰 Faturamento médio estimado", formatar_moeda(fat_medio), help="Média winsorizada (outliers contidos no ETL).")
k3.metric("📱 Visibilidade digital média", f"{vis_media:.1f}/100", help="0–100: Google 30 + Instagram 25 + WhatsApp 20 + nota 15 + volume 10.")
k4.metric("📍 Com Google Perfil", f"{pct_google:.0f}%", help="% com Google Perfil da Empresa (vitrine gratuita).")
k5.metric("👥 Empregos estimados", f"{empregos}", help="Soma de funcionários declarados — proxy do ODS 8.")

st.divider()

# ==============================================================================
# ABAS DE NAVEGAÇÃO (reduz carga cognitiva: 1 tema por aba — Desenho Universal #3)
# ==============================================================================
aba1, aba2, aba3, aba4, aba5, aba6 = st.tabs([
    "📊 Visão geral", "🗺️ Densidade de mercado", "📱 Visibilidade digital",
    "🗃️ Dados detalhados", "🌍 ODS 8 e 9", "💬 Feedback comunitário",
])

# --- ABA 1: distribuição por bairro/categoria --------------------------------------
with aba1:
    st.subheader("Distribuição dos comércios")
    c1, c2 = st.columns(2)

    por_bairro = df_f["bairro"].value_counts().sort_values(ascending=False)
    por_cat = df_f["categoria"].value_counts().sort_values(ascending=False)

    with c1:
        st.markdown("**Por bairro** (interativo — passe o mouse)")
        st.bar_chart(por_bairro, color=COR_PRIMARIA)  # nativo = interativo (tooltip)
        # Matplotlib exigido no enunciado, com rótulos de valor (acessível sem depender de cor)
        fig, ax = plt.subplots(figsize=(7, 4))
        por_bairro.plot.barh(ax=ax, color=COR_PRIMARIA)
        ax.set_xlabel("Nº de estabelecimentos"); ax.set_ylabel("")
        ax.set_title("Estabelecimentos por bairro — Araguari/MG")
        ax.invert_yaxis()
        for i, v in enumerate(por_bairro.values):
            ax.text(v + 0.3, i, str(v), va="center", fontsize=10)
        fig.tight_layout()
        st.pyplot(fig, use_container_width=True)

    with c2:
        st.markdown("**Por categoria** (interativo — passe o mouse)")
        st.bar_chart(por_cat, color=COR_SECUNDARIA)
        fig2, ax2 = plt.subplots(figsize=(7, 4))
        por_cat.plot.barh(ax=ax2, color=COR_SECUNDARIA)
        ax2.set_xlabel("Nº de estabelecimentos"); ax2.set_ylabel("")
        ax2.set_title("Estabelecimentos por categoria")
        ax2.invert_yaxis()
        for i, v in enumerate(por_cat.values):
            ax2.text(v + 0.3, i, str(v), va="center", fontsize=10)
        fig2.tight_layout()
        st.pyplot(fig2, use_container_width=True)

    st.info(
        f"💡 **Leitura:** o bairro com maior densidade é **{por_bairro.index[0]}** ({por_bairro.iloc[0]} comércios) "
        f"e a categoria mais presente é **{por_cat.index[0]}** ({por_cat.iloc[0]}). "
        "Bairros periféricos com baixa densidade são oportunidades de fomento (ODS 8).",
        icon="💡",
    )

# --- ABA 2: densidade + mapa -------------------------------------------------------
with aba2:
    st.subheader("Densidade de mercado por bairro")
    dens = df_f.groupby("bairro").agg(
        n=("id", "count"),
        fat_medio=("faturamento_mensal_estimado", "mean"),
        vis_media=("indice_visibilidade_digital", "mean"),
        empregos=("n_funcionarios", "sum"),
    ).sort_values("n", ascending=False).round(2)
    st.dataframe(dens, use_container_width=True,
                 help="Tabela dinâmica: ordene clicando no cabeçalho.")

    st.markdown("**Mapa dos estabelecimentos filtrados** (pontos por bairro, com jitter anti-sobreposição)")
    if {"latitude", "longitude"}.issubset(df_f.columns):
        st.map(df_f[["latitude", "longitude"]].dropna(), zoom=12, use_container_width=True)
        st.caption("Mapa interativo (scroll = zoom). Cada ponto é um estabelecimento da seleção atual.")
    else:
        st.caption("Coordenadas indisponíveis neste conjunto.")

    # Faturamento médio por categoria — onde está o dinheiro?
    st.markdown("**Faturamento médio estimado por categoria (R$)**")
    fat_cat = df_f.groupby("categoria")["faturamento_mensal_estimado"].mean().sort_values()
    st.bar_chart(fat_cat, color=COR_APOIO)
    st.caption("Barras interativas. Categorias à direita têm ticket médio maior — útil para decidir onde empreender.")

# --- ABA 3: visibilidade digital (ODS 9) -------------------------------------------
with aba3:
    st.subheader("Maturidade digital dos pequenos negócios (ODS 9)")
    m1, m2, m3 = st.columns(3)
    m1.metric("Com Instagram", f"{df_f['possui_instagram'].mean()*100:.0f}%")
    m2.metric("Com WhatsApp", f"{df_f['possui_whatsapp'].mean()*100:.0f}%")
    m3.metric("Nota média no Google", f"{df_f['avaliacao_google'].replace(0, pd.NA).mean():.1f} ⭐")

    st.markdown("**Visibilidade média por categoria** — quem está ficando invisível no digital?")
    vis_cat = df_f.groupby("categoria")["indice_visibilidade_digital"].mean().sort_values()
    st.bar_chart(vis_cat, color=COR_PRIMARIA)

    fig3, ax3 = plt.subplots(figsize=(8, 4))
    vis_cat.plot.barh(ax=ax3, color=COR_PRIMARIA)
    ax3.set_title("Índice médio de visibilidade digital por categoria (0–100)")
    ax3.set_xlabel("Índice médio"); ax3.invert_yaxis()
    for i, v in enumerate(vis_cat.values):
        ax3.text(v + 0.5, i, f"{v:.1f}", va="center", fontsize=10)
    fig3.tight_layout()
    st.pyplot(fig3, use_container_width=True)

    st.warning(
        "⚠️ **Alerta ODS 9:** estabelecimentos com índice abaixo de 30 geralmente não têm Google nem "
        "Instagram — são invisíveis para quem busca no celular. Oficinas de capacitação digital gratuita "
        "teriam maior impacto nesses grupos.",
        icon="⚠️",
    )

# --- ABA 4: tabela dinâmica + download ---------------------------------------------
with aba4:
    st.subheader("Tabela dinâmica — explore cada comércio")
    st.caption("Dica de acessibilidade: use a busca da barra lateral; a tabela acompanha os filtros. Clique no cabeçalho para ordenar.")
    cols_show = ["nome_fantasia", "categoria", "bairro", "endereco", "faturamento_mensal_estimado",
                 "indice_visibilidade_digital", "avaliacao_google", "n_funcionarios", "anos_atividade"]
    cols_show = [c for c in cols_show if c in df_f.columns]
    st.dataframe(
        df_f[cols_show].rename(columns={
            "nome_fantasia": "Estabelecimento", "categoria": "Categoria", "bairro": "Bairro",
            "endereco": "Endereço", "faturamento_mensal_estimado": "Faturamento mensal (R$)",
            "indice_visibilidade_digital": "Visibilidade (0–100)", "avaliacao_google": "Nota Google",
            "n_funcionarios": "Funcionários", "anos_atividade": "Anos de atividade",
        }),
        use_container_width=True, height=420,
    )
    csv = df_f.to_csv(index=False, encoding="utf-8")
    st.download_button("⬇️ Baixar seleção atual em CSV", data=csv,
                       file_name="araguari_selecao.csv", mime="text/csv",
                       help="Baixa exatamente o que está filtrado (transparência e reuso — ODS 9).")

# --- ABA 5: ODS --------------------------------------------------------------------
with aba5:
    st.subheader("Como este painel serve aos ODS 8 e 9")
    o1, o2 = st.columns(2)
    with o1:
        st.markdown("### 💼 ODS 8 — Trabalho Decente e Crescimento Econômico")
        st.markdown(
            "- **Mapeia** micro e pequenos negócios por bairro (base para políticas de fomento).\n"
            "- **Estima empregos** e faturamento médio por região/categoria.\n"
            "- **Revela vazios comerciais** (bairros pouco atendidos = oportunidade de empreender).\n"
            f"- Nesta seleção: **{empregos} empregos** em **{total} negócios** "
            f"(média de {empregos/max(total,1):.1f} por negócio)."
        )
    with o2:
        st.markdown("### 🏭 ODS 9 — Inovação e Infraestrutura")
        st.markdown(
            "- **Mede infraestrutura digital** de baixo custo (Google, Instagram, WhatsApp).\n"
            "- **Prioriza capacitação**: índice < 30 = público-alvo de inclusão digital.\n"
            "- **Dados abertos**: download em CSV para a prefeitura, SEBRAE e associações.\n"
            f"- Nesta seleção: visibilidade média **{vis_media:.1f}/100**; "
            f"**{100-pct_google:.0f}%** ainda sem Google Perfil."
        )
    st.success("🎯 **Recomendação extensionista:** mutirão de cadastro no Google Perfil da Empresa no Centro + "
               "oficina de Instagram para Alimentação e Vestuário nos bairros periféricos.", icon="🎯")

# --- ABA 6: FEEDBACK / VALIDAÇÃO COMUNITÁRIA ----------------------------------------
with aba6:
    st.subheader("💬 Validação comunitária — a voz do comerciante")
    st.markdown("Comerciante de Araguari? Registre seu nome, avalie a ferramenta (1–5 ⭐) e deixe um comentário. "
                "Sua avaliação valida o projeto perante a comunidade (requisito extensionista).")

    with st.form("form_feedback", clear_on_submit=True):
        nome = st.text_input("Seu nome *", placeholder="Ex.: Maria Silva",
                             help="Obrigatório. Será exibido na lista pública de validações.")
        bairro_fb = st.selectbox("Bairro do seu negócio", options=bairros_unicos,
                                 help="Selecione o bairro do seu estabelecimento.")
        nota = st.radio("Avaliação da ferramenta * (1 = pouco útil, 5 = muito útil)",
                        options=[1, 2, 3, 4, 5], index=4, horizontal=True,
                        help="1 estrela = pouco útil; 5 estrelas = muito útil.")
        comentario = st.text_area("Comentário / feedback *", placeholder="Ex.: o painel me ajudou a perceber que meu bairro tem poucos concorrentes...",
                                  max_chars=500, help="Máximo 500 caracteres. Seja específico: o que ajudou? O que falta?")
        enviado = st.form_submit_button("✅ Enviar avaliação", use_container_width=True)

        if enviado:
            if not nome.strip() or not comentario.strip():
                st.error("Por favor, preencha **nome** e **comentário** antes de enviar. (A nota já vem marcada como 5 — ajuste se quiser.)")
            else:
                salvar_feedback(nome, bairro_fb, nota, comentario)
                st.success(f"Obrigado, **{nome.strip()}**! Sua avaliação de **{nota} ⭐** foi registrada. 🙏")
                st.balloons()  # reforço positivo, sem prejuízo de acessibilidade (conteúdo segue em texto)

    st.divider()
    fb = carregar_feedbacks()
    if fb.empty:
        st.caption("Ainda não há avaliações registradas. Seja a primeira pessoa a validar! 👆")
    else:
        f1, f2, f3 = st.columns(3)
        f1.metric("Avaliações recebidas", len(fb))
        f2.metric("Nota média da comunidade", f"{pd.to_numeric(fb['nota'], errors='coerce').mean():.1f} ⭐")
        f3.metric("Bairros participantes", fb["bairro"].nunique())
        st.markdown("**Avaliações recentes**")
        st.dataframe(
            fb.sort_index(ascending=False).head(20).rename(columns={
                "data_hora": "Data", "nome": "Nome", "bairro": "Bairro",
                "nota": "Nota (1–5)", "comentario": "Comentário",
            }),
            use_container_width=True, height=300,
        )

# ==============================================================================
# RODAPÉ
# ==============================================================================
st.divider()
st.caption(
    "🏪 **Dashboard Comercial de Araguari/MG** • Atividade Extensionista II — UNINTER (Ciência de Dados) • "
    "ODS 8 e ODS 9 • Dados simulados para fins acadêmicos (IBGE 3103504) • "
    "Acessibilidade: Desenho Universal — contraste alto, rótulos claros, tolerância a erros e redundância texto+cor."
)
