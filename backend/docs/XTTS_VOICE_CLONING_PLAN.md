# Plan: Self-hosted Voice Cloning pt-BR (sem GPU) — XTTS v2

> **Status**: Aprovado — aguardando execução
> **Prioridade**: Fase futura (após Edge TTS estabilizar)
> **Decisão**: Usar XTTS v2 como container Docker separado com voice cloning zero-shot

---

## TL;DR

Implementar voice cloning self-hosted usando **Coqui XTTS v2** como container Docker separado (padrão Voicebox), integrado ao sistema via um novo `XTTSProvider`. XTTS v2 é o único modelo open-source com qualidade ultra-realista em pt-BR + voice cloning zero-shot (6s de áudio de referência) sem GPU. Será lento no CPU (~30-60s por frase), mas aceitável para dispatch async via Celery.

---

## Análise — Voice Cloning sem GPU em 2026

| Solução                    | RAM         | Tempo/frase (4 vCPU) | Qualidade pt-BR | Voice Cloning               | Licença     |
| -------------------------- | ----------- | -------------------- | --------------- | --------------------------- | ----------- |
| **XTTS v2 (Coqui TTS)**    | 2-3GB       | 30-60s               | ⭐⭐⭐⭐⭐      | Zero-shot (6s áudio)        | MPL 2.0     |
| OpenVoice v2               | 700MB-1.5GB | 5-15s                | ⭐⭐⭐          | Tone transfer (inferior)    | MIT         |
| F5-TTS                     | 2-3GB       | 20-40s               | ⭐⭐⭐⭐        | Zero-shot                   | CC BY-NC ⚠️ |
| Piper TTS                  | ~100MB      | <1s                  | ⭐⭐⭐⭐        | ❌ Requer treino c/ dataset | MIT         |
| Edge TTS (já implementado) | 0           | <2s                  | ⭐⭐⭐⭐⭐      | ❌ Não suporta              | Free        |

**Recomendação: XTTS v2** — único que combina voice cloning zero-shot + qualidade pt-BR ultra-realista.

---

## Restrições do VPS (4 vCPU / 8GB RAM)

- Stack atual (API + 5 workers + Redis + Beat) consome ~3-4GB
- XTTS v2 precisa de ~2-3GB RAM + CPU intensivo
- **Risco**: OOM se rodar tudo no mesmo host
- **Mitigação**: Deploy do XTTS como serviço separado no EasyPanel com resource limits, ou VPS dedicado ($5-10/mês)

## Volume de uso vs tempo de geração

- Rate limit: 40 LinkedIn DMs/dia
- Se 50% usam voice note: 20 notas × 60s = **20 min de CPU/dia**
- Celery dispatch é async — lead NÃO espera
- **Conclusão: viável para volume atual**

---

## Fases de Implementação

### Fase 1 — Container Docker XTTS v2

1. **Criar `backend/docker/xtts-server/`** — servidor FastAPI standalone que wraps Coqui TTS
   - `Dockerfile`: Python 3.12, instala `TTS>=0.22.0`, baixa modelo XTTS v2 no build
   - `server.py`: FastAPI app com endpoints:
     - `POST /synthesize` — text + voice_profile_id + speed + pitch → MP3 bytes
     - `POST /clone` — name + audio file → cria perfil de voz (salva speaker embedding)
     - `GET /voices` — lista perfis clonados
     - `DELETE /voices/{id}` — remove perfil
     - `GET /health` — healthcheck
   - `requirements.txt`: `TTS>=0.22.0`, `fastapi`, `uvicorn`, `python-multipart`
   - Volume Docker: `/app/voices/` para persistir speaker embeddings
   - Resource limits: `mem_limit: 3g`, `cpus: 2`

2. **Adicionar serviço ao `docker-compose.dev.yml` e `docker-compose.prod.yml`**
   - Porta: 17494 (próxima após Voicebox 17493)
   - Healthcheck: `/health`
   - Volume nomeado `xtts-voices` para persistência

### Fase 2 — Provider Backend

