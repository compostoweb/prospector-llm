# Google OAuth — Checklist exato para Dev e Prod

Este guia cobre dois fluxos que hoje usam o mesmo Google OAuth no backend:

- login web do sistema via Google
- login da extensao do navegador via Google, mediado pelo backend

Importante:

- o frontend nao fala com Google diretamente
- a extensao nao fala com Google diretamente
- o Google redireciona sempre para o backend
- o backend valida o usuario e depois redireciona para frontend ou extensao

## 1. Decisao recomendada no Google Console

Use um unico OAuth Client do tipo Web application para cada ambiente:

- 1 client para dev
- 1 client para prod

Nao misture dev e prod no mesmo client se quiser isolamento operacional e rollback limpo.

## 2. Projeto no Google Cloud

Para cada ambiente:

1. Acesse Google Cloud Console.
2. Crie ou selecione um projeto dedicado.
3. Ative a API Google Identity ou siga por APIs & Services.
4. Configure OAuth consent screen antes de criar a credencial.

## 3. OAuth Consent Screen

### Tipo de app

Escolha assim:

- Internal: se apenas usuarios do mesmo Google Workspace vao logar
- External: se havera usuarios fora do Workspace

Para a Composto Web, se o acesso for apenas interno, Internal e o mais simples.

### Campos minimos

Preencha:

- App name: Prospector
- User support email: email administrativo real
- Developer contact information: email administrativo real

### Escopos

Os fluxos atuais usam apenas:

- openid
- email
- profile

Nao adicione escopos Gmail, Drive ou qualquer outro aqui para esse login.

### Test users

Se o app estiver em Testing e for External, adicione todos os usuarios que vao testar:

- superadmin
- usuarios allowlisted na tabela users

## 4. Credentials

Em APIs & Services > Credentials:

1. Create Credentials
2. OAuth client ID
3. Application type: Web application

Nao use Chrome Extension como tipo de credencial neste fluxo atual.

## 5. Redirect URIs exatos

O backend hoje espera estes redirects.

### Dev

Adicione exatamente:

- http://localhost:8000/auth/google/callback
- http://localhost:8000/auth/extension/google/callback

### Prod

Troque api.seudominio.com.br pelo dominio real da API e adicione exatamente:

- https://api.seudominio.com.br/auth/google/callback
- https://api.seudominio.com.br/auth/extension/google/callback

Se a API de producao usar outro host, use esse host real. O valor precisa casar exatamente com o .env carregado no backend.

## 6. Authorized JavaScript origins

Para esta implementacao, nao sao obrigatorios para o login funcionar, porque o fluxo OAuth com Google termina no backend.

Se quiser cadastrar por organizacao, use:

### Dev

- http://localhost:3000
- http://localhost:8000

### Prod

- https://app.seudominio.com.br
- https://api.seudominio.com.br

Mas o ponto principal continua sendo os redirect URIs acima.

## 7. Variaveis de ambiente do backend

As variaveis relevantes ja existem em [backend/core/config.py](backend/core/config.py).

### Topologia recomendada para este projeto

Como o sistema hoje separa frontend e backend, a topologia recomendada para producao e:

- app web: https://prospector.compostoweb.com.br
- api: https://api.prospector.compostoweb.com.br

Os exemplos concretos abaixo usam essa topologia.

### Dev — backend/.env.dev

Checklist minimo:

```env
ENV=dev

API_PUBLIC_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]

GOOGLE_CLIENT_ID=seu-client-id-dev.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-dev
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=http://localhost:8000/auth/extension/google/callback

EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_DEV
```

Notas:

- EXTENSION_ALLOWED_IDS aceita lista separada por virgula
- se tiver um ID para Chrome e outro para Edge em dev, use ambos

Exemplo:

```env
EXTENSION_ALLOWED_IDS=abcdefghijklmnopabcdefghijklmnop,ponmlkjihgfedcbaponmlkjihgfedcba
```

### Prod — backend/.env.prod

Checklist minimo:

