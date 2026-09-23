# -*- coding: utf-8 -*-
"""
COLETA DE DADOS REAIS — Comércio de Araguari/MG
================================================
Atividade Extensionista II — UNINTER | Tecnologia em Ciência de Dados.

Este script NÃO gera nem inventa nenhum dado. Ele coleta (download + APIs +
webscraping de HTML público) exclusivamente de fontes públicas e oficiais:

  1. OpenStreetMap (Overpass API) .... estabelecimentos georreferenciados
     (nome, categoria `shop=*`, endereço, telefone, site). Licença ODbL.
  2. IBGE/SIDRA (API de Agregados v3) . CEMPRE tabelas 9509 (totais do
     município) e 9528 (por seção CNAE). Dados oficiais, ano mais recente.
  3. Nominatim (OpenStreetMap) ........ contorno oficial do município
     (relação OSM 314597) p/ filtrar POIs dentro de Araguari. Licença ODbL.
  4. Wikipédia (webscraping HTML) ..... infobox do verbete "Araguari"
     (população, área, fundação...). Licença CC BY-SA.

Saídas em `data/` (todas com fonte + data de acesso em `proveniencia.json`):
  - osm_pois_araguari.json        (POIs brutos dentro do município)
  - sidra_9509_totais.csv         (totais CEMPRE do município)
  - sidra_9528_por_secao.csv      (unidades locais e pessoal por seção CNAE)
  - municipio_wikipedia.json      (infobox da Wikipédia)
  - municipio_contorno.json       (polígono do município)
  - proveniencia.json             (auditoria: fonte, URL, acesso, licença)

Uso:
    python src/coleta_dados.py

Boas práticas de coleta (evita bloqueio e respeita os servidores):
  - User-Agent identificado; pedimos blocos pequenos; instâncias Overpass
    alternativas se a principal responder 504/429.
"""

import csv
import gzip
import json
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "UNINTER-Extensionista-II/1.0 (projeto academico sem fins lucrativos)"}
MUNICIPIO_IBGE = "3103504"          # Araguari/MG (código IBGE de 7 dígitos)
OSM_RELATION_ID = 314597            # Relação OSM do município de Araguari
BBOX = "-18.95,-48.55,-18.35,-47.90"  # retângulo envolvente (depois filtra no polígono)

OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]

PROVENIENCIA = []  # auditoria preenchida ao longo da coleta


def registrar_proveniencia(fonte, descricao, url, licenca, n_registros=None):
    """Registra de onde veio cada dado (transparência p/ a banca e reuso)."""
    PROVENIENCIA.append({
        "fonte": fonte,
        "descricao": descricao,
        "url": url,
        "licenca": licenca,
        "acesso_em_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "n_registros": n_registros,
    })


def http_get_json(url, timeout=90):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if raw[:2] == b"\x1f\x8b":  # servicodados às vezes responde gzipado
        raw = gzip.decompress(raw)
    return json.loads(raw.decode("utf-8"))


