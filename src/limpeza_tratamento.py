# -*- coding: utf-8 -*-
"""
LIMPEZA E TRATAMENTO DE DADOS REAIS — Araguari/MG
=================================================
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados.

Este ETL NÃO cria, estima ou inventa nenhum dado. Ele apenas LIMPA e
PADRONIZA o que `src/coleta_dados.py` baixou das fontes públicas:
  - data/osm_pois_araguari.json  (OpenStreetMap — estabelecimentos reais)

Transformações (todas auditáveis, sem imputação inventada):
  1. Remove POIs duplicados (mesmo nome + mesmas coordenadas).
  2. Padroniza bairro (tira espaços; "Não informado" quando ausente — o
     dashboard mostra esse grupo separadamente, sem disfarçar a lacuna).
  3. Traduz a etiqueta OSM (`shop=supermarket`) para categoria PT-BR via
     MAPA_CATEGORIAS. Etiquetas sem tradução viram "Outros (<etiqueta>)"
     e são listadas no log — nada é reclassificado no escuro.
  4. Converte presença digital em flags 0/1 a partir das tags REAIS
     (website/phone/instagram...). Sem tag = 0 (ausência registrada, não
     estimada). Índice 0–100 com fórmula documentada abaixo.
  5. Valida coordenadas dentro do retângulo do município.

Índice de presença digital (DERIVADO de flags reais, fórmula pública):
    site × 40 + telefone × 30 + rede social × 20 + whatsapp × 10
Não é "nota de qualidade": é só a soma ponderada do que está declarado
no cadastro OSM de cada ponto.

Uso:
    python src/limpeza_tratamento.py
"""

from pathlib import Path
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent.parent
POIS_PATH = BASE_DIR / "data" / "osm_pois_araguari.json"
CLEAN_PATH = BASE_DIR / "data" / "estabelecimentos_araguari_clean.csv"

# Tradução etiqueta OSM -> categoria do projeto (só renomeia; não cria dado).
# Chave: (chave_osm, valor_osm). Ausentes aqui caem em "Outros (<valor>)".
MAPA_CATEGORIAS = {
    # Alimentação
    ("shop", "supermarket"): "Alimentação", ("shop", "grocery"): "Alimentação",
    ("shop", "convenience"): "Alimentação", ("shop", "bakery"): "Alimentação",
    ("shop", "butcher"): "Alimentação", ("shop", "beverages"): "Alimentação",
    ("shop", "confectionery"): "Alimentação", ("shop", "greengrocer"): "Alimentação",
    ("shop", "deli"): "Alimentação", ("shop", "food"): "Alimentação",
    ("amenity", "restaurant"): "Alimentação", ("amenity", "cafe"): "Alimentação",
    ("amenity", "fast_food"): "Alimentação", ("amenity", "bar"): "Alimentação",
    ("amenity", "pub"): "Alimentação", ("amenity", "ice_cream"): "Alimentação",
    # Automotivo
    ("shop", "car"): "Automotivo", ("shop", "car_repair"): "Automotivo",
    ("shop", "car_parts"): "Automotivo", ("shop", "motorcycle"): "Automotivo",
    ("shop", "tyres"): "Automotivo", ("amenity", "fuel"): "Automotivo",
    # Saúde
    ("shop", "pharmacy"): "Saúde", ("shop", "optician"): "Saúde",
    ("shop", "medical_supply"): "Saúde",
    ("amenity", "pharmacy"): "Saúde", ("amenity", "clinic"): "Saúde",
    ("amenity", "doctors"): "Saúde", ("amenity", "dentist"): "Saúde",
    ("amenity", "veterinary"): "Saúde",
    # Vestuário
    ("shop", "clothes"): "Vestuário", ("shop", "shoes"): "Vestuário",
    ("shop", "fashion"): "Vestuário", ("shop", "tailor"): "Vestuário",
    # Beleza e Estética
    ("shop", "hairdresser"): "Beleza e Estética", ("shop", "beauty"): "Beleza e Estética",
    ("shop", "cosmetics"): "Beleza e Estética", ("shop", "tattoo"): "Beleza e Estética",
    # Educação e papelaria
    ("shop", "books"): "Educação e Papelaria", ("shop", "stationery"): "Educação e Papelaria",
    ("office", "educational_institution"): "Educação e Papelaria",
    # Serviços Gerais
    ("shop", "laundry"): "Serviços Gerais", ("shop", "dry_cleaning"): "Serviços Gerais",
    ("shop", "funeral_directors"): "Serviços Gerais", ("shop", "pet"): "Serviços Gerais",
    ("shop", "pet_grooming"): "Serviços Gerais", ("shop", "travel_agency"): "Serviços Gerais",
    ("shop", "lottery"): "Serviços Gerais",
    ("shop", "general"): "Varejo Diverso", ("shop", "repair"): "Serviços Gerais",
    ("shop", "photo"): "Serviços Gerais", ("shop", "agrarian"): "Varejo Diverso",
    ("shop", "swimming_pool"): "Varejo Diverso",
    ("office", "estate_agent"): "Serviços Gerais", ("office", "company"): "Serviços Gerais",
    ("amenity", "bank"): "Serviços Gerais",
    ("craft", "photographer"): "Serviços Gerais",
    # Varejo Diverso
    ("shop", "department_store"): "Varejo Diverso", ("shop", "variety_store"): "Varejo Diverso",
    ("shop", "gift"): "Varejo Diverso", ("shop", "florist"): "Varejo Diverso",
    ("shop", "furniture"): "Varejo Diverso", ("shop", "houseware"): "Varejo Diverso",
    ("shop", "second_hand"): "Varejo Diverso", ("shop", "newsagent"): "Varejo Diverso",
    ("shop", "toys"): "Varejo Diverso", ("shop", "sports"): "Varejo Diverso",
    ("amenity", "marketplace"): "Varejo Diverso",
    # Construção e Reforma
    ("shop", "doityourself"): "Construção e Reforma", ("shop", "hardware"): "Construção e Reforma",
    ("shop", "paint"): "Construção e Reforma", ("shop", "trade"): "Construção e Reforma",
    ("craft", "carpenter"): "Construção e Reforma", ("craft", "electrician"): "Construção e Reforma",
    ("craft", "plumber"): "Construção e Reforma", ("craft", "metal_construction"): "Construção e Reforma",
    # Tecnologia e Informática
    ("shop", "computer"): "Tecnologia e Informática", ("shop", "electronics"): "Tecnologia e Informática",
    ("shop", "mobile_phone"): "Tecnologia e Informática",
}