```env
ENV=prod

API_PUBLIC_URL=https://api.prospector.compostoweb.com.br
FRONTEND_URL=https://prospector.compostoweb.com.br
ALLOWED_ORIGINS=["https://prospector.compostoweb.com.br","https://api.prospector.compostoweb.com.br"]

GOOGLE_CLIENT_ID=seu-client-id-prod.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-prod
GOOGLE_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/extension/google/callback

EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_PROD
```

### Bloco pronto para backend/.env.prod

Se voce for usar exatamente o dominio informado, o bloco base fica assim:

```env
ENV=prod
DEBUG=false

API_PUBLIC_URL=https://api.prospector.compostoweb.com.br
FRONTEND_URL=https://prospector.compostoweb.com.br
ALLOWED_ORIGINS=["https://prospector.compostoweb.com.br","https://api.prospector.compostoweb.com.br"]

GOOGLE_CLIENT_ID=seu-client-id-prod.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-prod
GOOGLE_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/extension/google/callback

EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_PROD
```

## 8. Variaveis do frontend

O frontend nao precisa de GOOGLE_CLIENT_ID nem GOOGLE_CLIENT_SECRET.

No frontend, mantenha apenas o basico:

### Dev — frontend/.env.local

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events
NEXT_PUBLIC_APP_URL=http://localhost:3000
API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
```

### Prod

```env
NEXT_PUBLIC_API_URL=https://api.prospector.compostoweb.com.br
NEXT_PUBLIC_WS_URL=wss://api.prospector.compostoweb.com.br/ws/events
NEXT_PUBLIC_APP_URL=https://prospector.compostoweb.com.br
API_URL=https://api.prospector.compostoweb.com.br
NEXTAUTH_URL=https://prospector.compostoweb.com.br
```

### Bloco pronto para frontend em prod

```env
NEXT_PUBLIC_API_URL=https://api.prospector.compostoweb.com.br
NEXT_PUBLIC_WS_URL=wss://api.prospector.compostoweb.com.br/ws/events
NEXT_PUBLIC_APP_URL=https://prospector.compostoweb.com.br
API_URL=https://api.prospector.compostoweb.com.br
NEXTAUTH_URL=https://prospector.compostoweb.com.br
```

## 9. Variaveis da extensao

A extensao hoje nao depende de .env para autenticar em Google.

Ela usa:

- X-Extension-Id enviado automaticamente pelo runtime
- URL da API configuravel na options page
- allowlist no backend via EXTENSION_ALLOWED_IDS

Em desenvolvimento, a API base default da extensao esta em localhost. Em producao, ajuste a URL da API na options page ou gere build com valor padrao apropriado.

## 10. Checklist final de dev

1. Criar projeto dev no Google Cloud.
2. Configurar OAuth consent screen.
3. Criar OAuth Client do tipo Web application.
4. Adicionar os redirects:
   - http://localhost:8000/auth/google/callback
   - http://localhost:8000/auth/extension/google/callback
5. Preencher backend/.env.dev com GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET.
6. Preencher GOOGLE_REDIRECT_URI e GOOGLE_EXTENSION_REDIRECT_URI com localhost.
7. Habilitar EXTENSION_LINKEDIN_CAPTURE_ENABLED=true.
8. Preencher EXTENSION_ALLOWED_IDS com o ID real da extensao carregada no Chrome/Edge.
9. Garantir que o usuario testador esta cadastrado e ativo na tabela users.
10. Subir backend, frontend e carregar a extensao.

## 10.1 Bloco pronto para backend/.env.dev

```env
ENV=dev
DEBUG=true

API_PUBLIC_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
ALLOWED_ORIGINS=["http://localhost:3000","http://localhost:8000"]

GOOGLE_CLIENT_ID=seu-client-id-dev.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-dev
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=http://localhost:8000/auth/extension/google/callback

EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_DEV
```

## 10.2 Bloco pronto para frontend/.env.local em dev

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws/events
NEXT_PUBLIC_APP_URL=http://localhost:3000
API_URL=http://localhost:8000
NEXTAUTH_URL=http://localhost:3000
```

## 11. Checklist final de prod

