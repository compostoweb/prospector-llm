"use client"

import { useCallback, useRef, useState } from "react"
import * as XLSX from "xlsx"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { FileSpreadsheet, Upload, ArrowRight, Check, X } from "lucide-react"

// ── Tipos ─────────────────────────────────────────────────────────────

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** Called with the final list of LinkedIn profile URLs */
  onConfirm: (urls: string[]) => void
}

type Step = "upload" | "map" | "preview"

// ── Helpers ──────────────────────────────────────────────────────────

/** Patterns that suggest a column contains LinkedIn profile URLs */
const LINKEDIN_HINTS = [
  "linkedin",
  "linkedin_url",
  "linkedin url",
  "profile",
  "perfil",
  "url",
  "link",
]

function guessLinkedInColumn(headers: string[]): string | null {
  for (const hint of LINKEDIN_HINTS) {
    const found = headers.find((h) => h.toLowerCase().includes(hint))
    if (found) return found
  }
  return null
}

function isLinkedInProfileUrl(val: string): boolean {
  return /linkedin\.com\/(in|pub)\//i.test(val)
}

function parseWorkbook(file: File): Promise<{ headers: string[]; rows: string[][] }> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => {
      try {
        const data = e.target?.result
        if (!data) return reject(new Error("Arquivo vazio"))
        const wb = XLSX.read(data, { type: "array" })
        const firstSheetName = wb.SheetNames[0]
        if (!firstSheetName) return reject(new Error("Planilha não encontrada"))
        const ws = wb.Sheets[firstSheetName]
        if (!ws) return reject(new Error("Planilha não encontrada"))
        const raw = XLSX.utils.sheet_to_json<string[]>(ws, { header: 1 })
        if (raw.length < 1) return reject(new Error("Nenhuma linha encontrada"))
        const headers = (raw[0] as unknown[]).map((h) => String(h ?? ""))
        const rows = raw
          .slice(1)
          .map((r) => headers.map((_, idx) => String((r as unknown[])[idx] ?? "").trim()))
        resolve({ headers, rows })
      } catch (err) {
        reject(err instanceof Error ? err : new Error("Falha ao processar arquivo"))
      }
    }
    reader.onerror = () => reject(new Error("Falha ao ler arquivo"))
    reader.readAsArrayBuffer(file)
  })
}

// ── Component ─────────────────────────────────────────────────────────

