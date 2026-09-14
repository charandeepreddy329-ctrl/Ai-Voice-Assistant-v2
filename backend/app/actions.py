from urllib.parse import quote_plus
from .models import NovaError

class DesktopActions:
    """Web actions return structured data. Never launch or execute server programs."""
    def __init__(self, llm): self.llm, self.result = llm, None
    def link(self, label, url):
        self.result = {'type':'link','label':label,'url':url}
        return f'{label} is ready. Use the link below to open it.'
    def search_google(self, query): return self.link('Search Google', 'https://www.google.com/search?q='+quote_plus(query))
    def search_youtube(self, query): return self.link('Search YouTube', 'https://www.youtube.com/results?search_query='+quote_plus(query))
    def open_website(self, name):
        sites = {'google':'https://www.google.com','youtube':'https://www.youtube.com','github':'https://github.com','wikipedia':'https://www.wikipedia.org','gmail':'https://mail.google.com','chatgpt':'https://chatgpt.com','linkedin':'https://www.linkedin.com'}
        url = sites.get(name.lower().strip())
        return self.link('Open '+name, url) if url else 'I can open Google, YouTube, GitHub, Gmail, ChatGPT, LinkedIn, or Wikipedia. You can also ask me to search.'
    def open_app(self, name): return 'A public website cannot launch your desktop apps. Please open the app on your device.'
    def create_python_file(self, command):
        code = self.llm.generate_python(command)
        if len(code) > 100_000:
            raise NovaError('The generated program is too large to download safely.')
        try:
            compile(code, 'nova_generated.py', 'exec')
        except (SyntaxError, ValueError):
            raise NovaError('The model produced invalid Python. Please try again.')
        self.result = {'type':'download','filename':'nova_generated.py','content':code}
        return 'Your Python file is ready to download. Review generated code before running it.'