1. Criar projeto prod no Google Cloud.
2. Configurar OAuth consent screen de prod.
3. Criar OAuth Client do tipo Web application.
4. Adicionar os redirects:
   - https://api.seudominio.com.br/auth/google/callback
   - https://api.seudominio.com.br/auth/extension/google/callback
5. Preencher backend/.env.prod com GOOGLE_CLIENT_ID e GOOGLE_CLIENT_SECRET de prod.
6. Ajustar FRONTEND_URL, API_PUBLIC_URL e ALLOWED_ORIGINS para os dominios reais.
7. Habilitar EXTENSION_LINKEDIN_CAPTURE_ENABLED=true so quando quiser liberar o rollout.
8. Preencher EXTENSION_ALLOWED_IDS com o ID real da extensao publicada ou empacotada de prod.
9. Garantir que os usuarios permitidos estao ativos na tabela users.
10. Validar login web e login da extensao separadamente apos deploy.

## 11.1 Redirect URIs exatos para o seu dominio de producao

No Google Console, usando a topologia recomendada, cadastre exatamente:

- https://api.prospector.compostoweb.com.br/auth/google/callback
- https://api.prospector.compostoweb.com.br/auth/extension/google/callback

## 11.2 Authorized origins recomendados para o seu dominio de producao

- https://prospector.compostoweb.com.br
- https://api.prospector.compostoweb.com.br

## 11.3 Bloco completo sugerido para backend/.env.prod

Este bloco ja vem com os hosts de producao aplicados. A ideia e voce copiar, colar em backend/.env.prod e preencher apenas os segredos e IDs reais.

