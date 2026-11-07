"""OpenAI-compatible JSON provider; credentials are environment-only."""
import httpx
from ...config import Settings
from ...schemas import Passage
from ...services.prompt import messages
from .base import Generation, count_tokens


class HostedProvider:
    name = 'hosted'

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def generate(self, question: str, passages: list[Passage],
                 validation_error: str = '') -> Generation:
        if not self.settings.llm_api_key or not self.settings.hosted_base_url:
            raise RuntimeError('hosted mode requires LLM_API_KEY and HOSTED_BASE_URL')
        prompt = messages(question, passages)
        if validation_error:
            prompt.append({'role': 'system', 'content': 'Previous output failed validation: '
                           + validation_error + '. Return valid JSON and only evidence citations.'})
        # Groq, OpenRouter and Gemini OpenAI-compatible URLs are selected by configuration.
        with httpx.Client(timeout=120) as client:
            response = client.post(self.settings.hosted_base_url.rstrip('/')+'/chat/completions',
                headers={'Authorization': 'Bearer '+self.settings.llm_api_key}, json={
                    'model': self.settings.llm_model, 'messages': prompt,
                    'temperature': self.settings.temperature,
                    'response_format': {'type': 'json_object'}})
            response.raise_for_status()
            data = response.json()
            text = data['choices'][0]['message']['content']
            usage = data.get('usage') or {}
            return Generation(text, int(usage.get('prompt_tokens', count_tokens(str(prompt)))),
                              int(usage.get('completion_tokens', count_tokens(text))))
