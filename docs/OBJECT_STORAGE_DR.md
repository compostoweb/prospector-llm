# Object Storage DR

Ultima atualizacao: 2026-05-02

## Objetivo

Versionar a rotina de verificacao e restore dos prefixos criticos do bucket S3/MinIO usados pelo produto.

## Prefixos criticos

- audio/
- lm-pdfs/
- lm-images/
- branding/
- content/

## Referencias de banco cobertas pelo verificador

- audio_files.s3_key
- content_posts.image_s3_key
- content_posts.video_s3_key
- content_gallery_images.image_s3_key
- content_articles.thumbnail_s3_key
- content_newsletters.cover_image_s3_key
- content_lead_magnets.file_url

## Script versionado

Arquivo:
- backend/scripts/verify_object_storage_restore.py

O script:
- abre o banco restaurado
- opcionalmente filtra por tenant slug
- resolve storage keys reais a partir das colunas persistidas
- executa head_object no bucket configurado
- retorna JSON com missing, parse_errors e exemplos por tipo de asset

Exemplo:

```powershell
Set-Location backend
c:/python314/python.exe .\scripts\verify_object_storage_restore.py \
  --database-url "$env:RESTORE_CHECK_DATABASE_URL" \
  --tenant-slug "$env:RESTORE_CHECK_TENANT_SLUG" \
  --limit-per-asset 25
```

## Procedimento de restore

1. Restaurar ou remontar o bucket alvo.
2. Validar policy e credenciais do bucket.
3. Executar o script versionado contra o banco restaurado.
4. Se houver missing, restaurar prefixo ou objeto a partir do mirror/offsite.
5. Rerodar o script ate zerar missing e parse_errors.

## Estrategia offsite recomendada

- Mirror frequente dos prefixos criticos para bucket secundario ou provedor/regiao diferente.
- Retencao minima de 7 a 14 dias para objetos sobrescritos ou removidos.
- Backup da configuracao de bucket e policies fora do host principal.

## Criterios de saida

- Todos os asset types verificados com missing = 0.
- Nenhum parse_error nas URLs mascaradas ou bucket URLs.
- Prefixos publicos continuam limitados a assets realmente publicos.