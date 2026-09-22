"""
GERADOR DE DADOS SINTÉTICOS — Comércio local de Araguari/MG
------------------------------------------------------------
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados
ODS 8 (Trabalho Decente e Crescimento Econômico) e
ODS 9 (Indústria, Inovação e Infraestrutura).

Este script gera o arquivo `data/estabelecimentos_araguari_raw.csv`
com ~240 registros simulados porém realistas, PROPOSITALMENTE com
"sujeiras" típicas de coleta de campo (caixa inconsistente, "Sim/Não",
valores monetários como texto, nulos e duplicatas) para que o script
`limpeza_tratamento.py` demonstre o processo de ETL.

Bairros e categorias baseados na realidade de Araguari/MG.
Coordenadas aproximadas do centro: -18.6472, -48.1872.
"""

import random
import csv
from pathlib import Path

random.seed(42)  # Reprodutibilidade — importante em ciência de dados

# Bairros reais de Araguari/MG (IBGE cód. 3103504)
BAIRROS = [
    "Centro", "Rosário", "Independência", "Amorim", "Miranda",
    "São Sebastião", "Novo Horizonte", "Bosque", "Santa Helena",
    "Jóquei Clube", "Portal de Fátima", "Ouro Verde",
    "Goiás", "Paraíso", "Sibipiruna", "Vieno",
]

# Categorias comerciais mapeadas no projeto
CATEGORIAS = [
    "Alimentação", "Automotivo", "Saúde", "Vestuário",
    "Beleza e Estética", "Educação", "Serviços Gerais",
    "Varejo Diverso", "Construção e Reforma", "Tecnologia e Informática",
]

# Nomes-base por categoria para nomes fantasia realistas
NOMES_BASE = {
    "Alimentação": ["Sabor Mineiro", "Pão & Prosa", "Cantina do Zé", "Acarajé da Leninha",
                    "Pastelaria Central", "Empório Araguari", "Churrascaria Boi na Brasa",
                    "Doceria Sonho Doce", "Marmitaria Dona Cida", "Café do Cerrado"],
    "Automotivo": ["Auto Center Araguari", "Oficina do Paulinho", "Pneu & Cia",
                   "Funilaria Ideal", "Moto Peças Rosário", "Lava Jato Estrela"],
    "Saúde": ["Farmácia Popular", "Clínica Vida Plena", "Odonto Sorriso",
              "Fisio + Saúde", "Laboratório BioAnálise", "Psicóloga Ana Ribeiro"],
    "Vestuário": ["Moda Mineira", "Boutique Elegance", "Brechó Retrô",
                  "Loja Estilo Jovem", "Confecções Amorim", "Sapataria Central"],
    "Beleza e Estética": ["Salão Beleza Pura", "Barbearia Corte Fino", "Studio Nail Art",
                          "Espaço Zen Estética", "Salão Dona Flor"],
    "Educação": ["Escola de Idiomas Fala Mundo", "Reforço Escolar Aprender+",
                 "Curso Preparatório Aprova", "Escola de Música Ritmo"],
    "Serviços Gerais": ["Chaveiro 24h", "Lavanderia Limpa Tudo", "Pet Shop Amigo Fiel",
                        "Assistência Técnica Cell+", "Contabilidade Prática"],
    "Varejo Diverso": ["Papelaria Horizonte", "Livraria Saber", "Presentes & Cia",
                       "Utilidades Lar Doce Lar", "Bazar Central"],
    "Construção e Reforma": ["Material de Construção Alvorada", "Elétrica & Hidráulica JM",
                             "Marcenaria Arte Madeira", "Tintas Colorir"],
    "Tecnologia e Informática": ["InfoTech Araguari", "Lan House Conecta",
                                 "Assistência Notebook Já", "Loja Gamer Level Up"],
}

