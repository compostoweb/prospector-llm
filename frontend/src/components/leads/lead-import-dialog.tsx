"use client"

import { useRef, useState } from "react"
import { useImportLeads, type ImportLeadItem } from "@/lib/api/hooks/use-leads"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Download, Loader2, Upload } from "lucide-react"

const MAX_PREVIEW = 10

/** Mapeamento de nomes de coluna do CSV → campo do ImportLeadItem */
const COLUMN_MAP: Record<string, keyof ImportLeadItem> = {
  name: "name",
  full_name: "name",
  nome: "name",
  first_name: "first_name",
  primeiro_nome: "first_name",
  last_name: "last_name",
  sobrenome: "last_name",
  job_title: "job_title",
  cargo: "job_title",
  company: "company",
  empresa: "company",
  company_domain: "company_domain",
  dominio: "company_domain",
  website: "website",
  site: "website",
  industry: "industry",
  setor: "industry",
  industria: "industry",
  company_size: "company_size",
  tamanho: "company_size",
  linkedin_url: "linkedin_url",
  linkedin: "linkedin_url",
  url: "linkedin_url",
  city: "city",
  cidade: "city",
  location: "location",
  localizacao: "location",
  segment: "segment",
  segmento: "segment",
  phone: "phone",
  telefone: "phone",
  email_corporate: "email_corporate",
  email_corporativo: "email_corporate",
  email_personal: "email_personal",
  email_pessoal: "email_personal",
  notes: "notes",
  notas: "notes",
  observacoes: "notes",
}

/** Colunas da planilha exemplo (cabeçalho) */
const TEMPLATE_COLUMNS = [
  "name",
  "first_name",
  "last_name",
  "job_title",
  "company",
  "company_domain",
  "website",
  "industry",
  "company_size",
  "linkedin_url",
  "city",
  "location",
  "segment",
  "phone",
  "email_corporate",
  "email_personal",
  "notes",
]

const TEMPLATE_EXAMPLE_ROW = [
  "João Silva",
  "João",
  "Silva",
  "CTO",
  "Acme Corp",
  "acme.com",
  "https://acme.com",
  "Tecnologia",
  "51-200",
  "https://linkedin.com/in/joaosilva",
  "São Paulo",
  "São Paulo - SP - Brasil",
  "Enterprise",
  "+5511999999999",
  "joao@acme.com",
  "joao.pessoal@gmail.com",
  "Lead quente via evento",
]

/** Escapa valor CSV: envolve em aspas duplas se contiver vírgula, aspas ou quebra de linha */
function csvEscape(value: string): string {
  if (value.includes(",") || value.includes('"') || value.includes("\n")) {
    return `"${value.replace(/"/g, '""')}"`
  }
  return value
}

function downloadTemplate() {
  const csv = [
    TEMPLATE_COLUMNS.map(csvEscape).join(","),
    TEMPLATE_EXAMPLE_ROW.map(csvEscape).join(","),
  ].join("\n")
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" })
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = "prospector_leads_template.csv"
  a.click()
  URL.revokeObjectURL(url)
}

/** Divide uma linha CSV respeitando campos entre aspas duplas */
function splitCSVLine(line: string): string[] {
  const result: string[] = []
  let current = ""
  let inQuotes = false

  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (inQuotes) {
      if (ch === '"' && line[i + 1] === '"') {
        current += '"'
        i++ // pula aspas escapada
      } else if (ch === '"') {
        inQuotes = false
      } else {
        current += ch
      }
    } else {
      if (ch === '"') {
        inQuotes = true
      } else if (ch === ",") {
        result.push(current.trim())
        current = ""
      } else {
        current += ch
      }
    }
  }
  result.push(current.trim())
  return result
}

function parseCSV(text: string): ImportLeadItem[] {
  const lines = text.split(/\r?\n/).filter((l) => l.trim())
  if (lines.length < 2) return []

  const firstLine = lines[0]
  if (!firstLine) return []
  const headers = splitCSVLine(firstLine).map((h) => h.toLowerCase())

  // Mapeia índice da coluna → campo
  const colMapping: { idx: number; field: keyof ImportLeadItem }[] = []
  headers.forEach((h, idx) => {
    const field = COLUMN_MAP[h]
    if (field) colMapping.push({ idx, field })
  })

  // Precisa pelo menos "name"
  if (!colMapping.some((c) => c.field === "name")) return []

  const items: ImportLeadItem[] = []
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (!line) continue
    const cols = splitCSVLine(line)
    const item: Record<string, string | null> = {}

    for (const { idx, field } of colMapping) {
      const val = cols[idx]
      if (val) item[field] = val
    }

    if (item.name) {
      items.push(item as unknown as ImportLeadItem)
    }
  }
  return items
}