def overpass_post(query, timeout=180):
    """POST na Overpass com fallback entre instâncias (respeito a rate-limit)."""
    data = urllib.parse.urlencode({"data": query}).encode()
    erros = []
    for url in OVERPASS_URLS:
        try:
            req = urllib.request.Request(url, data=data, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            erros.append(f"{url}: {e}")
            time.sleep(2)
    raise RuntimeError("Todas as instâncias Overpass falharam: " + " | ".join(erros))


# ---------------------------------------------------------------------------
# 1. IBGE/SIDRA — CEMPRE (totais + por seção CNAE)
# ---------------------------------------------------------------------------
def coletar_sidra():
    base = "https://apisidra.ibge.gov.br/values"

    # 1a. Tabela 9509: totais do município (ano mais recente disponível)
    url_9509 = f"{base}/t/9509/n6/{MUNICIPIO_IBGE}/p/last/v/allxp"
    dados_9509 = http_get_json(url_9509)
    ano_9509 = dados_9509[1]["D2N"]
    with open(DATA_DIR / "sidra_9509_totais.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["variavel_codigo", "variavel", "valor", "unidade", "ano", "municipio"])
        for row in dados_9509[1:]:
            w.writerow([row["D3C"], row["D3N"], row["V"], row["MN"], row["D2N"], row["D1N"]])
    registrar_proveniencia(
        "IBGE/SIDRA", f"CEMPRE tabela 9509 — totais de Araguari/MG ({ano_9509})",
        url_9509, "Dados públicos IBGE (uso livre com citação da fonte)",
        len(dados_9509) - 1,
    )
    print(f"[SIDRA 9509] {len(dados_9509)-1} variáveis, ano {ano_9509}")

    # 1b. Tabela 9528 por SEÇÃO CNAE (descobre os ids das 21 seções via metadados)
    meta = http_get_json("https://servicodados.ibge.gov.br/api/v3/agregados/9528/metadados")
    classif = next(c for c in meta["classificacoes"] if int(c["id"]) == 12762)
    # nível 1 da hierarquia = as 21 SEÇÕES CNAE (A..U); níveis 2+ = divisões/grupos/classes
    secoes = [(str(c["id"]), c["nome"]) for c in classif["categorias"] if c.get("nivel") == 1]
    print(f"[SIDRA 9528] {len(secoes)} seções CNAE identificadas")
    ids = ",".join(sid for sid, _ in secoes)  # SIDRA: múltiplas categorias separadas por vírgula
    url_9528 = (f"{base}/t/9528/n6/{MUNICIPIO_IBGE}/p/last/v/706,707"
                f"/c12762/{ids}")
    dados_9528 = http_get_json(url_9528)
    nomes = dict(secoes)
    with open(DATA_DIR / "sidra_9528_por_secao.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["secao_codigo", "secao_cnae", "variavel", "valor", "ano"])
        for row in dados_9528[1:]:
            if row["V"] == "X":  # desidentificado (<3 informantes): preserva como ausente
                continue
            w.writerow([row["D4C"], nomes.get(row["D4C"], row["D4N"]),
                        row["D3N"], row["V"], row["D2N"]])
    registrar_proveniencia(
        "IBGE/SIDRA", "CEMPRE tabela 9528 — unidades locais e pessoal por seção CNAE, Araguari/MG",
        url_9528, "Dados públicos IBGE (uso livre com citação da fonte)",
        None,
    )
    print(f"[SIDRA 9528] salvo (ano {dados_9528[1]['D2N']})")


# ---------------------------------------------------------------------------
# 2. Contorno do município (Nominatim) + POIs (Overpass), filtrados no polígono
# ---------------------------------------------------------------------------
def ponto_no_poligono(lon, lat, aneis):
    """Ray casting puro-stdlib (sem shapely): True se (lon,lat) está no polígono."""
    dentro = False
    for anel in aneis:
        n = len(anel)
        j = n - 1
        for i in range(n):
            xi, yi = anel[i][0], anel[i][1]
            xj, yj = anel[j][0], anel[j][1]
            if ((yi > lat) != (yj > lat)) and (lon < (xj - xi) * (lat - yi) / (yj - yi) + xi):
                dentro = not dentro
            j = i
    return dentro


def coletar_osm():
    # 2a. Contorno oficial do município (GeoJSON da relação OSM)
    url_nom = (f"https://nominatim.openstreetmap.org/lookup?osm_ids=R{OSM_RELATION_ID}"
               f"&format=json&polygon_geojson=1")
    info = http_get_json(url_nom)[0]
    gj = info["geojson"]
    aneis = []
    if gj["type"] == "Polygon":
        aneis = gj["coordinates"]
    elif gj["type"] == "MultiPolygon":
        for poly in gj["coordinates"]:
            aneis.append(poly[0])  # anel externo de cada parte
    with open(DATA_DIR / "municipio_contorno.json", "w", encoding="utf-8") as f:
        json.dump({"type": "MultiPolygon", "coordinates": [[a] for a in aneis]},
                  f, ensure_ascii=False)
    registrar_proveniencia(
        "OpenStreetMap/Nominatim", f"Contorno do município (relação OSM {OSM_RELATION_ID})",
        url_nom, "ODbL (© contribuidores OpenStreetMap)", len(aneis),
    )
    print(f"[OSM] contorno: {len(aneis)} anéis")

    # 2b. POIs comerciais no bbox (depois filtra dentro do município)
    query = (
        f"[out:json][timeout:150][bbox:{BBOX}];"
        "(node['shop'];way['shop'];"
        "node['amenity'~'^(restaurant|cafe|fast_food|bar|pub|ice_cream|pharmacy|bank|fuel|marketplace|clinic|doctors|dentist|veterinary)$'];"
        "way['amenity'~'^(restaurant|cafe|fast_food|pharmacy|bank|fuel|marketplace|clinic)$'];"
        "node['craft'];node['office'];);out tags center;"
    )
    resp = overpass_post(query)
    elems = resp.get("elements", [])
    print(f"[OSM] {len(elems)} elementos no bbox; filtrando no polígono...")

    dentro, sem_nome = [], 0
    for el in elems:
        lon = el.get("lon") or (el.get("center") or {}).get("lon")
        lat = el.get("lat") or (el.get("center") or {}).get("lat")
        if lon is None or lat is None:
            continue
        if not ponto_no_poligono(lon, lat, aneis):
            continue  # fora de Araguari (bbox retangular pega vizinhos)
        tags = el.get("tags", {})
        if not tags.get("name"):
            sem_nome += 1
            continue  # sem nome não serve ao mapeamento comercial
        dentro.append({
            "osm_tipo": el["type"], "osm_id": el["id"],
            "nome": tags.get("name"), "latitude": lat, "longitude": lon,
            "chave": ("shop" if "shop" in tags else
                      "amenity" if "amenity" in tags else
                      "craft" if "craft" in tags else "office"),
            "valor": tags.get("shop", tags.get("amenity", tags.get("craft", tags.get("office")))),
            "rua": tags.get("addr:street"), "numero": tags.get("addr:housenumber"),
            "bairro": tags.get("addr:suburb") or tags.get("addr:neighbourhood") or tags.get("addr:district"),
            "telefone": tags.get("phone") or tags.get("contact:phone"),
            "site": tags.get("website") or tags.get("contact:website"),
            "rede_social": (tags.get("contact:instagram") or tags.get("instagram")
                            or tags.get("contact:facebook") or tags.get("facebook")),
            "whatsapp": tags.get("contact:whatsapp") or tags.get("whatsapp"),
            "horario": tags.get("opening_hours"),
        })
    with open(DATA_DIR / "osm_pois_araguari.json", "w", encoding="utf-8") as f:
        json.dump(dentro, f, ensure_ascii=False, indent=1)
    registrar_proveniencia(
        "OpenStreetMap/Overpass",
        "Estabelecimentos comerciais georreferenciados dentro de Araguari/MG (com nome)",
        "https://overpass-api.de/api/interpreter (query shop/amenity/craft/office no bbox + filtro no polígono)",
        "ODbL (© contribuidores OpenStreetMap)", len(dentro),
    )
    print(f"[OSM] {len(dentro)} POIs com nome DENTRO de Araguari ({sem_nome} sem nome descartados)")

    # 2c. Bairro via geocodificação reversa (só p/ quem não tem addr:suburb; 1 req/s)
    sem_bairro = [p for p in dentro if not p["bairro"]]
    print(f"[OSM] completando bairro de {len(sem_bairro)} POIs via Nominatim reverse...")
    for i, p in enumerate(sem_bairro):
        url_rev = (f"https://nominatim.openstreetmap.org/reverse?lat={p['latitude']}"
                   f"&lon={p['longitude']}&format=json&zoom=16")
        try:
            addr = http_get_json(url_rev).get("address", {})
            p["bairro"] = (addr.get("suburb") or addr.get("neighbourhood")
                           or addr.get("city_district") or addr.get("quarter"))
            p["bairro_fonte"] = "nominatim_reverse" if p["bairro"] else None
        except Exception:
            p["bairro_fonte"] = None
        time.sleep(1.1)  # política de uso do Nominatim: máx. 1 req/s
        if (i + 1) % 20 == 0:
            print(f"  ... {i+1}/{len(sem_bairro)}")
    for p in dentro:
        p.setdefault("bairro_fonte", "osm_tag" if p["bairro"] else None)
    with open(DATA_DIR / "osm_pois_araguari.json", "w", encoding="utf-8") as f:
        json.dump(dentro, f, ensure_ascii=False, indent=1)
    n_bairro = sum(1 for p in dentro if p["bairro"])
    registrar_proveniencia(
        "OpenStreetMap/Nominatim (reverse)",
        "Bairro dos POIs sem addr:suburb (geocodificação reversa das coordenadas)",
        "https://nominatim.openstreetmap.org/reverse",
        "ODbL (© contribuidores OpenStreetMap)", n_bairro,
    )
    print(f"[OSM] bairro conhecido em {n_bairro}/{len(dentro)} POIs")


# ---------------------------------------------------------------------------
# 3. Webscraping real: infobox da Wikipédia "Araguari" (HTML público, CC BY-SA)
# ---------------------------------------------------------------------------
def coletar_wikipedia():
    from bs4 import BeautifulSoup  # import tardio: só esta etapa precisa de scraping HTML
    import urllib.request as req

    url = "https://pt.wikipedia.org/wiki/Araguari"
    r = req.Request(url, headers={**UA, "Accept-Language": "pt-BR,pt;q=0.9"})
    with req.urlopen(r, timeout=60) as resp:
        html = resp.read()
    soup = BeautifulSoup(html, "html.parser")
    info = {}
    infobox = soup.find("table", class_=lambda c: c and "infobox" in c)
    if infobox:
        for tr in infobox.find_all("tr"):
            th, td = tr.find("th"), tr.find("td")
            if th and td:
                chave = th.get_text(" ", strip=True)
                valor = td.get_text(" ", strip=True)
                if chave and valor:
                    info[chave] = valor
    # Resumo: primeiro parágrafo com conteúdo do artigo
    resumo = ""
    for p in soup.find_all("p"):
        txt = p.get_text(" ", strip=True)
        if len(txt) > 200:
            resumo = txt[:800]
            break
    with open(DATA_DIR / "municipio_wikipedia.json", "w", encoding="utf-8") as f:
        json.dump({"artigo": url, "infobox": info, "resumo": resumo},
                  f, ensure_ascii=False, indent=1)
    registrar_proveniencia(
        "Wikipédia (webscraping HTML com BeautifulSoup)",
        "Infobox do verbete Araguari (população, área, fundação etc.)",
        url, "CC BY-SA (texto da Wikipédia)", len(info),
    )
    print(f"[WIKI] {len(info)} campos da infobox coletados")


def main():
    t0 = time.time()
    coletar_sidra()
    coletar_osm()
    coletar_wikipedia()
    with open(DATA_DIR / "proveniencia.json", "w", encoding="utf-8") as f:
        json.dump(PROVENIENCIA, f, ensure_ascii=False, indent=2)
    print(f"[OK] coleta concluída em {time.time()-t0:.0f}s. Ver data/proveniencia.json")


if __name__ == "__main__":
    main()
