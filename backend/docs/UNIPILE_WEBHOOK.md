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

| Evento | Ação |
|---|---|
| `message_received` | Classifica intent, salva Interaction inbound, notifica, broadcast WS |
| `relation_created` | Marca lead como `connected`, cria ManualTasks se cadência semi-manual |
| `account_connected` | Log informativo |
| Outros | Ignorados silenciosamente (retorna 200) |

---

## Configuração necessária no painel Unipile

### 1. URL do webhook

No painel da Unipile (https://dashboard.unipile.com), configurar:

- **Webhook URL**: `https://SEU-DOMINIO/webhooks/unipile`
- **Eventos**: `message_received`, `relation_created`, `account_connected`

### 2. Variável de ambiente

Copiar o **Webhook Secret** gerado pela Unipile e adicionar ao `.env.prod`:

```env
UNIPILE_WEBHOOK_SECRET=seu_secret_aqui
```

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

| Ambiente | Sem secret | Com secret inválido |
|---|---|---|
| `dev` | Aceita (warning no log) | Rejeita 401 |
| `prod` | Rejeita 401 (erro no log) | Rejeita 401 |

---

## Fluxo `message_received` (detalhado)

1. Extrai `text`, `unipile_message_id`, `sender_id`, `account_id` do payload
2. **Idempotência**: verifica se `unipile_message_id` já existe em `interactions`
3. Localiza o lead por `linkedin_profile_id` → email corporativo → email pessoal
4. Resolve a configuração efetiva de LLM do tenant e classifica intent via `ReplyParser`
5. Salva `Interaction` com `direction=INBOUND`
6. Ações por intent:
   - `INTEREST` → `lead.status = CONVERTED` + notificação
   - `OBJECTION` → notificação
   - `NOT_INTERESTED` → `lead.status = ARCHIVED`
7. Broadcast WebSocket `new_message` → frontend invalida queries do inbox

---

## Fluxo `relation_created` (detalhado)

1. Extrai `linkedin_profile_id` do payload
2. Localiza o lead no banco
3. Atualiza `linkedin_connection_status = "connected"` e `linkedin_connected_at`
4. Se lead em cadência `semi_manual` → cria `ManualTasks` para próximos passos
5. Broadcast WebSocket `connection_accepted` → frontend atualiza

---

## WebSocket → Frontend

O webhook faz broadcast via `api/routes/ws.py` → `broadcast_event()`.
O frontend escuta em `lib/ws/use-events.ts` e:

- Invalida queries TanStack Query automaticamente (inbox, leads, tasks)
- Mostra notificações toast para eventos relevantes

---

## Complemento: Polling com cache Redis

Quando o webhook não está configurado (ou como fallback), o frontend usa
polling via `GET /inbox/conversations` com cache Redis multi-nível:

| Nível | TTL | O que cacheia |
|---|---|---|
| Lista de conversas | 2 min | Response completa da listagem |
| Preview de mensagem | 5 min | Última mensagem de cada chat |
| Perfil de usuário | 24h | Nome/foto do LinkedIn |

O botão de sync (`POST /inbox/sync`) força resincronização da conta Unipile
e limpa os caches Redis do inbox.

---

## Checklist de deploy

- [ ] Configurar webhook URL no painel Unipile
- [ ] Definir `UNIPILE_WEBHOOK_SECRET` no `.env.prod`
- [ ] Garantir que a porta/domínio está acessível externamente (HTTPS obrigatório)
- [ ] Testar com `curl -X POST https://seu-dominio/webhooks/unipile` (deve retornar 401)
- [ ] Verificar logs com `structlog` para confirmar recebimento: `webhook.unipile.received`