3. **Criar `backend/integrations/tts/xtts_provider.py`**
   - Seguir exatamente o padrão de `voicebox_provider.py`
   - httpx.AsyncClient apontando para `XTTS_BASE_URL`
   - Timeout: 120s (CPU é lento)
   - Implementar: `synthesize()`, `list_voices()`, `create_voice()`, `delete_voice()`

4. **Atualizar `backend/core/config.py`**
   - Adicionar `XTTS_ENABLED: bool = False`
   - Adicionar `XTTS_BASE_URL: str = "http://localhost:17494"`

5. **Registrar no `backend/integrations/tts/registry.py`**
   - Bloco condicional `if settings.XTTS_ENABLED`
   - Lazy import de `XTTSProvider`

### Fase 3 — Frontend

6. **Nenhuma mudança necessária!**
   - Provider "xtts" aparece automaticamente em `GET /tts/providers`
   - Vozes clonadas aparecem em `GET /tts/voices` com `provider: "xtts"`
   - Upload de clone funciona via `POST /tts/voices/xtts`
   - O `tts-config-form.tsx` já renderiza qualquer provider dinamicamente

### Fase 4 — Teste

7. **Testar clonagem da voz do Adriano**
   - Gravar ~10-15s de áudio falando português natural
   - Upload via endpoint de clone
   - Gerar voice notes de teste e comparar qualidade

---

## Arquivos a Criar

| Arquivo                                       | Descrição                                                   |
| --------------------------------------------- | ----------------------------------------------------------- |
| `backend/docker/xtts-server/Dockerfile`       | Imagem Docker com TTS + XTTS v2                             |
| `backend/docker/xtts-server/server.py`        | FastAPI wrapper do Coqui TTS (endpoints de síntese + clone) |
| `backend/docker/xtts-server/requirements.txt` | Dependências do container                                   |
| `backend/integrations/tts/xtts_provider.py`   | Provider seguindo padrão de `voicebox_provider.py`          |

## Arquivos a Modificar

| Arquivo                                | Mudança                                   |
| -------------------------------------- | ----------------------------------------- |
| `backend/core/config.py`               | Adicionar `XTTS_ENABLED`, `XTTS_BASE_URL` |
| `backend/integrations/tts/registry.py` | Registrar XTTSProvider                    |
| `backend/docker-compose.dev.yml`       | Adicionar serviço xtts-server             |
| `backend/docker-compose.prod.yml`      | Adicionar serviço xtts-server             |

---

## Verificação

1. `docker build -t xtts-server backend/docker/xtts-server/` → build OK
2. `curl http://localhost:17494/health` → 200
3. `GET /tts/providers` inclui "xtts"
4. Upload 10s áudio PT-BR → retorna voice profile
5. `POST /tts/test` com provider "xtts" → MP3 com voz clonada
6. `docker stats xtts-server` → confirmar <3GB RAM

---

## Decisões Técnicas

- **XTTS v2 sobre OpenVoice**: qualidade pt-BR muito superior, mesmo sendo mais lento
- **Container separado**: isolamento de RAM/CPU, não impacta a stack principal
- **Padrão Voicebox**: mesma arquitetura já comprovada (HTTP API + httpx client)
- **Porta 17494**: sequencial após Voicebox (17493)
- **XTTS_ENABLED=False por padrão**: só ativa quando container estiver rodando
- **Timeout 120s**: margem para CPU lento
- **Volume Docker para embeddings**: persistir vozes clonadas entre restarts
- **Sem migration**: `tts_provider` no cadence já é string livre
- **Sem mudança frontend**: arquitetura dinâmica de providers já suporta

## Considerações Futuras

1. **RAM do VPS**: 4vCPU/8GB pode ficar apertado. Opção segura: VPS dedicado de $5-10/mês
2. **Modelo ~1.8GB**: Download na primeira build. Cache Docker para builds seguintes
3. **Upgrade com GPU**: Se volume crescer (100+ notas/dia), mesmo provider/API, só muda hardware
