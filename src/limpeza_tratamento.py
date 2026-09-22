"""
LIMPEZA E TRATAMENTO DE DADOS — Araguari/MG
-------------------------------------------
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados.

Pipeline ETL (Extract–Transform–Load):
  1. EXTRACT: lê `data/estabelecimentos_araguari_raw.csv`
  2. TRANSFORM: padroniza textos, remove duplicatas, converte tipos,
     trata nulos/outliers e calcula o ÍNDICE DE VISIBILIDADE DIGITAL (0–100)
  3. LOAD: salva `data/estabelecimentos_araguari_clean.csv`

Índice de Visibilidade Digital (justificativa acadêmica — ODS 9):
  Inovação e infraestrutura digital são medidas pela presença em canais
  gratuitos de baixo custo (Google Perfil da Empresa, Instagram, WhatsApp)
  + reputação (nota média e volume de avaliações). Pesos:
    Google (30) + Instagram (25) + WhatsApp (20) + Nota (15) + Volume (10)

Uso:
    python src/limpeza_tratamento.py
"""

from pathlib import Path
import re
import pandas as pd
import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_raw.csv"
CLEAN_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_clean.csv"

# Coordenadas aproximadas por bairro (centroides fictícios p/ mapa/tabela)
COORDS_BAIRRO = {
    "Centro": (-18.6472, -48.1872), "Rosário": (-18.6420, -48.1840),
    "Independência": (-18.6550, -48.1950), "Amorim": (-18.6380, -48.1780),
    "Miranda": (-18.6600, -48.1800), "São Sebastião": (-18.6500, -48.2000),
    "Novo Horizonte": (-18.6350, -48.1950), "Bosque": (-18.6450, -48.1720),
    "Santa Helena": (-18.6650, -48.1900), "Jóquei Clube": (-18.6300, -48.1830),
    "Portal de Fátima": (-18.6580, -48.2050), "Ouro Verde": (-18.6400, -48.2050),
    "Goiás": (-18.6520, -48.1750), "Paraíso": (-18.6455, -48.1920),
    "Sibipiruna": (-18.6385, -48.1900), "Vieno": (-18.6490, -48.1820),
}


def parse_sim_nao(valor) -> int:
    """Normaliza 'Sim/SIM/S/1' -> 1 e 'Não/N/0/vazio' -> 0."""
    if pd.isna(valor):
        return 0
    v = str(valor).strip().lower()
    return 1 if v in {"sim", "s", "1", "yes", "y", "true"} else 0