```env
ENV=prod
DEBUG=false

# ============================================================
# BANCO E REDIS
# ============================================================
DATABASE_URL=postgresql+asyncpg://USER:PASSWORD@HOST:5432/prospector_prod
REDIS_URL=redis://REDIS_HOST:6379/0
CELERY_BROKER_URL=redis://REDIS_HOST:6379/1
CELERY_RESULT_BACKEND=redis://REDIS_HOST:6379/2

# ============================================================
# APP / SEGURANCA / CORS
# ============================================================
SECRET_KEY=TROQUE_POR_UMA_CHAVE_LONGA_E_ALEATORIA
API_PUBLIC_URL=https://api.prospector.compostoweb.com.br
FRONTEND_URL=https://prospector.compostoweb.com.br
TRACKING_BASE_URL=https://api.prospector.compostoweb.com.br
ALLOWED_ORIGINS=["https://prospector.compostoweb.com.br","https://api.prospector.compostoweb.com.br"]
SUPERUSER_EMAIL=adriano@compostoweb.com.br

# ============================================================
# GOOGLE OAUTH — LOGIN WEB + EXTENSAO
# ============================================================
GOOGLE_CLIENT_ID=seu-client-id-prod.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu-client-secret-prod
GOOGLE_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/google/callback
GOOGLE_EXTENSION_REDIRECT_URI=https://api.prospector.compostoweb.com.br/auth/extension/google/callback

# ============================================================
# EXTENSAO DO NAVEGADOR — LinkedIn Capture V1
# ============================================================
EXTENSION_LINKEDIN_CAPTURE_ENABLED=true
EXTENSION_CAPTURE_DAILY_LIMIT=250
EXTENSION_ALLOWED_IDS=SEU_EXTENSION_ID_PROD

# ============================================================
# LLM
# ============================================================
OPENAI_API_KEY=sk-...
OPENAI_DEFAULT_MODEL=gpt-5.1-mini

GEMINI_API_KEY=
GEMINI_DEFAULT_MODEL=gemini-2.5-flash

ANTHROPIC_API_KEY=
ANTHROPIC_DEFAULT_MODEL=claude-sonnet-4-6

REPLY_PARSER_PROVIDER=openai
REPLY_PARSER_MODEL=gpt-4o-mini

# ============================================================
# VOZ / TTS
# ============================================================
VOICE_PROVIDER=speechify
SPEECHIFY_API_KEY=
SPEECHIFY_VOICE_ID=
VOICEBOX_BASE_URL=http://localhost:17493
VOICEBOX_ENABLED=false
EDGE_TTS_ENABLED=true
EDGE_TTS_DEFAULT_VOICE=pt-BR-FranciscaNeural

# ============================================================
# UNIPILE
# ============================================================
UNIPILE_API_KEY=
UNIPILE_BASE_URL=https://api2.unipile.com:13246/api/v1
UNIPILE_ACCOUNT_ID_LINKEDIN=
UNIPILE_ACCOUNT_ID_GMAIL=
UNIPILE_WEBHOOK_SECRET=

# ============================================================
# APIFY
# ============================================================
APIFY_API_TOKEN=

# ============================================================
# EMAIL FINDERS
# ============================================================
PROSPEO_API_KEY=
HUNTER_API_KEY=
APOLLO_API_KEY=
ZEROBOUNCE_API_KEY=

# ============================================================
# CONTEXTO / WEB SCRAPING
# ============================================================
JINA_API_KEY=
FIRECRAWL_API_KEY=
TAVILY_API_KEY=

# ============================================================
# PIPEDRIVE
# ============================================================
PIPEDRIVE_API_TOKEN=
PIPEDRIVE_DOMAIN=compostoweb
PIPEDRIVE_STAGE_INTEREST=
PIPEDRIVE_STAGE_OBJECTION=
PIPEDRIVE_OWNER_ID=
PIPEDRIVE_NOTIFY_EMAIL=adriano@compostoweb.com.br

# ============================================================
# RESEND / EMAILS TRANSACIONAIS
# ============================================================
RESEND_API_KEY=
RESEND_FROM_EMAIL=Composto Web <site@compostoweb.com.br>
CONTENT_CALCULATOR_NOTIFY_EMAIL=adriano@compostoweb.com.br
CONTENT_CALCULATOR_NOTIFY_FROM_EMAIL=site@compostoweb.com.br
CONTENT_CALCULATOR_REPLY_TO_EMAIL=contato@compostoweb.com.br
COMPOSTO_WEB_LOGO_EMAIL_URL=

# ============================================================
# SENDPULSE / CONTENT HUB INBOUND
# ============================================================
SENDPULSE_API_KEY=
SENDPULSE_CLIENT_ID=
SENDPULSE_CLIENT_SECRET=
SENDPULSE_WEBHOOK_SECRET=
SENDPULSE_BASE_URL=https://api.sendpulse.com

# ============================================================
# S3 / MINIO
# ============================================================
S3_ENDPOINT_URL=
S3_ACCESS_KEY=
S3_SECRET_KEY=
S3_BUCKET=prospector
S3_REGION=us-east-1

# ============================================================
# LIMITES DIARIOS
# ============================================================
LIMIT_LINKEDIN_CONNECT=20
LIMIT_LINKEDIN_DM=40
LIMIT_EMAIL=300

# ============================================================
# FLOWER
# ============================================================
FLOWER_USER=admin
FLOWER_PASSWORD=TROQUE_AQUI

# ============================================================
# GOOGLE OAUTH — GMAIL SEND
# ============================================================
GOOGLE_CLIENT_ID_EMAIL=
GOOGLE_CLIENT_SECRET_EMAIL=
GOOGLE_REDIRECT_URI_EMAIL=https://api.prospector.compostoweb.com.br/email-accounts/google/callback
EMAIL_ACCOUNT_ENCRYPTION_KEY=

# ============================================================
# LINKEDIN NATIVE ACCOUNT STORAGE
# ============================================================
LINKEDIN_ACCOUNT_ENCRYPTION_KEY=

# ============================================================
# CONTENT HUB — LINKEDIN OAUTH
# ============================================================
LINKEDIN_CLIENT_ID=
LINKEDIN_CLIENT_SECRET=
LINKEDIN_REDIRECT_URI=https://api.prospector.compostoweb.com.br/api/content/linkedin/callback

# ============================================================
# CONTENT HUB — GERACAO / PAGINAS PUBLICAS
# ============================================================
CONTENT_GEN_PROVIDER=openai
CONTENT_GEN_MODEL=gpt-4o-mini
CONTENT_PUBLIC_BASE_URL=https://prospector.compostoweb.com.br
```

