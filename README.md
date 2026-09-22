# 🏪 Dashboard Comercial de Araguari/MG — Densidade de Mercado e Visibilidade Digital

**Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados**
Alinhado aos **ODS 8** (Trabalho Decente e Crescimento Econômico) e **ODS 9** (Indústria, Inovação e Infraestrutura).

Painel interativo em **Streamlit + Pandas + Matplotlib** que mapeia pequenos estabelecimentos de Araguari/MG por bairro e categoria, estima faturamento e mede a **visibilidade digital** (Google, Instagram, WhatsApp + avaliações).

## 📁 Estrutura do projeto

```
uninter/
├── app.py                              # Aplicativo principal (arquivo único executável)
├── requirements.txt                    # Dependências
├── README.md                           # Este guia
├── .streamlit/config.toml              # Tema de alto contraste (acessibilidade)
├── data/
│   ├── estabelecimentos_araguari_raw.csv    # Dados brutos (com sujeiras propositais)
│   ├── estabelecimentos_araguari_clean.csv  # Dados limpos (gerado pelo ETL)
│   └── feedbacks.csv                   # Validação comunitária (gerado pelo app)
└── src/
    ├── gerar_dados.py                  # Gera dados sintéticos realistas de Araguari/MG
    └── limpeza_tratamento.py           # Pipeline ETL + índice de visibilidade digital
```

## 🚀 Guia de instalação e execução (Windows, macOS ou Linux)

**1. Pré-requisito:** Python 3.10+ instalado. Confira:

```bash
python --version
```

**2. (Recomendado) Criar ambiente virtual:**

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
```

**3. Instalar dependências (pandas, streamlit, matplotlib):**

```bash
pip install -r requirements.txt
```

**4. (Opcional) Regenerar os dados:**

```bash
python src/gerar_dados.py
python src/limpeza_tratamento.py
```

> O `app.py` já funciona direto com os CSVs incluídos. O passo 4 só é necessário se quiser regenerar a massa de dados.

**5. Executar o dashboard:**

```bash
streamlit run app.py
```

Acesse no navegador o endereço exibido (geralmente http://localhost:8501).

## ✨ Funcionalidades

- **KPIs:** total mapeado, faturamento médio, visibilidade digital média, % com Google, empregos estimados.
- **Filtros laterais:** bairro (Centro, Rosário, Independência etc.), categoria (Alimentação, Automotivo, Saúde, Vestuário etc.), busca textual, faixa de faturamento e visibilidade mínima.
- **Gráficos:** barras interativas (`st.bar_chart`) + Matplotlib com rótulos de valor; mapa com `st.map`.
- **Tabela dinâmica + download CSV** da seleção filtrada.
- **Feedback comunitário:** formulário (nome, bairro, 1–5 estrelas, comentário) salvo em `data/feedbacks.csv`, com média e lista pública.
- **Aba ODS 8 e 9** com leitura extensionista e recomendações.

## 🧹 Tratamento de dados (resumo do ETL)

1. Remove duplicatas; 2. padroniza caixa/espaços; 3. normaliza "Sim/Não/S/N" → 0/1;
4. converte "R$ 12.500,00" → float; 5. imputa faturamento pela mediana da categoria;
6. winsoriza outliers (IQR); 7. calcula o **índice de visibilidade digital (0–100)**:
`Google×30 + Instagram×25 + WhatsApp×20 + nota×15 + volume×10`.

## ♿ Acessibilidade (Desenho Universal)

Tema de alto contraste, fonte ≥11pt nos gráficos, rótulos de valor além da cor, textos de ajuda em todos os filtros, tratamento de estado vazio com orientação, layout responsivo e botão "Limpar filtros" em 1 clique.

## 📝 Créditos

Projeto acadêmico — dados simulados e realistas para fins educacionais. Município: Araguari/MG (IBGE 3103504, ~-18.6472, -48.1872).
