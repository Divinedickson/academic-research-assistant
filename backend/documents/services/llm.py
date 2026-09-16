from dataclasses import dataclass
from typing import Protocol

import requests
from django.conf import settings


class LLMError(Exception):
    pass


class LLMConfigurationError(LLMError):
    pass


class LLMAuthenticationError(LLMError):
    pass


class LLMRateLimitError(LLMError):
    pass


class LLMTimeoutError(LLMError):
    pass


class LLMProviderUnavailableError(LLMError):
    pass


@dataclass(frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(frozen=True)
class LLMResponse:
    content: str
    model: str


class LLMProvider(Protocol):
    model_name: str

    def generate(
        self,
        messages: list[LLMMessage],
        max_output_tokens: int,
        timeout_seconds: float,
    ) -> LLMResponse:
        ...


class GroqLLMProvider:
    def __init__(
        self,
        api_key=None,
        model_name=None,
        base_url=None,
        temperature=None,
        supported_models=None,
    ):
        self.api_key = api_key if api_key is not None else settings.LLM_API_KEY
        self.model_name = model_name or settings.LLM_MODEL
        self.base_url = (base_url or settings.LLM_API_BASE_URL).rstrip('/')
        self.temperature = settings.LLM_TEMPERATURE if temperature is None else temperature
        self.supported_models = supported_models or settings.LLM_GROQ_SUPPORTED_MODELS

    def _validate_configuration(self):
        if not self.api_key:
            raise LLMConfigurationError(
                'LLM provider is not configured. Add GROQ_API_KEY to backend/.env.',
            )

        if self.model_name not in self.supported_models:
            raise LLMConfigurationError(
                'Configured LLM model is not in the supported Groq model allowlist.',
            )

    def generate(self, messages, max_output_tokens, timeout_seconds):
        self._validate_configuration()

        payload = {
            'model': self.model_name,
            'messages': [
                {
                    'role': message.role,
                    'content': message.content,
                }
                for message in messages
            ],
            'max_tokens': max_output_tokens,
            'temperature': self.temperature,
        }

        try:
            response = requests.post(
                f'{self.base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json',
                },
                json=payload,
                timeout=timeout_seconds,
            )
        except requests.Timeout as exc:
            raise LLMTimeoutError('The LLM provider timed out. Please try again.') from exc
        except requests.RequestException as exc:
            raise LLMProviderUnavailableError(
                'The LLM provider is unavailable. Please try again later.',
            ) from exc

        if response.status_code in {401, 403}:
            raise LLMAuthenticationError('The LLM provider rejected the configured API key.')

        if response.status_code == 429:
            raise LLMRateLimitError('The LLM provider rate limit was reached. Please try again later.')

        if response.status_code >= 500:
            raise LLMProviderUnavailableError(
                'The LLM provider is unavailable. Please try again later.',
            )

        if response.status_code >= 400:
            raise LLMError('The LLM provider could not generate an answer.')

        try:
            data = response.json()
            content = data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError('The LLM provider returned an invalid response.') from exc

        if not isinstance(content, str) or not content.strip():
            raise LLMError('The LLM provider returned an empty response.')

        return LLMResponse(content=content.strip(), model=self.model_name)


def get_llm_provider():
    if settings.LLM_PROVIDER != 'groq':
        raise LLMConfigurationError('Configured LLM provider is not supported.')

    return GroqLLMProvider()