export function CsvXlsImportDialog({ open, onOpenChange, onConfirm }: Props) {
  const [step, setStep] = useState<Step>("upload")
  const [headers, setHeaders] = useState<string[]>([])
  const [rows, setRows] = useState<string[][]>([])
  const [selectedColumn, setSelectedColumn] = useState<string>("")
  const [error, setError] = useState<string | null>(null)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  // Computed preview
  const extractedUrls = rows
    .map((row) => {
      const colIdx = headers.indexOf(selectedColumn)
      return colIdx >= 0 ? (row[colIdx] ?? "") : ""
    })
    .filter((v) => v.length > 0)

  const linkedInUrls = extractedUrls.filter(isLinkedInProfileUrl)
  const nonLinkedIn = extractedUrls.filter((v) => !isLinkedInProfileUrl(v))

  // ── File processing ──────────────────────────────────────────────

  async function processFile(file: File) {
    setError(null)
    const ext = file.name.split(".").pop()?.toLowerCase()
    if (!["csv", "xlsx", "xls"].includes(ext ?? "")) {
      setError("Formato não suportado. Use CSV, XLSX ou XLS.")
      return
    }
    try {
      const { headers: h, rows: r } = await parseWorkbook(file)
      setHeaders(h)
      setRows(r)
      const guess = guessLinkedInColumn(h)
      setSelectedColumn(guess ?? h[0] ?? "")
      setStep("map")
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao processar arquivo")
    }
  }

  // ── Drag & drop ──────────────────────────────────────────────────

  const handleDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(false)
    const file = e.dataTransfer.files[0]
    if (file) processFile(file)
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback(() => setIsDragging(false), [])

  // ── Confirm ──────────────────────────────────────────────────────

  function handleConfirm() {
    onConfirm(linkedInUrls)
    handleClose()
  }

  function handleClose() {
    onOpenChange(false)
    // Reset after animation
    setTimeout(() => {
      setStep("upload")
      setHeaders([])
      setRows([])
      setSelectedColumn("")
      setError(null)
    }, 200)
  }

  // ── Render ───────────────────────────────────────────────────────

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet size={18} />
            Importar URLs do LinkedIn via CSV / XLSX
          </DialogTitle>
        </DialogHeader>

        {/* Step: Upload */}
        {step === "upload" && (
          <div className="space-y-4">
            <div
              onDrop={handleDrop}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onClick={() => fileInputRef.current?.click()}
              className={`cursor-pointer rounded-xl border-2 border-dashed p-10 text-center transition-colors ${
                isDragging
                  ? "border-(--accent) bg-(--accent-subtle)"
                  : "border-(--border-default) hover:border-(--accent) hover:bg-(--bg-overlay)"
              }`}
            >
              <Upload
                size={32}
                className="mx-auto mb-3 text-(--text-tertiary)"
                aria-hidden="true"
              />
              <p className="text-sm font-medium text-(--text-primary)">
                Arraste um arquivo ou clique para selecionar
              </p>
              <p className="mt-1 text-xs text-(--text-tertiary)">CSV, XLSX ou XLS</p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv,.xlsx,.xls"
                aria-label="Selecionar arquivo CSV ou XLSX"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0]
                  if (file) processFile(file)
                  e.target.value = ""
                }}
              />
            </div>
            {error && (
              <p className="flex items-center gap-2 rounded-lg bg-(--error-subtle) px-3 py-2 text-sm text-(--error)">
                <X size={14} />
                {error}
              </p>
            )}
            <p className="text-xs text-(--text-tertiary)">
              A planilha precisa ter pelo menos uma coluna com URLs de perfil do LinkedIn
              (linkedin.com/in/…).
            </p>
          </div>
        )}

        {/* Step: Map column */}
        {step === "map" && (
          <div className="space-y-4">
            <p className="text-sm text-(--text-secondary)">
              Selecione qual coluna do arquivo contém as URLs do LinkedIn:
            </p>
            <Select value={selectedColumn} onValueChange={setSelectedColumn}>
              <SelectTrigger>
                <SelectValue placeholder="Escolher coluna" />
              </SelectTrigger>
              <SelectContent>
                {headers.map((h) => (
                  <SelectItem key={h} value={h}>
                    {h}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Mini preview of selected column values */}
            {selectedColumn && (
              <div className="rounded-lg border border-(--border-default) bg-(--bg-overlay) p-3">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-(--text-tertiary)">
                  Primeiros valores da coluna selecionada
                </p>
                <ul className="space-y-1">
                  {rows.slice(0, 5).map((row, i) => {
                    const idx = headers.indexOf(selectedColumn)
                    const val = idx >= 0 ? (row[idx] ?? "") : ""
                    return (
                      <li
                        key={i}
                        className="flex items-center gap-2 truncate text-xs text-(--text-secondary)"
                      >
                        {isLinkedInProfileUrl(val) ? (
                          <Check size={12} className="shrink-0 text-green-500" />
                        ) : (
                          <X size={12} className="shrink-0 text-(--text-tertiary)" />
                        )}
                        {val || <span className="italic text-(--text-tertiary)">vazio</span>}
                      </li>
                    )
                  })}
                </ul>
              </div>
            )}

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setStep("upload")}>
                Voltar
              </Button>
              <Button
                onClick={() => setStep("preview")}
                disabled={!selectedColumn || linkedInUrls.length === 0}
              >
                <ArrowRight size={14} />
                Ver preview ({linkedInUrls.length})
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Step: Preview */}
        {step === "preview" && (
          <div className="space-y-4">
            <div className="flex gap-4 text-sm">
              <span className="font-medium text-green-600">
                ✓ {linkedInUrls.length} URL(s) válidas
              </span>
              {nonLinkedIn.length > 0 && (
                <span className="text-(--text-tertiary)">{nonLinkedIn.length} ignoradas</span>
              )}
            </div>

            <div className="max-h-60 overflow-y-auto rounded-lg border border-(--border-default) bg-(--bg-overlay) p-3">
              <ul className="space-y-1">
                {linkedInUrls.map((url, i) => (
                  <li key={i} className="truncate text-xs text-(--text-secondary)">
                    <a
                      href={url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-(--accent) hover:underline"
                    >
                      {url}
                    </a>
                  </li>
                ))}
              </ul>
            </div>

            <p className="text-xs text-(--text-tertiary)">
              As URLs serão adicionadas ao campo &quot;URLs do LinkedIn&quot; da fonte de
              enriquecimento.
            </p>

            <DialogFooter className="gap-2">
              <Button variant="outline" onClick={() => setStep("map")}>
                Voltar
              </Button>
              <Button onClick={handleConfirm} disabled={linkedInUrls.length === 0}>
                <Check size={14} />
                Usar {linkedInUrls.length} URL(s)
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
