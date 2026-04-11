# Extensao de Navegador — LinkedIn Capture V1

## Objetivo

Fechar a V1 da extensao com um escopo unico e controlado:

- capturar posts do LinkedIn enquanto o usuario navega
- importar esse conteudo para o Prospector
- usar o backend existente do Content Hub como fonte de verdade

Fica explicitamente fora da V1:

- geracao de comentarios
- postagem no LinkedIn pela extensao
- interacao com inbox, DM ou convites
- enriquecimento automatico fora do fluxo de captura/importacao
- automacao de clique ou acao dentro do LinkedIn

## Escopo Fechado da V1

### Casos suportados

1. Capturar um post publico do LinkedIn a partir do feed ou da pagina de detalhe.
2. Revisar os dados extraidos antes de importar.
3. Escolher o destino da importacao:
   - biblioteca de referencias do Content Hub
   - sessao de engagement existente
4. Persistir auditoria da origem da captura.
5. Evitar duplicidade por URL canonica e identidade do post.

### Casos nao suportados na V1

1. Importar comentarios do post.
2. Capturar carrosseis/PDF/video com parsing binario completo.
3. Rodar scan de engagement pela extensao.
4. Escrever no DOM do LinkedIn alem de injetar o CTA da extensao.
5. Fazer login direto no LinkedIn pela extensao.

## Login na extensao

### Podemos fazer login com Google?

Sim. A recomendacao e permitir login com Google na extensao, mas mantendo o Google OAuth centralizado no backend.

### O que nao fazer

- nao autenticar o usuario direto contra APIs internas do Google a partir da extensao
- nao armazenar access token do Google na extensao
- nao duplicar a regra de allowlist de usuarios fora do backend
- nao tentar reaproveitar cookie HttpOnly da aplicacao web dentro da extensao

### Abordagem recomendada

Usar um fluxo de autenticacao em ponte, gerenciado pelo backend:

1. A extensao inicia uma sessao de login no backend.
2. O backend gera `state`, salva em Redis e devolve a URL de autorizacao Google.
3. A extensao abre o fluxo com `launchWebAuthFlow`.
4. O callback Google volta para um endpoint especifico do backend para extensao.
5. O backend valida o usuario com a mesma regra atual de allowlist.
6. O backend emite um grant temporario de uso unico.
7. A extensao troca esse grant pelo JWT normal da API.

Com isso, a regra de autenticacao continua unica no backend e a extensao recebe apenas o JWT da aplicacao, nao um token Google.

## Arquitetura da extensao

### Stack recomendada

- Manifest V3
- TypeScript
- React apenas no popup e na options page
- content scripts puros para leitura do DOM do LinkedIn
- service worker para auth, API client, fila local e telemetria leve

### Estrutura proposta

```text
extension/
  package.json
  tsconfig.json
  vite.config.ts
  public/
    manifest.json
  src/
    background/
      index.ts
      auth.ts
      api.ts
      storage.ts
    content/
      linkedin-feed.ts
      linkedin-post-detail.ts
      dom-parser.ts
      injector.ts
    popup/
      main.tsx
      app.tsx
    options/
      main.tsx
      app.tsx
    shared/
      contracts.ts
      linkedin-normalizer.ts
      types.ts
```

### Componentes

#### 1. Content script

Responsabilidades:

- detectar cards e paginas de post do LinkedIn
- extrair texto, URL, autor, headline e metricas visiveis
- injetar o CTA `Salvar no Prospector`
- mandar o payload bruto para o service worker

Regra:

- o content script nao fala direto com a API

#### 2. Service worker

Responsabilidades:

- manter sessao autenticada da extensao
- executar o fluxo OAuth com o backend
- normalizar e enriquecer o payload vindo do content script
- chamar os endpoints da API
- controlar retries leves e expiracao de sessao

#### 3. Popup

Responsabilidades:

- exibir estado de login
- mostrar preview do ultimo post detectado
- escolher destino da importacao
- confirmar importacao

#### 4. Options page

Responsabilidades:

