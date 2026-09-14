# Creamos una clase para hacer el web-scraping
import requests
from bs4 import BeautifulSoup

class Website:
    """Clase encargada de extraer contenido de sitios web."""
    def __init__(self, url):
        self.url = url
        response = requests.get(url).content
        soup = BeautifulSoup(response, 'html.parser')
        self.title = soup.title.string if soup.title else "Sin título"
        if soup.body:
            for irrelevant in soup.body(["script", "style", "img", "input"]):
                irrelevant.decompose()
            self.text = soup.body.get_text(separator="\n", strip=True)
        else:
            self.text = ""
        links = [link.get('href') for link in soup.find_all('a')]
        self.links = [link for link in links if link]

    def get_contents(self):
        return f"Título de la Web:\n{self.title}\nContenido de la Web:\n{self.text}\n\n"