RUAS = ["Av. Minas Gerais", "Rua Rui Barbosa", "Av. Coronel Teodolino Pereira de Araújo",
        "Rua Pedro Nasciutti", "Av. Senador Melo Viana", "Rua Florestina Quintino",
        "Av. das Palmeiras", "Rua Hermogênio Veloso", "Rua Marciano Santos"]


def dinheiro_como_texto(valor: float) -> str:
    """Simula sujeira: às vezes 'R$ 12.500,00', às vezes número puro, às vezes vazio."""
    sorte = random.random()
    if sorte < 0.08:
        return ""  # dado ausente (nulo)
    if sorte < 0.35:
        # Formato brasileiro como texto
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return str(round(valor, 2))


def sim_nao_sujo(valor_bool: bool) -> str:
    """Simula sujeira: 'Sim', 'SIM', 'sim ', 'S', 'Não', 'N', 'nao', etc."""
    opcoes_sim = ["Sim", "SIM", "sim ", " Sim", "S", "s", "1"]
    opcoes_nao = ["Não", "NÃO", "não", "Nao", "nao", "N", "n", "0", ""]
    if valor_bool:
        return random.choice(opcoes_sim)
    return random.choice(opcoes_nao)


def gerar_registros(n: int = 240):
    registros = []
    reg_id = 1
    for _ in range(n):
        categoria = random.choice(CATEGORIAS)
        bairro = random.choices(
            BAIRROS,
            weights=[22, 10, 9, 8, 7, 7, 6, 6, 5, 5, 4, 4, 2, 2, 2, 1],
            k=1,
        )[0]
        nome = f"{random.choice(NOMES_BASE[categoria])} {random.choice(['', 'II', 'Jr.', 'Express', 'Prime'])}".strip()
        # Caixa inconsistente proposital
        if random.random() < 0.25:
            nome = nome.upper()
        elif random.random() < 0.25:
            nome = nome.lower()

        faturamento = round(random.gauss(18500, 12000), 2)
        faturamento = max(1500, faturamento)
        if random.random() < 0.03:  # outlier proposital
            faturamento = round(random.uniform(250000, 600000), 2)

        tem_google = random.random() < (0.72 if bairro == "Centro" else 0.45)
        tem_insta = random.random() < (0.68 if categoria in ("Vestuário", "Beleza e Estética", "Alimentação") else 0.40)
        tem_wpp = random.random() < 0.85
        avaliacao = round(random.uniform(3.2, 5.0), 1) if tem_google and random.random() > 0.1 else ""
        num_av = random.randint(3, 850) if tem_google and avaliacao != "" else ""

        registros.append({
            "id": reg_id,
            "nome_fantasia": nome,
            "categoria": categoria.upper() if random.random() < 0.2 else categoria,  # sujeira caixa
            "bairro": f" {bairro} " if random.random() < 0.15 else bairro,  # espaços extras
            "endereco": f"{random.choice(RUAS)}, {random.randint(50, 2500)}",
            "faturamento_mensal_estimado": dinheiro_como_texto(faturamento),
            "possui_google": sim_nao_sujo(tem_google),
            "possui_instagram": sim_nao_sujo(tem_insta),
            "possui_whatsapp": sim_nao_sujo(tem_wpp),
            "avaliacao_google": avaliacao,
            "num_avaliacoes_google": num_av,
            "n_funcionarios": random.choice([1, 2, 3, 4, 5, 6, 8, 10, "", 3, 2]),
            "anos_atividade": round(random.uniform(0.5, 28), 1),
        })
        reg_id += 1

    # Duplicatas propositais (~4%)
    for _ in range(10):
        registros.append(random.choice(registros).copy())
    random.shuffle(registros)
    return registros


def main():
    out = Path(__file__).resolve().parent.parent / "data" / "estabelecimentos_araguari_raw.csv"
    out.parent.mkdir(parents=True, exist_ok=True)
    registros = gerar_registros()
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(registros[0].keys()))
        writer.writeheader()
        writer.writerows(registros)
    print(f"[OK] {len(registros)} registros brutos gerados em: {out}")


if __name__ == "__main__":
    main()