- logout
- ambiente atual
- healthcheck simples da API
- configuracoes de debug da extensao

## Fluxos

### Fluxo 1 — login

1. Usuario clica em `Entrar com Google` no popup.
2. Service worker chama `POST /auth/extension/session/start`.
3. Backend retorna `authorization_url` e metadados da sessao.
4. Extensao abre o fluxo OAuth.
5. Backend recebe o callback, valida o usuario e grava grant temporario.
6. Extensao chama `POST /auth/extension/session/exchange`.
7. Backend retorna o JWT padrao da API.

### Fluxo 2 — captura para referencias

1. Usuario clica em `Salvar no Prospector` em um post do LinkedIn.
2. Content script extrai os dados visiveis do post.
3. Popup mostra preview e o destino `Biblioteca de referencias`.
4. Service worker chama `POST /content/extension/capture/linkedin-post`.
5. Backend cria ou mescla a referencia e registra auditoria.

### Fluxo 3 — captura para engagement

1. Usuario clica em `Salvar no Prospector`.
2. Popup permite selecionar uma sessao de engagement recente.
3. Service worker chama `POST /content/extension/capture/linkedin-post`.
4. Backend encaminha internamente para o fluxo de importacao de engagement.
5. Resposta informa se o item foi criado ou mesclado.

## Contratos com backend

### Endpoints atuais que a extensao pode reaproveitar

#### Autenticacao e contexto

- `GET /auth/me`
- `GET /api/content/linkedin/status`
- `GET /api/content/engagement/sessions`
- `GET /api/content/engagement/sessions/{session_id}`

#### Importacao ja existente

- `POST /api/content/references`
- `POST /api/content/engagement/posts/import?session_id={session_id}`

Esses endpoints sao suficientes para um prototipo, mas para a V1 fechada da extensao o ideal e criar uma facade propria para reduzir acoplamento com regras internas do Content Hub.

### Endpoints novos propostos para a V1

#### 1. Iniciar login da extensao

`POST /auth/extension/session/start`

Request:

```json
{
  "extension_id": "abcdefghijklmnopabcdefghijklmnop",
  "extension_version": "0.1.0",
  "browser": "chrome"
}
```

Response:

```json
{
  "auth_session_id": "uuid",
  "authorization_url": "https://accounts.google.com/...",
  "expires_in": 300
}
```

Responsabilidades do backend:

- gerar `state`
- guardar sessao temporaria em Redis
- usar o mesmo provider Google ja adotado na web

#### 2. Callback Google da extensao

`GET /auth/extension/google/callback`

Uso interno do fluxo OAuth. Esse endpoint nao e consumido manualmente pela extensao. Ele:

- valida `state`
- valida allowlist de usuario
- gera `grant_code` de uso unico
- redireciona para a URL de callback da extensao

Redirect final esperado:

```text
https://<extension-id>.chromiumapp.org/provider_cb?grant_code=... 
```

#### 3. Trocar grant por JWT da API

`POST /auth/extension/session/exchange`

Request:

```json
{
  "grant_code": "one-time-code",
  "extension_id": "abcdefghijklmnopabcdefghijklmnop"
}
```

Response:

```json
{
  "access_token": "jwt-da-api",
  "token_type": "bearer",
  "expires_at": "2026-04-10T12:00:00Z",
  "user": {
    "id": "uuid",
    "email": "user@empresa.com",
    "name": "Nome Usuario",
    "is_superuser": false
  }
}
```

#### 4. Bootstrap da extensao

`GET /api/content/extension/bootstrap`

Response:

```json
{
  "user": {
    "id": "uuid",
    "email": "user@empresa.com",
    "name": "Nome Usuario"
  },
  "linkedin": {
    "connected": true,
    "display_name": "Nome Autor"
  },
  "features": {
    "capture_reference": true,
    "capture_engagement": true
  },
  "recent_engagement_sessions": [
    {
      "id": "uuid",
      "status": "completed",
      "created_at": "2026-04-10T12:00:00Z"
    }
  ]
}
```

