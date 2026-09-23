# 🏪 Dashboard Comercial de Araguari/MG — 100% dados reais e públicos

**Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados**
**ODS 8** (Trabalho Decente e Crescimento Econômico) e **ODS 9** (Inovação e Infraestrutura).

> **Nenhum dado foi inventado, estimado ou simulado.** Todo número vem de coleta automatizada
> (`python src/coleta_dados.py`) de fontes públicas, com auditoria em `data/proveniencia.json`.

## 📚 Fontes reais

| Fonte | O que fornece | Acesso |
|---|---|---|
| OpenStreetMap (Overpass + Nominatim, ODbL) | Estabelecimentos com nome, categoria, coordenadas, bairro e tags de contato dentro do município (filtro no polígono oficial, relação OSM 314597) | API + geocodificação reversa (1 req/s) |
| IBGE/SIDRA CEMPRE 2024 (tabelas 9509 e 9528) | Unidades locais, empresas, pessoal ocupado, salários — total e por seção CNAE | API de Agregados v3 |
| Wikipédia (CC BY-SA) | Contexto municipal (população, área, PIB, IDH) via webscraping da infobox com BeautifulSoup | HTML público |

**Limitação declarada:** não existe base pública de faturamento por estabelecimento (sigilo fiscal);
por isso o painel usa pessoal ocupado e salários do CEMPRE como indicadores oficiais (ODS 8).

## 📁 Estrutura

```
├── app.py                          # dashboard (streamlit run app.py)
├── requirements.txt
├── src/
│   ├── coleta_dados.py             # coleta real: OSM + SIDRA + Nominatim + Wikipédia
│   └── limpeza_tratamento.py       # ETL: limpa e padroniza (não inventa nada)
└── data/
    ├── osm_pois_araguari.json      # POIs brutos (coletados)
    ├── estabelecimentos_araguari_clean.csv  # POIs limpos
    ├── sidra_9509_totais.csv       # CEMPRE: totais do município
    ├── sidra_9528_por_secao.csv    # CEMPRE: por seção CNAE
    ├── municipio_wikipedia.json    # infobox da Wikipédia
    ├── municipio_contorno.json     # polígono do município
    ├── proveniencia.json           # auditoria: fonte, URL, acesso, licença
    └── feedbacks.csv               # validação comunitária (via app)
```

## 🚀 Instalação e execução

```bash
python --version            # Python 3.10+
python -m venv .venv
# Windows: .venv\Scripts\activate | Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python src/coleta_dados.py         # ~3 min: baixa dados reais
python src/limpeza_tratamento.py   # limpa e padroniza
streamlit run app.py               # abre em http://localhost:8501
```

## ✨ Funcionalidades

- **KPIs reais:** pontos OSM, unidades locais, pessoal ocupado e salário médio (CEMPRE 2024), % com telefone/site.
- **Filtros:** bairro (Centro, Independência, Goiás...), categoria (etiqueta OSM traduzida), busca textual, presença digital mínima.
- **Gráficos** interativos + Matplotlib, **mapa real** (lat/lon OSM), tabela com etiqueta original p/ auditoria + download CSV.
- **Aba Fontes e método** com proveniência, método reprodutível e limitações declaradas.
- **Feedback comunitário** (nome, bairro, 1–5 ⭐, comentário) em `data/feedbacks.csv`.

## ♿ Acessibilidade (Desenho Universal)

Alto contraste, rótulos de valor nos gráficos, ajuda nos filtros, aviso orientado em filtro vazio, layout responsivo.