/** Colunas mais relevantes para o preview  */
const PREVIEW_COLS: { key: keyof ImportLeadItem; label: string }[] = [
  { key: "name", label: "Nome" },
  { key: "company", label: "Empresa" },
  { key: "linkedin_url", label: "LinkedIn" },
  { key: "email_corporate", label: "Email Corp." },
]

export function LeadImportDialog() {
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<ImportLeadItem[]>([])
  const [error, setError] = useState<string | null>(null)
  const fileRef = useRef<HTMLInputElement>(null)
  const { mutate, isPending, data: result } = useImportLeads()

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    setError(null)
    setItems([])
    const file = e.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = () => {
      const parsed = parseCSV(reader.result as string)
      if (parsed.length === 0) {
        setError(
          "CSV inválido. O arquivo precisa ter pelo menos a coluna 'name'. Baixe a planilha exemplo para referência.",
        )
      } else {
        setItems(parsed)
      }
    }
    reader.readAsText(file)
  }

  function handleImport() {
    mutate(
      { items },
      {
        onSuccess: () => {
          // keep dialog open to show result
        },
      },
    )
  }

  function handleClose() {
    setOpen(false)
    setItems([])
    setError(null)
    if (fileRef.current) fileRef.current.value = ""
  }

  const showResult = !!result && !isPending

  return (
    <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : handleClose())}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <Upload size={14} aria-hidden="true" />
          Importar CSV
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Importar leads via CSV</DialogTitle>
        </DialogHeader>

        {/* Instruções + template */}
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-3">
            <p className="text-xs text-(--text-secondary)">
              O arquivo deve conter pelo menos a coluna <strong>name</strong>. Campos adicionais
              como <em>company</em>, <em>linkedin_url</em>, <em>email_corporate</em>,{" "}
              <em>job_title</em> etc. serão importados automaticamente.
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="shrink-0"
              onClick={downloadTemplate}
            >
              <Download size={14} aria-hidden="true" />
              Planilha exemplo
            </Button>
          </div>
          <label className="sr-only" htmlFor="csv-file">
            Arquivo CSV
          </label>
          <input
            id="csv-file"
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFile}
            className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-(--bg-overlay) file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-(--text-primary)"
          />
          {error && <p className="text-xs text-(--danger)">{error}</p>}
        </div>

        {/* Preview */}
        {items.length > 0 && !showResult && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-(--text-secondary)">
              Prévia — {items.length} lead{items.length > 1 ? "s" : ""} encontrado
              {items.length > 1 ? "s" : ""}
            </p>
            <div className="max-h-48 overflow-auto rounded border border-(--border)">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-(--border) bg-(--bg-overlay)">
                    {PREVIEW_COLS.map((col) => (
                      <th key={col.key} className="px-2 py-1 text-left font-medium">
                        {col.label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {items.slice(0, MAX_PREVIEW).map((item, i) => (
                    <tr key={i} className="border-b border-(--border) last:border-0">
                      {PREVIEW_COLS.map((col) => (
                        <td
                          key={col.key}
                          className="max-w-40 truncate px-2 py-1 text-(--text-secondary)"
                        >
                          {String(item[col.key] ?? "—")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
              {items.length > MAX_PREVIEW && (
                <p className="px-2 py-1 text-[11px] text-(--text-tertiary)">
                  +{items.length - MAX_PREVIEW} mais...
                </p>
              )}
            </div>
          </div>
        )}

        {/* Result */}
        {showResult && (
          <div className="space-y-1 rounded-md bg-(--bg-overlay) p-3 text-sm">
            <p className="font-medium text-(--text-primary)">Importação concluída</p>
            <p className="text-(--text-secondary)">
              {result.imported} importado{result.imported !== 1 ? "s" : ""}, {result.duplicates}{" "}
              duplicata{result.duplicates !== 1 ? "s" : ""}
            </p>
            {result.errors.length > 0 && (
              <ul className="mt-1 list-disc pl-4 text-xs text-(--danger)">
                {result.errors.slice(0, 5).map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            )}
          </div>
        )}

        <DialogFooter>
          <Button type="button" variant="ghost" size="sm" onClick={handleClose}>
            {showResult ? "Fechar" : "Cancelar"}
          </Button>
          {!showResult && (
            <Button size="sm" disabled={isPending || items.length === 0} onClick={handleImport}>
              {isPending && <Loader2 size={14} className="animate-spin" aria-hidden="true" />}
              Importar {items.length > 0 ? `(${items.length})` : ""}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