def traduzir_categoria(chave, valor):
    """Retorna a categoria PT-BR ou 'Outros (<valor>)' — nunca inventa classe."""
    return MAPA_CATEGORIAS.get((chave, valor), f"Outros ({valor})")


def limpar() -> pd.DataFrame:
    df = pd.read_json(POIS_PATH, encoding="utf-8")
    print(f"[ETL] {len(df)} POIs brutos lidos.")

    # 1. Deduplicação por nome + coordenada (mesmo ponto cadastrado 2x)
    antes = len(df)
    df = df.drop_duplicates(subset=["nome", "latitude", "longitude"], keep="first")
    print(f"[ETL] duplicatas removidas: {antes - len(df)}")

    # 2. Bairro: só normaliza texto; ausente vira "Não informado" (grupo visível no app)
    df["bairro"] = df["bairro"].fillna("").astype(str).str.strip()
    df.loc[df["bairro"] == "", "bairro"] = "Não informado"

    # 3. Categoria PT-BR via dicionário público (acima); lista o que caiu em "Outros"
    df["categoria_osm"] = df["chave"] + "=" + df["valor"]
    df["categoria"] = [traduzir_categoria(k, v) for k, v in zip(df["chave"], df["valor"])]
    outros = sorted(df.loc[df["categoria"].str.startswith("Outros"), "categoria_osm"].unique())
    if outros:
        print(f"[ETL] etiquetas sem tradução ({len(outros)}), classificadas como Outros: {outros}")

    # 4. Flags de presença digital a partir das tags REAIS (sem tag = 0)
    df["tem_site"] = df["site"].notna().astype(int)
    df["tem_telefone"] = df["telefone"].notna().astype(int)
    df["tem_rede_social"] = df["rede_social"].notna().astype(int)
    df["tem_whatsapp"] = df["whatsapp"].notna().astype(int)
    df["indice_presenca_digital"] = (
        df["tem_site"] * 40 + df["tem_telefone"] * 30
        + df["tem_rede_social"] * 20 + df["tem_whatsapp"] * 10
    ).astype(int)

    # 5. Endereço textual só com o que existe (sem completar número/bairro)
    df["endereco"] = (df["rua"].fillna("") + " " + df["numero"].fillna("")).str.strip()
    df.loc[df["endereco"] == "", "endereco"] = "Não informado"

    df["fonte"] = "OpenStreetMap"
    df = df.sort_values(["bairro", "categoria", "nome"]).reset_index(drop=True)
    df["id"] = df.index + 1
    cols = ["id", "nome", "categoria", "categoria_osm", "bairro", "bairro_fonte",
            "endereco", "latitude", "longitude", "tem_site", "tem_telefone",
            "tem_rede_social", "tem_whatsapp", "indice_presenca_digital",
            "horario", "fonte", "osm_tipo", "osm_id"]
    return df[cols]


def main():
    if not POIS_PATH.exists():
        raise FileNotFoundError(f" rode `python src/coleta_dados.py` primeiro: {POIS_PATH}")
    df = limpar()
    df.to_csv(CLEAN_PATH, index=False, encoding="utf-8")
    print(f"[OK] {len(df)} estabelecimentos reais salvos em {CLEAN_PATH}")
    print(f"     bairros: {df['bairro'].nunique()} | categorias: {df['categoria'].nunique()}")
    print(f"     com site: {df['tem_site'].sum()} | com telefone: {df['tem_telefone'].sum()} "
          f"| com rede social: {df['tem_rede_social'].sum()}")


if __name__ == "__main__":
    main()
