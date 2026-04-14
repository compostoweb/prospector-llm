# Unipile Webhook — Configuração e Funcionamento

## Visão geral

O sistema recebe eventos da Unipile via webhook para processar mensagens
inbound e aceites de conexão em **tempo real**. O webhook trabalha em conjunto
com o WebSocket interno para atualizar o frontend instantaneamente.

```
Unipile Cloud
     │  POST /webhooks/unipile
     ▼
FastAPI (webhook handler)
     │  valida HMAC-SHA256
     ├─► Salva Interaction no banco
     ├─► Classifica intent via ReplyParser (LLM)
     ├─► Atualiza status do lead
     ├─► Envia notificação (Resend)
     └─► Broadcast WebSocket → Frontend atualiza em tempo real
```

---

## Endpoint

```
POST /webhooks/unipile
```

Arquivo: `api/webhooks/unipile.py`

---

## Eventos tratados

| Source | Evento | Ação |
|---|---|---|
| `messaging` | `message_received` | Classifica intent, salva Interaction inbound, notifica, broadcast WS |
| `users` | `new_relation` | Marca lead como `connected`, cria ManualTasks se cadência semi-manual |
| `email` | `mail_received` | Processa resposta inbound de email via Gmail |
| `account_status` | `ok`, `reconnected`, `sync_success`, etc. | Log informativo e observabilidade da conta |
| qualquer outro | qualquer outro | Ignorado silenciosamente (retorna 200) |

---

## Configuração necessária no painel Unipile

### 1. URL do webhook