Notas sobre esse bloco:

- se API e workers estiverem no mesmo host ou rede privada, use o host real do Redis em vez de localhost
- se voce nao usa alguns provedores opcionais, pode deixar as chaves vazias
- para Gmail OAuth separado, o redirect de prod deve apontar para o host real da API
- CONTENT_PUBLIC_BASE_URL deve apontar para o frontend publico que servira landing pages e assets do Content Hub

## 12. Como descobrir e fixar o Extension ID

### Dev — descobrir o ID atual

1. Rode o build da extensao:
   - npm run extension:build
2. Abra chrome://extensions
3. Ative Developer mode
4. Clique em Load unpacked
5. Selecione a pasta extension/dist
6. Copie o campo ID exibido no card da extensao
7. Cole esse valor em backend/.env.dev na chave EXTENSION_ALLOWED_IDS

Exemplo:

```env
EXTENSION_ALLOWED_IDS=abcdefghijklmnopabcdefghijklmnop
```

### Dev — fixar o ID com o minimo de atrito

Opção prática:

1. Use sempre o mesmo perfil do Chrome para desenvolvimento.
2. Mantenha a mesma extensao carregada em chrome://extensions.
3. Rebuild a pasta extension/dist e clique em Reload na extensao.

Nesse modo, o ID tende a permanecer estavel para o seu ciclo local de desenvolvimento.

### Dev — fixar o ID de forma forte

Se quiser um ID realmente estavel entre reinstalacoes e distribuicao manual:

1. Gere um pacote assinado da extensao uma vez no Chrome ou Edge usando Pack extension.
2. Guarde o arquivo .pem gerado em local seguro.
3. Sempre empacote novas versoes usando o mesmo .pem.
4. Instale sempre o pacote derivado da mesma chave.

Resultado:

- o extension ID permanece o mesmo enquanto a mesma chave privada for reutilizada.

### Prod — descobrir e fixar o ID

Se for publicar na Chrome Web Store:

1. Gere a build final.
2. Suba a extensao no painel da Chrome Web Store.
3. Depois que o item for criado, copie o extension ID atribuido pela loja.
4. Preencha backend/.env.prod em EXTENSION_ALLOWED_IDS com esse valor.

Se for distribuir fora da loja:

1. Empacote a extensao com uma chave .pem dedicada de producao.
2. Guarde essa .pem em cofre seguro.
3. Reutilize sempre a mesma .pem em todos os pacotes futuros.
4. Use o ID desse pacote em EXTENSION_ALLOWED_IDS.

### Regra operacional para dev e prod

- dev deve ter seu proprio extension ID
- prod deve ter seu proprio extension ID
- nao reutilize o ID de dev em prod
- se usar Chrome e Edge com builds separadas, inclua ambos em EXTENSION_ALLOWED_IDS separados por virgula

## 12. Erros comuns

### redirect_uri_mismatch

Causa:

- URI no Google Console diferente da URI em GOOGLE_REDIRECT_URI ou GOOGLE_EXTENSION_REDIRECT_URI

### access_denied para usuario valido

Causa comum:

- app External em Testing sem test user cadastrado no Google Console

### login web funciona e extensao falha

Causa comum:

- faltou cadastrar /auth/extension/google/callback no Google Console
- EXTENSION_ALLOWED_IDS nao contem o ID da extensao carregada

### Google autentica mas backend bloqueia

Causa comum:

- usuario nao esta cadastrado ou ativo na tabela users

## 13. Valores que precisam casar exatamente

Os pares abaixo precisam ser identicos entre Google Console e backend:

- Google Console redirect URI web <-> GOOGLE_REDIRECT_URI
- Google Console redirect URI extensao <-> GOOGLE_EXTENSION_REDIRECT_URI
- dominio do app <-> FRONTEND_URL
- dominio da API <-> API_PUBLIC_URL
- ID real da extensao <-> EXTENSION_ALLOWED_IDS