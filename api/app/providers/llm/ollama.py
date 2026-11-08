"""Ollama structured generation with transport-only localhost fallback."""
import httpx
from ...config import Settings
from ...schemas import Answer, Passage
from ...services.prompt import messages
from .base import Generation, count_tokens


class OllamaProvider:
    name = 'ollama'

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, question: str, passages: list[Passage],
                 validation_error: str = '') -> Generation:
        prompt = messages(question, passages)
        if validation_error:
            prompt.append({'role': 'system', 'content': 'Previous output failed validation: '
                           + validation_error + '. Return valid JSON and only evidence citations.'})
        urls = [self.settings.ollama_url]
        if self.settings.ollama_url == 'http://host.minikube.internal:11434':
            urls.append('http://localhost:11434')
        with httpx.Client(timeout=120) as client:
            for index, url in enumerate(urls):
                try:
                    response = client.post(url+'/api/chat', json={
                        'model': self.settings.llm_model, 'messages': prompt,
                        'format': Answer.model_json_schema(), 'stream': False,
                        'options': {'temperature': self.settings.temperature,
                                    'num_ctx': 8192, 'num_predict': 512}})
                    response.raise_for_status()
                    data = response.json()
                    text = data['message']['content']
                    return Generation(text, int(data.get('prompt_eval_count', count_tokens(str(prompt)))),
                                      int(data.get('eval_count', count_tokens(text))))
                except httpx.TransportError:
                    if index == len(urls)-1:
                        raise
        raise RuntimeError('Ollama unavailable')
