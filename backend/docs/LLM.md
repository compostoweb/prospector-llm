# LLM Multi-Provider — Guia completo

O Prospector suporta múltiplos provedores de LLM simultaneamente.
A escolha de provider e modelo é feita **por cadência** — cadências
diferentes podem usar modelos diferentes sem nenhuma mudança de código.

---

## Providers suportados

| Provider | SDK | Key necessária | Status |
|---|---|---|---|
| OpenAI | `openai >= 1.55` | `OPENAI_API_KEY` | ✅ Implementado |
| Google Gemini | `google-genai >= 1.0` | `GEMINI_API_KEY` | ✅ Implementado |
| Anthropic | — | — | 🔜 Futuro |
| Groq | — | — | 🔜 Futuro |

---

## Configuração

### Variáveis de ambiente

```bash
# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_DEFAULT_MODEL=gpt-4o-mini       # padrão global

# Gemini (key em: https://aistudio.google.com/app/apikey)
GEMINI_API_KEY=...
GEMINI_DEFAULT_MODEL=gemini-2.5-flash  # padrão global

# Reply Parser (fallback legado; os fluxos ativos resolvem o modelo pelo tenant)
REPLY_PARSER_PROVIDER=openai
REPLY_PARSER_MODEL=gpt-4o-mini
```

Ambas as keys podem coexistir. O sistema carrega apenas os providers
cujas keys estiverem presentes.

---

## Criando uma cadência com LLM específico

```http
POST /cadences
Content-Type: application/json

{
  "name": "Advocacia SP — alto volume",
  "llm": {
    "provider": "gemini",
    "model": "gemini-2.5-flash-lite",
    "temperature": 0.7,
    "max_tokens": 512
  }
}
```

```http
POST /cadences
Content-Type: application/json

{
  "name": "Escritórios premium — alto valor",
  "llm": {
    "provider": "openai",
    "model": "gpt-4o",
    "temperature": 0.8,
    "max_tokens": 800
  }
}
```

Se o campo `llm` for omitido, usa os defaults globais (`OPENAI_DEFAULT_MODEL`).

---

## Endpoints de gerenciamento

### Listar providers configurados
```http
GET /llm/providers
```
```json
{ "providers": ["openai", "gemini"] }
```

### Listar todos os modelos (cache Redis 1h)
```http
GET /llm/models
```
```json
{
  "providers": ["openai", "gemini"],
  "total": 28,
  "models": [
    {
      "id": "gemini-2.5-flash",
      "name": "Gemini 2.5 Flash",
      "provider": "gemini",
      "context_window": 1000000,
      "supports_json_mode": true,
      "price_input_per_mtok": 0.30,
      "price_output_per_mtok": 2.50
    },
    {
      "id": "gpt-4o-mini",
      "name": "GPT-4o Mini",
      "provider": "openai",
      "context_window": 0,
      "supports_json_mode": true,
      "price_input_per_mtok": 0.15,
      "price_output_per_mtok": 0.60
    }
  ]
}
```

### Filtrar por provider
```http
GET /llm/models/openai
GET /llm/models/gemini
```

### Forçar atualização do cache
```http
GET /llm/models?force_refresh=true
```

### Testar um modelo
```http
POST /llm/test
Content-Type: application/json

{
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "prompt": "Responda em 1 frase: qual é a capital do Brasil?",
  "temperature": 0.3,
  "max_tokens": 50
}
```
```json
{
  "text": "A capital do Brasil é Brasília.",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "input_tokens": 18,
  "output_tokens": 9,
  "ok": true
}
```

---

## Modelos recomendados por caso de uso

| Caso de uso | Provider | Modelo | Input $/MTok | Por quê |
|---|---|---|---|---|
| **Volume alto** | gemini | gemini-2.5-flash-lite | $0.10 | Mais barato disponível |
| **Padrão recomendado** | gemini | gemini-2.5-flash | $0.30 | Melhor custo/qualidade |
| **Padrão alternativo** | openai | gpt-4o-mini | $0.15 | JSON mode muito confiável |
| **Alto valor** | openai | gpt-4o | $2.50 | Máxima personalização |
| **Alto valor alt.** | gemini | gemini-2.5-pro | $1.25 | Context 1M + raciocínio |
| **Reply parser** | openai | gpt-4o-mini | $0.15 | JSON determinístico |

---

## Como funciona internamente

### LLMRegistry (singleton via Depends)

```python
# api/dependencies.py
@lru_cache(maxsize=1)
def get_llm_registry() -> LLMRegistry:
    return LLMRegistry(settings=settings, redis=redis_client)
```

O registry é criado uma vez no startup e reutilizado em todos os requests.

### Fluxo de uma completion

```
api/workers chama registry.complete(provider="gemini", model="gemini-2.5-flash", ...)
    ↓
LLMRegistry._get_provider("gemini") → GeminiProvider
    ↓
GeminiProvider.complete() → google-genai SDK → API Google
    ↓
LLMResponse(text, model, provider, input_tokens, output_tokens)
    ↓
services/ai_composer.py usa response.text
```

### Diferenças de API entre providers

| Aspecto | OpenAI | Gemini |
|---|---|---|
| System prompt | `messages[0].role = "system"` | `GenerateContentConfig(system_instruction=...)` |
| JSON mode | `response_format={"type":"json_object"}` | `config.response_mime_type = "application/json"` |
| Async | `AsyncOpenAI` nativo | `client.aio.models.generate_content()` |
| Modelos disponíveis | `GET /v1/models` | `client.models.list()` |

O `GeminiProvider` converte o formato `LLMMessage[]` para o formato `Content[]`
do Gemini automaticamente, separando o system prompt.

---

## Adicionando um novo provider

1. Criar `integrations/llm/novo_provider.py`:

```python
from integrations.llm.base import LLMProvider, LLMMessage, LLMResponse, ModelInfo

class NovoProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "novo"

    async def complete(self, messages, model, temperature, max_tokens, json_mode) -> LLMResponse:
        # implementar
        ...

    async def list_models(self) -> list[ModelInfo]:
        # implementar
        ...
```

2. Registrar em `integrations/llm/registry.py`:

```python
if settings.NOVO_API_KEY:
    self._providers["novo"] = NovoProvider(api_key=settings.NOVO_API_KEY)
```

3. Adicionar em `core/config.py`:
```python
NOVO_API_KEY: str = ""
```

4. Adicionar em `.env.example`:
```bash
NOVO_API_KEY=...
```

5. Atualizar `_VALID_PROVIDERS` e `_PROVIDER_MODEL_PREFIXES` em `schemas/cadence.py`.

Nenhum outro arquivo precisa mudar.

---

## SDK Gemini — atenção à versão

```python
# CORRETO — SDK GA (google-genai), disponível desde maio/2025
pip install google-genai>=1.0.0
from google import genai
from google.genai import types

# ERRADO — descontinuado em novembro/2025, sem novos recursos
pip install google-generativeai    # ← NÃO USAR
import google.generativeai as genai # ← NÃO USAR
```

O pacote antigo `google-generativeai` entrou em EOL (end-of-life) em
novembro/2025. O novo `google-genai` suporta Gemini Developer API e
Vertex AI com o mesmo código.
