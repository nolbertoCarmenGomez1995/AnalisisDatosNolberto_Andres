# =============================================================
# EVIDENCIA DE APRENDIZAJE 1 - ANÁLISIS Y HERRAMIENTAS DE EXTRACCIÓN DE DATOS
# Estudiantes: Nolberto Carmen Gómez y Andrés David Mesa
# Grupo: 19 | Institución: IU Digital de Antioquia
# Herramientas: BeautifulSoup4 + Selenium + Scrapy + Cloudscraper
# =============================================================

import time
import subprocess
import json
import os
import sys
import cloudscraper
from bs4 import BeautifulSoup
import pandas as pd

# Importaciones para Selenium
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

metricas_tiempos = {}

# =============================================================
# MÉTODO 1: BEAUTIFULSOUP4 + CLOUDSCRAPER + APIs VTEX
# =============================================================
def buscar_libros_beautifulsoup(termino_busqueda, max_por_tienda=5):
    """
    Busca libros en tiendas de Colombia por ISBN, Nombre de Autor o Título
    usando BeautifulSoup4 para parsing HTML y peticiones HTTP a catálogos VTEX.
    """
    inicio = time.time()
    scraper = cloudscraper.create_scraper()
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    resultados = []

    print(f"[Método 1 - BeautifulSoup] Buscando: '{termino_busqueda}'...")

    # 1.1 BUSCALIBRE COLOMBIA (Parsing HTML con BeautifulSoup)
    try:
        url_busca = f"https://www.buscalibre.com.co/libros/buscar?q={termino_busqueda}"
        resp = scraper.get(url_busca, headers=headers)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            items = soup.select('.producto, .v2-search-item, div.item')

            for item in items[:max_por_tienda]:
                tit = item.select_one('.tituloProducto, .nombre, .metatag-pro_title, h3, h2')
                prc = item.select_one('.precioAhora, .precio-ahora, .precio, span.precio')
                lnk = item.select_one('a')

                if tit:
                    resultados.append({
                        'Método': 'BeautifulSoup4',
                        'Tienda': 'BuscaLibre',
                        'Criterio': termino_busqueda,
                        'Título / Edición': tit.text.strip(),
                        'Precio_COP': prc.text.strip() if prc else 'N/A',
                        'Enlace': lnk['href'] if lnk and lnk.has_attr('href') else url_busca
                    })
    except Exception as e:
        print(f"Error en BuscaLibre (BS4): {e}")

    # 1.2 PANAMERICANA Y 1.3 LIBRERÍA NACIONAL (API VTEX - Catálogo JSON)
    tiendas_vtex = [
        ("Panamericana", f"https://www.panamericana.com.co/api/catalog_system/pub/products/search?ft={termino_busqueda}"),
        ("Librería Nacional", f"https://librerianacional.com/api/catalog_system/pub/products/search?ft={termino_busqueda}")
    ]

    for nombre_tienda, url_api in tiendas_vtex:
        try:
            resp = scraper.get(url_api, headers=headers)
            if resp.status_code in [200, 206] and resp.json():
                productos = resp.json()
                for prod in productos[:max_por_tienda]:
                    tit = prod.get('productTitle', 'N/A')
                    lnk = prod.get('link', 'N/A')
                    sellers = prod.get('items', [{}])[0].get('sellers', [{}])
                    precio_val = sellers[0].get('commertialOffer', {}).get('Price', 0) if sellers else 0

                    resultados.append({
                        'Método': 'BeautifulSoup4 / API',
                        'Tienda': nombre_tienda,
                        'Criterio': termino_busqueda,
                        'Título / Edición': tit,
                        'Precio_COP': f"${precio_val:,.0f} COP" if precio_val > 0 else 'Agotado / N/A',
                        'Enlace': lnk
                    })
        except Exception as e:
            print(f"Error en {nombre_tienda}: {e}")

    metricas_tiempos['BeautifulSoup4'] = round(time.time() - inicio, 3)
    return pd.DataFrame(resultados)


# =============================================================
# MÉTODO 2: SELENIUM (Automatización de Navegador Google Chrome)
# =============================================================
def buscar_libros_selenium(termino_busqueda, max_por_tienda=3):
    """
    Automatiza un navegador Google Chrome en modo Headless mediante Selenium
    para renderizar el DOM dinámico y extraer los elementos con selectores CSS.
    """
    inicio = time.time()
    resultados = []
    print(f"[Método 2 - Selenium] Renderizando navegador Chrome para: '{termino_busqueda}'...")

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    driver = None
    try:
        driver = webdriver.Chrome(options=chrome_options)
        url_busca = f"https://www.buscalibre.com.co/libros/buscar?q={termino_busqueda}"
        driver.get(url_busca)
        time.sleep(2)

        items = driver.find_elements(By.CSS_SELECTOR, ".producto, .v2-search-item, div.item")
        for item in items[:max_por_tienda]:
            try:
                tit = item.find_element(By.CSS_SELECTOR, ".tituloProducto, .nombre, h3, h2").text.strip()
            except:
                tit = ""
            try:
                prc = item.find_element(By.CSS_SELECTOR, ".precioAhora, .precio-ahora, .precio").text.strip()
            except:
                prc = "N/A"
            try:
                lnk = item.find_element(By.TAG_NAME, "a").get_attribute("href")
            except:
                lnk = url_busca

            if tit:
                resultados.append({
                    'Método': 'Selenium WebDriver',
                    'Tienda': 'BuscaLibre',
                    'Criterio': termino_busqueda,
                    'Título / Edición': tit,
                    'Precio_COP': prc,
                    'Enlace': lnk
                })
    except Exception as e:
        print(f"Nota en Selenium: {e}")
    finally:
        if driver:
            driver.quit()

    metricas_tiempos['Selenium'] = round(time.time() - inicio, 3)
    return pd.DataFrame(resultados)


