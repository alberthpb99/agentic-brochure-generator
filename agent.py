import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from concurrent.futures import ThreadPoolExecutor
from scraper import Website

# Cargamos la variable de entorno
load_dotenv()
api_key = os.getenv('OPENAI_API_KEY')
MODEL = 'gpt-4o-mini'
openai = OpenAI()


# ----------------------------------- System Prompts -----------------------------------
# Prompt para filtrar los links relevantes
link_system_prompt = """
Eres un asistente especializado en análisis de sitios web para la creación de folletos corporativos.

TU OBJETIVO:
Analizar la lista de enlaces proporcionada y seleccionar ÚNICAMENTE los 3 a 6 enlaces más relevantes para comprender la empresa (propuesta de valor, historia, cultura, servicios, productos o empleos).

REGLAS:
1. Excluye enlaces irrelevantes como: Términos y Condiciones, Políticas de Privacidad, Avisos Legales, Contacto general, Redes Sociales o enlaces `mailto:`.
2. Responde ÚNICAMENTE con un objeto JSON válido. No incluyas intros, explicaciones ni bloques de texto fuera del JSON.

FORMATO DE SALIDA REQUERIDO:
{
    "links": [
        {"type": "Sobre nosotros", "url": "https://dominio.com/about"},
        {"type": "Servicios", "url": "https://dominio.com/services"}
    ]
}
"""
# Prompt para realizar los resúmenes de las páginas secundarias
map_system_prompt = '''
Eres un asistente analista de texto corporativo. 
Tu tarea es extraer los datos clave del texto de la página web provista (servicios, productos, historia, propuesta de valor o cultura).
Sintetiza la información en un resumen conciso (máximo 200 palabras) sin perder datos importantes y retorna únicamente dicho resumen.
'''
# Prompt para crear el folleto/resumen
brochure_system_prompt = """
Eres un especialista en marketing corporativo y redacción publicitaria.
Tu objetivo es crear un folleto informativo, atractivo y profesional sobre la empresa utilizando el contenido del sitio web proporcionado.

REGLAS DE FORMATO (MARKDOWN):
1. Utiliza encabezados claros (`#`, `##`, `###`).
2. Incluye las siguientes secciones estratégicas:
   - **Visión General / Propuesta de Valor**: ¿Qué hace la empresa y qué problema resuelve?
   - **Servicios o Productos Principales**: Listas con viñetas destacando características clave.
   - **Cultura o Por qué elegirnos**: Lo que los diferencia en el mercado o su visión.
3. Mantén un tono profesional, entusiasta y persuasivo pero fundamentado estrictamente en los datos provistos.
4. NO inventes datos, enlaces o servicios que no aparezcan en el texto de origen.
"""


# ----------------------------------- Funciones Auxiliares -----------------------------------
# Función para concatenar el user prompt con los links del sitio web
def get_links_user_prompt(website):

    unique_links = sorted(list(set(website.links))) # Eliminamos duplicados
    links_text = "\n".join(unique_links)            
    
    user_prompt = f"""Analiza la siguiente lista de enlaces extraídos del sitio web: {website.url}

    Selecciona únicamente los enlaces más relevantes para crear el folleto según las instrucciones dadas.

    LISTA DE ENLACES:
    ---
    {links_text}
    ---
    """
    return user_prompt

# Función que hará la llamada a la api para seleccionar los links relevantes
def get_links_openAI(website):
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {'role':'system', 'content': link_system_prompt},
            {'role':'user', 'content': get_links_user_prompt(website)}
        ],
        response_format={"type": "json_object"}
    )
    result = response.choices[0].message.content
    return json.loads(result)

# Funcion para resumir el contenido de cada pagina secundaria.
def map_summarize_page(page_type, text_content):
    user_prompt = f'Página: {page_type}\nContenido:\n{text_content[:8000]}'
    try:
        response = openai.chat.completions.create(
            model=MODEL,
            messages=[
                {'role': 'system', 'content': map_system_prompt},
                {'role': 'user', 'content': user_prompt}
            ]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f'[Error al resumir {page_type}: {e}]'

# Función para hacer el web scraping y su respectivo resumen de cada página secundaria
def _process_link(link):
    link_type = link.get('type', 'Página Relevante')
    link_url = link.get('url')
    
    if not link_url:
        return ""
        
    try:
        subpage = Website(link_url)
        subpage_summary = map_summarize_page(link_type, subpage.get_contents())
        return f'--- RESUMEN SECCIÓN: {link_type} ({link_url}) ---\n{subpage_summary}\n\n'
    except Exception as e:
        return f'--- RESUMEN SECCIÓN: {link_type} ({link_url}) ---\n[No se pudo procesar: {e}]\n\n'
    
# Esta función toma las funciones definidas antes y retorna el contexto necesario para crear el brochure
def get_all_details(url):
    website = Website(url)
    
    landing_summary = map_summarize_page('Landing Page Principal', website.get_contents())    
    result = f'=== RESUMEN DE LANDING PAGE ({url}) ===\n{landing_summary}\n\n'

    links = get_links_openAI(website)
    links_relevantes = links.get('links', [])
    
    with ThreadPoolExecutor(max_workers=5) as executor:
        subpage_summaries = list(executor.map(_process_link, links_relevantes))
        
    result += "".join(subpage_summaries)

    return result

# Función que concatena el user prompt con la info obtenida por  get_all_details()
def get_brochure_user_prompt(company_name, url):
    details = get_all_details(url)
    
    user_prompt = f"""Analiza los resúmenes de la información extraída del sitio web de la empresa "{company_name}" ({url}) y genera un folleto corporativo en Markdown.

    INSTRUCCIONES:
    - Utiliza la información provista abajo para completar las secciones solicitadas en tus instrucciones del sistema (Visión General, Servicios/Productos, Cultura/Diferenciadores, etc.).
    - Si alguna sección (como Empleos o Cursos) no tiene información relevante en el texto, omítela o adáptala sin inventar datos.

    INFORMACIÓN REUNIDA:
    ---
    {details}
    ---
    """
    return user_prompt


# ----------------------------------- Función Principal -----------------------------------
# Esta función realiza la última llamada a la api para generar el folleto
def create_brochure(company_name, url):
    user_prompt = get_brochure_user_prompt(company_name, url)
    response = openai.chat.completions.create(
        model=MODEL,
        messages=[
            {'role':'system', 'content':brochure_system_prompt},
            {'role':'user', 'content':user_prompt}
            ]
        )
    
    return response.choices[0].message.content