Objetivo:

- evitar que a extensao monte a home com varias chamadas soltas
- centralizar feature flags e estado minimo

#### 5. Captura/importacao unificada de post do LinkedIn

`POST /api/content/extension/capture/linkedin-post`

Request:

```json
{
  "destination": {
    "type": "reference",
    "session_id": null
  },
  "post": {
    "post_url": "https://www.linkedin.com/posts/...",
    "canonical_post_url": "https://www.linkedin.com/posts/...",
    "post_text": "texto capturado do post",
    "author_name": "Nome Sobrenome",
    "author_title": "CEO",
    "author_company": "Empresa X",
    "author_profile_url": "https://www.linkedin.com/in/...",
    "likes": 120,
    "comments": 18,
    "shares": 7,
    "post_type": "reference"
  },
  "client_context": {
    "captured_from": "feed",
    "page_url": "https://www.linkedin.com/feed/",
    "captured_at": "2026-04-10T12:00:00Z",
    "extension_version": "0.1.0"
  }
}
```

Response quando `destination.type = reference`:

```json
{
  "destination": "reference",
  "result": "created",
  "reference_id": "uuid",
  "dedup_key": "linkedin:url:hash"
}
```

Response quando `destination.type = engagement`:

```json
{
  "destination": "engagement",
  "result": "merged",
  "session_id": "uuid",
  "engagement_post_id": "uuid",
  "dedup_key": "linkedin:url:hash"
}
```

Com esse endpoint, a extensao nao precisa conhecer os detalhes de `ContentReferenceCreate` nem de `ImportExternalPostsRequest`.

## Mapeamento interno no backend

### Quando o destino for `reference`

O facade da extensao converte o payload para `ContentReferenceCreate` e usa a regra atual da biblioteca.

### Quando o destino for `engagement`

O facade da extensao converte o payload para `AddManualPostRequest` e usa `POST /content/engagement/posts/import` internamente.

### Auditoria adicional obrigatoria

Toda captura deve registrar:

- `source = extension_linkedin`
- URL original da pagina
- versao da extensao
- usuario autenticado
- resultado: criado, mesclado ou ignorado

## Item 5 — seguranca e operacao

### Seguranca

1. O Google OAuth continua no backend. A extensao nunca guarda token Google.
2. O redirect da extensao usa `grant_code` de uso unico com TTL curto em Redis.
3. O JWT da API fica em `chrome.storage.session`, nao em `storage.sync`.
4. Toda request da extensao envia:
   - `Authorization: Bearer <jwt>`
   - `X-Client-Platform: chrome_extension`
   - `X-Extension-Version: <versao>`
5. O backend deve aceitar apenas `extension_id` previamente autorizado por ambiente.

### Operacao

1. Criar feature flag `EXTENSION_LINKEDIN_CAPTURE_ENABLED`.
2. Expor um endpoint de bootstrap para kill switch remoto.
3. Registrar logs estruturados por evento:
   - `extension.auth.started`
   - `extension.auth.exchanged`
   - `extension.capture.received`
   - `extension.capture.imported`
   - `extension.capture.rejected`
4. Aplicar rate limit por usuario e por tenant no endpoint de captura.
5. Distribuir inicialmente fora da loja publica, com IDs separados por dev e prod.

### Politica de rollout

1. Ambiente dev com extension id proprio.
2. Ambiente prod com extension id proprio.
3. So liberar para usuarios allowlisted no backend.
4. So liberar a V1 para captura/importacao manual, sem automacao de interacao.

## Decisoes finais desta V1

1. A extensao sera exclusivamente de captura/importacao do LinkedIn.
2. O login sera com Google, mas mediado pelo backend.
3. O backend ganhara uma facade propria para a extensao, em vez de expor a extensao diretamente aos contratos internos.
4. O destino inicial suportado sera biblioteca de referencias e sessao de engagement existente.
5. Seguranca e operacao ficam fechadas com grant temporario, JWT da API, allowlist, feature flag e auditoria estruturada.