# =============================================================
# MÉTODO 3: SCRAPY (Framework Asíncrono de Web Crawling)
# =============================================================
def buscar_libros_scrapy(termino_busqueda, max_por_tienda=3):
    """
    Crea y ejecuta un Spider de Scrapy para rastrear de forma asíncrona
    el catálogo y exportar los ítems extraídos.
    """
    inicio = time.time()
    print(f"[Método 3 - Scrapy] Ejecutando Spider asíncrono para: '{termino_busqueda}'...")
    archivo_salida = "scrapy_resultados.json"
    if os.path.exists(archivo_salida):
        os.remove(archivo_salida)

    codigo_spider = f'''
import scrapy

class LibrosSpider(scrapy.Spider):
    name = "libros_spider"
    custom_settings = {{
        "USER_AGENT": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "LOG_ENABLED": False
    }}
    start_urls = [
        "https://www.panamericana.com.co/api/catalog_system/pub/products/search?ft={termino_busqueda}"
    ]

    def parse(self, response):
        datos = response.json()
        for prod in datos[:{max_por_tienda}]:
            sellers = prod.get("items", [{{}}])[0].get("sellers", [{{}}])
            precio = sellers[0].get("commertialOffer", {{}}).get("Price", 0) if sellers else 0
            yield {{
                "Método": "Scrapy Spider",
                "Tienda": "Panamericana",
                "Criterio": "{termino_busqueda}",
                "Título / Edición": prod.get("productTitle", "N/A"),
                "Precio_COP": f"${{precio:,.0f}} COP" if precio > 0 else "Agotado / N/A",
                "Enlace": prod.get("link", "N/A")
            }}
'''
    with open("spider_libros.py", "w", encoding="utf-8") as f:
        f.write(codigo_spider)

    subprocess.run([sys.executable, "-m", "scrapy", "runspider", "spider_libros.py", "-O", archivo_salida], check=False)

    resultados = []
    if os.path.exists(archivo_salida):
        with open(archivo_salida, "r", encoding="utf-8") as f:
            try:
                resultados = json.load(f)
            except:
                resultados = []

    metricas_tiempos['Scrapy'] = round(time.time() - inicio, 3)
    return pd.DataFrame(resultados)


# =============================================================
# PRUEBAS DE EJECUCIÓN Y COMPARATIVA DE LOS 3 MÉTODOS
# =============================================================
if __name__ == "__main__":
    # Prueba 1: Búsqueda por Nombre de Autor (BeautifulSoup + APIs)
    df_autor = buscar_libros_beautifulsoup("Brandon Sanderson", max_por_tienda=3)
    print("\n=== 1. RESULTADOS POR AUTOR ('Brandon Sanderson') - BEAUTIFULSOUP ===")
    print(df_autor.to_string())

    # Prueba 2: Búsqueda del Artículo Seleccionado por ISBN Exacto con los 3 Métodos
    isbn_objetivo = "9786287737433"
    df_isbn_bs4 = buscar_libros_beautifulsoup(isbn_objetivo, max_por_tienda=3)
    df_isbn_sel = buscar_libros_selenium(isbn_objetivo, max_por_tienda=3)
    df_isbn_scr = buscar_libros_scrapy(isbn_objetivo, max_por_tienda=3)

    df_comparativo_isbn = pd.concat([df_isbn_bs4, df_isbn_sel, df_isbn_scr], ignore_index=True)
    print(f"\n=== 2. RESULTADOS POR ISBN ('{isbn_objetivo}') INTEGRANDO LOS 3 MÉTODOS ===")
    print(df_comparativo_isbn.to_string())

    # Resumen de Métricas de Desempeño
    df_metricas = pd.DataFrame([
        {"Método de Scraping": k, "Tiempo de Ejecución (s)": v}
        for k, v in metricas_tiempos.items()
    ])
    print("\n=== 3. MÉTRICAS DE TIEMPO DE EJECUCIÓN POR HERRAMIENTA ===")
    print(df_metricas.to_string())

    # Exportar todos los resultados consolidados a CSV
    df_final = pd.concat([df_autor, df_comparativo_isbn], ignore_index=True)
    df_final.to_csv("Gomez_Nolberto_Analizando_EA1.csv", index=False, encoding="utf-8-sig")
    print("\nArchivo 'Gomez_Nolberto_Analizando_EA1.csv' generado exitosamente en local.")