No painel da Unipile (https://dashboard.unipile.com), configurar:

- **Webhook URL**: `https://api.prospector.compostoweb.com.br/webhooks/unipile`
- **Sources/Eventos esperados pelo sistema**:
     - `messaging` → `message_received`
     - `users` → `new_relation`
     - `email` → `mail_received` quando houver conta Gmail conectada

Eventos de `account_status` como `ok`, `reconnected` e `sync_success` podem existir na sua workspace e aparecer no painel, mas são tratados como observabilidade da conexão, não como gatilhos principais de inbox ou cadência.

Também é possível registrar o webhook direto pela tela
`/configuracoes/unipile` usando o botão **Registrar via API da Unipile**.
Nesse caso, o backend cria os webhooks necessários por source (`messaging`, `users` e `email` quando aplicável) com headers:

- `Content-Type: application/json`
- `Unipile-Auth: <UNIPILE_WEBHOOK_SECRET>`

O registro automático só é liberado quando `API_PUBLIC_URL` aponta para uma
URL **HTTPS pública**. Endereços locais como `http://localhost:8000` são
bloqueados para evitar cadastrar um webhook inalcançável pela nuvem da Unipile.

O painel também consulta a lista de webhooks já cadastrados na Unipile para
mostrar de forma persistente quais sources já estão registrados para a URL atual,
incluindo os respectivos `webhook_id` quando disponíveis.

### 2. Variável de ambiente

Copiar o **Webhook Secret** gerado pela Unipile e adicionar ao `.env.prod`:

```env
UNIPILE_WEBHOOK_SECRET=seu_secret_aqui
```

No repositório atual, o arquivo alvo é `backend/.env.prod`.

> Em `ENV=dev` sem secret configurado, a validação de assinatura é ignorada
> (com warning no log). Em `ENV=prod`, requisições sem assinatura válida são
> rejeitadas com HTTP 401.

---

## Segurança — Validação HMAC-SHA256

A Unipile envia o header:

```
X-Unipile-Signature: sha256=<hex_digest>
```

O sistema valida com `hmac.compare_digest()` usando `UNIPILE_WEBHOOK_SECRET`.

Além do fluxo padrão do dashboard com `X-Unipile-Signature`, o backend também
aceita o header `Unipile-Auth` com o mesmo secret para webhooks criados via API,
como documentado em `https://developer.unipile.com/docs/webhooks-2`.

| Ambiente | Sem secret | Com secret inválido |
|---|---|---|
| `dev` | Aceita (warning no log) | Rejeita 401 |
| `prod` | Rejeita 401 (erro no log) | Rejeita 401 |

---

## Fluxo `message_received` (detalhado)

1. Extrai `text`, `unipile_message_id`, `sender_id`, `account_id` do payload
2. **Idempotência**: verifica se `unipile_message_id` já existe em `interactions`
3. Resolve o `tenant_id` pela `account_id` da Unipile; em ambiente com um único tenant ativo faz fallback automático
4. Localiza o lead por `linkedin_profile_id` → email corporativo → email pessoal dentro do tenant resolvido
5. Marca o `CadenceStep` enviado mais recente do mesmo canal como `REPLIED`
6. Resolve a configuração efetiva de LLM do tenant e classifica intent via `ReplyParser`
7. Salva `Interaction` com `direction=INBOUND`
8. Ações por intent:
     - `INTEREST` → `lead.status = CONVERTED` + notificação
     - `OBJECTION` → notificação
     - `NOT_INTERESTED` → `lead.status = ARCHIVED`
9. Broadcast WebSocket `inbox.new_message` → frontend invalida queries do inbox

---

## Fluxo `new_relation` (detalhado)

1. Extrai `linkedin_profile_id` e tenta resolver o tenant pela `account_id`
2. Localiza o lead no banco dentro do tenant resolvido
3. Atualiza `linkedin_connection_status = "connected"` e `linkedin_connected_at`
4. Se lead em cadência `semi_manual` → cria `ManualTasks` para próximos passos
5. Broadcast WebSocket `connection.accepted` → frontend atualiza

---

## WebSocket → Frontend

O webhook faz broadcast via `api/routes/ws.py` → `broadcast_event()`.
O frontend escuta em `lib/ws/use-events.ts` e:

- Invalida queries TanStack Query automaticamente (inbox, leads, tasks)
- Mostra notificações toast para eventos relevantes

Envelope enviado para o frontend:

```json
{
     "type": "inbox.new_message",
     "data": {
          "lead_id": "...",
          "lead_name": "...",
          "channel": "email",
          "intent": "interest",
          "text_preview": "..."
     },
     "tenant_id": "...",
     "timestamp": "2026-04-13T12:00:00+00:00"
}
```

Eventos legados como `new_message` e `connection_accepted` são normalizados no backend para manter compatibilidade com o frontend atual.

---

## Complemento: Polling com cache Redis

Quando o webhook não está configurado (ou como fallback), o frontend usa
polling via `GET /inbox/conversations` com cache Redis multi-nível:

| Nível | TTL | O que cacheia |
|---|---|---|
| Lista de conversas | 10 min | Response completa da listagem |
| Preview de mensagem | 5 min | Última mensagem de cada chat |
| Perfil de usuário | 24h | Nome/foto do LinkedIn |

O botão de sync (`POST /inbox/sync`) força resincronização da conta Unipile
e limpa os caches Redis do inbox.

Além disso, a lista do inbox no frontend mantém o resultado em cache por 5 minutos
e deixa de refazer fetch automático ao simplesmente trocar de tela e voltar.
Novas mensagens, envios e sync invalidam o cache explicitamente para buscar dados
frescos só quando realmente necessário.

---

## Checklist de deploy

- [ ] Configurar webhook URL no painel Unipile para `https://api.prospector.compostoweb.com.br/webhooks/unipile`
- [ ] Garantir o source `messaging` com evento `message_received`
- [ ] Garantir o source `users` com evento `new_relation`
- [ ] Garantir o source `email` com evento `mail_received` se houver Gmail conectado
- [ ] Definir `UNIPILE_WEBHOOK_SECRET` em `backend/.env.prod`
- [ ] Garantir que a porta/domínio está acessível externamente (HTTPS obrigatório)
- [ ] Testar com `curl -X POST https://api.prospector.compostoweb.com.br/webhooks/unipile` (deve retornar 401)
- [ ] Verificar logs com `structlog` para confirmar recebimento: `webhook.unipile.received`

---

## Migration em produção

O `.env.prod` desta base usa hostnames internos do EasyPanel, por exemplo
`chatwoot_bd_prospector_llm`, então a migration não roda a partir de uma máquina
local fora da rede interna do servidor.

Execute no container/app de produção:

```bash
cd /app/backend
ENV=prod python -m alembic upgrade head
```

Se quiser validar especificamente a nova migration antes do upgrade:

```bash
cd /app/backend
ENV=prod python -m alembic current
ENV=prod python -m alembic upgrade 059
ENV=prod python -m alembic current
```