def parse_dinheiro(valor) -> float:
    """Converte 'R$ 12.500,00' ou '12500.5' ou '' -> float ou NaN."""
    if pd.isna(valor) or str(valor).strip() == "":
        return np.nan
    s = str(valor).strip().replace("R$", "").strip()
    # Formato BR: 12.500,00 -> 12500.00 ; formato US: 12500.50
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    s = re.sub(r"[^0-9.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return np.nan


def title_case_compare(texto: str) -> str:
    """Padroniza 'CENTRO' / ' centro ' -> 'Centro' (respeita nomes próprios)."""
    if pd.isna(texto):
        return texto
    return str(texto).strip().title().replace(" E ", " e ").replace(" De ", " de ")


def calcular_visibilidade(df: pd.DataFrame) -> pd.Series:
    """Calcula o índice 0–100 conforme pesos documentados no cabeçalho."""
    nota = pd.to_numeric(df["avaliacao_google"], errors="coerce").fillna(0) / 5.0  # 0–1
    volume = pd.to_numeric(df["num_avaliacoes_google"], errors="coerce").fillna(0)
    volume_norm = (np.log1p(volume) / np.log1p(850)).clip(0, 1)  # normalização log
    indice = (
        df["possui_google"] * 30
        + df["possui_instagram"] * 25
        + df["possui_whatsapp"] * 20
        + nota * 15
        + volume_norm * 10
    )
    return indice.round(1).clip(0, 100)


def limpar(df: pd.DataFrame) -> pd.DataFrame:
    # 1. Remove duplicatas exatas e por nome+bairro+endereço
    antes = len(df)
    df = df.drop_duplicates()
    df["nome_fantasia"] = df["nome_fantasia"].astype(str).str.strip()
    df["bairro"] = df["bairro"].astype(str).str.strip()
    df["endereco"] = df["endereco"].astype(str).str.strip()
    df = df.drop_duplicates(subset=["nome_fantasia", "bairro", "endereco"], keep="first")
    print(f"[LIMPEZA] Duplicatas removidas: {antes - len(df)}")

    # 2. Padronização textual (Desenho Universal: dados consistentes = leitura simples)
    df["nome_fantasia"] = df["nome_fantasia"].apply(title_case_compare)
    df["categoria"] = df["categoria"].astype(str).str.strip().str.title()
    df["categoria"] = df["categoria"].replace({
        "Varejo Diverso": "Varejo Diverso", "Servicos Gerais": "Serviços Gerais",
    })
    df["bairro"] = df["bairro"].apply(title_case_compare)
    # Corrige variação sem acento
    df["bairro"] = df["bairro"].replace({"Sibipiruna": "Sibipiruna", "Independencia": "Independência"})

    # 3. Conversões de tipo
    df["faturamento_mensal_estimado"] = df["faturamento_mensal_estimado"].apply(parse_dinheiro)
    for col in ["possui_google", "possui_instagram", "possui_whatsapp"]:
        df[col] = df[col].apply(parse_sim_nao).astype(int)
    df["avaliacao_google"] = pd.to_numeric(df["avaliacao_google"], errors="coerce")
    df["num_avaliacoes_google"] = pd.to_numeric(df["num_avaliacoes_google"], errors="coerce").fillna(0).astype(int)
    df["n_funcionarios"] = pd.to_numeric(df["n_funcionarios"], errors="coerce")
    df["anos_atividade"] = pd.to_numeric(df["anos_atividade"], errors="coerce")

    # 4. Tratamento de nulos: mediana por categoria (preserva contexto econômico local)
    df["faturamento_mensal_estimado"] = df.groupby("categoria")["faturamento_mensal_estimado"] \
        .transform(lambda s: s.fillna(s.median()))
    df["faturamento_mensal_estimado"] = df["faturamento_mensal_estimado"].fillna(df["faturamento_mensal_estimado"].median())
    df["n_funcionarios"] = df["n_funcionarios"].fillna(df["n_funcionarios"].median()).astype(int)
    df["avaliacao_google"] = df["avaliacao_google"].fillna(0)

    # 5. Tratamento de outliers (IQR winsorização — evita distorcer a média do KPI)
    q1 = df["faturamento_mensal_estimado"].quantile(0.25)
    q3 = df["faturamento_mensal_estimado"].quantile(0.75)
    iqr = q3 - q1
    teto = q3 + 1.5 * iqr
    n_out = int((df["faturamento_mensal_estimado"] > teto).sum())
    df["faturamento_mensal_estimado"] = df["faturamento_mensal_estimado"].clip(upper=teto).round(2)
    print(f"[LIMPEZA] Outliers de faturamento contidos (teto R$ {teto:,.2f}): {n_out}")

    # 6. Índice de visibilidade digital (KPI central do dashboard)
    df["indice_visibilidade_digital"] = calcular_visibilidade(df)

    # 7. Coordenadas p/ mapa (jitter para não sobrepor pontos do mesmo bairro)
    rng = np.random.default_rng(42)
    lats, lons = [], []
    for b in df["bairro"]:
        lat0, lon0 = COORDS_BAIRRO.get(b, (-18.6472, -48.1872))
        lats.append(lat0 + rng.normal(0, 0.004))
        lons.append(lon0 + rng.normal(0, 0.004))
    df["latitude"], df["longitude"] = np.round(lats, 5), np.round(lons, 5)

    # 8. Ordenação final e reset do índice
    df = df.sort_values(["bairro", "categoria", "nome_fantasia"]).reset_index(drop=True)
    df["id"] = df.index + 1
    return df


def main():
    if not RAW_PATH.exists():
        raise FileNotFoundError(f"Arquivo bruto não encontrado: {RAW_PATH}. Rode `python src/gerar_dados.py` primeiro.")
    df_raw = pd.read_csv(RAW_PATH)
    print(f"[ETL] Lidos {len(df_raw)} registros brutos.")
    df_clean = limpar(df_raw)
    CLEAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_clean.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    print(f"[OK] {len(df_clean)} registros limpos salvos em: {CLEAN_PATH}")
    print(df_clean[["categoria", "bairro"]].value_counts().head(5).to_string())
    print(f"Faturamento médio: R$ {df_clean['faturamento_mensal_estimado'].mean():,.2f} | "
          f"Visibilidade média: {df_clean['indice_visibilidade_digital'].mean():.1f}/100")


if __name__ == "__main__":
    main()
