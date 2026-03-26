"use client"

import { useState } from "react"
import {
  useSearchLinkedIn,
  useImportLinkedInProfiles,
  type LinkedInProfile,
} from "@/lib/api/hooks/use-leads"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Linkedin,
  Loader2,
  Search,
  UserPlus,
  CheckSquare,
  Square,
  ExternalLink,
} from "lucide-react"
import { cn } from "@/lib/utils"

export function LinkedInSearchDialog() {
  const [open, setOpen] = useState(false)

  // Campos de busca
  const [keywords, setKeywords] = useState("")
  const [location, setLocation] = useState("")
  const [industry, setIndustry] = useState("")
  const [companySize, setCompanySize] = useState("")

  // Resultados e seleção
  const [results, setResults] = useState<LinkedInProfile[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [cursor, setCursor] = useState<string | null>(null)
  const [importDone, setImportDone] = useState<{ created: number; skipped: number } | null>(null)

  const searchMutation = useSearchLinkedIn()
  const importMutation = useImportLinkedInProfiles()

  const isSearching = searchMutation.isPending
  const isImporting = importMutation.isPending

  function handleSearch(loadMore = false) {
    if (!keywords.trim()) return
    searchMutation.mutate(
      {
        keywords: keywords.trim(),
        location: location.trim() || undefined,
        industry: industry.trim() || undefined,
        company_size: companySize.trim() || undefined,
        limit: 25,
        cursor: loadMore ? (cursor ?? undefined) : undefined,
      },
      {
        onSuccess: (data) => {
          if (loadMore) {
            setResults((prev) => [...prev, ...data.items])
          } else {
            setResults(data.items)
            setSelected(new Set())
            setImportDone(null)
          }
          setCursor(data.cursor)
        },
      },
    )
  }

  function toggleSelect(id: string) {
    setSelected((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function toggleAll() {
    if (selected.size === results.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(results.map((p) => p.provider_id)))
    }
  }

  function handleImport() {
    const toImport = results.filter((p) => selected.has(p.provider_id))
    importMutation.mutate(
      { profiles: toImport },
      {
        onSuccess: (data) => {
          setImportDone({ created: data.created, skipped: data.skipped })
          setSelected(new Set())
        },
      },
    )
  }

  function handleClose() {
    setOpen(false)
    setKeywords("")
    setLocation("")
    setIndustry("")
    setCompanySize("")
    setResults([])
    setSelected(new Set())
    setCursor(null)
    setImportDone(null)
    searchMutation.reset()
    importMutation.reset()
  }

  const allSelected = results.length > 0 && selected.size === results.length

  return (
    <Dialog
      open={open}
      onOpenChange={(v) => {
        if (!v) handleClose()
        else setOpen(true)
      }}
    >
      <DialogTrigger asChild>
        <Button variant="outline" size="sm" className="gap-1.5">
          <Linkedin size={14} />
          Buscar no LinkedIn
        </Button>
      </DialogTrigger>

      <DialogContent className="max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Linkedin size={16} className="text-[#0A66C2]" />
            Buscar perfis no LinkedIn
          </DialogTitle>
        </DialogHeader>

        {/* Formulário de busca */}
        <div className="grid grid-cols-2 gap-3 py-2">
          <div className="col-span-2 space-y-1">
            <Label htmlFor="li-keywords">Palavras-chave *</Label>
            <div className="flex gap-2">
              <Input
                id="li-keywords"
                placeholder="Ex: CTO SaaS, Head de Marketing, Founder B2B"
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                disabled={isSearching}
              />
              <Button
                onClick={() => handleSearch()}
                disabled={!keywords.trim() || isSearching}
                size="sm"
                className="shrink-0"
              >
                {isSearching ? (
                  <Loader2 size={14} className="animate-spin" />
                ) : (
                  <Search size={14} />
                )}
              </Button>
            </div>
          </div>

          <div className="space-y-1">
            <Label htmlFor="li-location">Localização</Label>
            <Input
              id="li-location"
              placeholder="Ex: São Paulo, Brasil"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              disabled={isSearching}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="li-industry">Setor</Label>
            <Input
              id="li-industry"
              placeholder="Ex: Software, Saúde, Financeiro"
              value={industry}
              onChange={(e) => setIndustry(e.target.value)}
              disabled={isSearching}
            />
          </div>

          <div className="space-y-1">
            <Label htmlFor="li-company-size">Porte da empresa</Label>
            <Input
              id="li-company-size"
              placeholder="Ex: 11-50, 51-200, 201-500"
              value={companySize}
              onChange={(e) => setCompanySize(e.target.value)}
              disabled={isSearching}
            />
          </div>
        </div>

        {/* Feedback de erro */}
        {searchMutation.isError && (
          <p className="text-sm text-(--status-error)">
            Erro na busca. Verifique se a conta LinkedIn está configurada em Configurações →
            Unipile.
          </p>
        )}

        {/* Feedback de importação concluída */}
        {importDone && (
          <div className="rounded-md border border-(--border-default) bg-(--bg-overlay) px-3 py-2 text-sm">
            <span className="font-medium text-(--text-primary)">{importDone.created}</span>
            <span className="text-(--text-secondary)">
              {" "}
              lead{importDone.created !== 1 ? "s" : ""} importado
              {importDone.created !== 1 ? "s" : ""}
            </span>
            {importDone.skipped > 0 && (
              <span className="text-(--text-tertiary)"> · {importDone.skipped} já existiam</span>
            )}
          </div>
        )}

        {/* Resultados */}
        {results.length > 0 && (
          <div className="flex flex-col gap-2 min-h-0 flex-1 overflow-hidden">
            {/* Barra de seleção */}
            <div className="flex items-center justify-between shrink-0">
              <button
                onClick={toggleAll}
                className="flex items-center gap-1.5 text-sm text-(--text-secondary) hover:text-(--text-primary) transition-colors"
              >
                {allSelected ? (
                  <CheckSquare size={14} className="text-(--accent)" />
                ) : (
                  <Square size={14} />
                )}
                {allSelected ? "Desmarcar todos" : "Selecionar todos"}
              </button>
              <span className="text-xs text-(--text-tertiary)">
                {results.length} resultado{results.length !== 1 ? "s" : ""}
                {selected.size > 0 && (
                  <span className="ml-2 text-(--text-secondary)">
                    · {selected.size} selecionado{selected.size !== 1 ? "s" : ""}
                  </span>
                )}
              </span>
            </div>

            {/* Lista de perfis */}
            <div className="overflow-y-auto flex-1 space-y-1.5 pr-1">
              {results.map((profile) => {
                const isSelected = selected.has(profile.provider_id)
                return (
                  <button
                    key={profile.provider_id}
                    onClick={() => toggleSelect(profile.provider_id)}
                    className={cn(
                      "w-full rounded-md border px-3 py-2.5 text-left transition-colors",
                      isSelected
                        ? "border-(--accent) bg-(--accent)/5"
                        : "border-(--border-default) bg-(--bg-surface) hover:border-(--border-hover)",
                    )}
                  >
                    <div className="flex items-start gap-3">
                      {/* Checkbox */}
                      <div className="mt-0.5 shrink-0">
                        {isSelected ? (
                          <CheckSquare size={15} className="text-(--accent)" />
                        ) : (
                          <Square size={15} className="text-(--text-tertiary)" />
                        )}
                      </div>

                      {/* Dados */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-sm text-(--text-primary) truncate">
                            {profile.name || "Nome não disponível"}
                          </span>
                          {profile.profile_url && (
                            <span
                              role="link"
                              onClick={(e) => {
                                e.stopPropagation()
                                window.open(
                                  profile.profile_url ?? "",
                                  "_blank",
                                  "noopener,noreferrer",
                                )
                              }}
                              className="shrink-0 text-(--text-tertiary) hover:text-[#0A66C2] transition-colors cursor-pointer"
                              title="Ver no LinkedIn"
                            >
                              <ExternalLink size={11} />
                            </span>
                          )}
                        </div>
                        {profile.headline && (
                          <p className="text-xs text-(--text-secondary) truncate mt-0.5">
                            {profile.headline}
                          </p>
                        )}
                        <div className="flex items-center gap-3 mt-1">
                          {profile.company && (
                            <span className="text-xs text-(--text-tertiary)">
                              {profile.company}
                            </span>
                          )}
                          {profile.location && (
                            <span className="text-xs text-(--text-tertiary)">
                              {profile.location}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </button>
                )
              })}

              {/* Carregar mais */}
              {cursor && (
                <button
                  onClick={() => handleSearch(true)}
                  disabled={isSearching}
                  className="w-full rounded-md border border-dashed border-(--border-default) py-2 text-sm text-(--text-tertiary) hover:text-(--text-secondary) hover:border-(--border-hover) transition-colors disabled:opacity-50"
                >
                  {isSearching ? (
                    <Loader2 size={13} className="animate-spin mx-auto" />
                  ) : (
                    "Carregar mais resultados"
                  )}
                </button>
              )}
            </div>
          </div>
        )}

        {/* Estado vazio após busca */}
        {!isSearching && results.length === 0 && searchMutation.isSuccess && (
          <p className="text-sm text-(--text-tertiary) py-4 text-center">
            Nenhum perfil encontrado para esta busca.
          </p>
        )}

        <DialogFooter className="shrink-0 pt-2">
          <Button variant="ghost" onClick={handleClose}>
            Fechar
          </Button>
          <Button
            onClick={handleImport}
            disabled={selected.size === 0 || isImporting}
            className="gap-1.5"
          >
            {isImporting ? <Loader2 size={14} className="animate-spin" /> : <UserPlus size={14} />}
            Salvar {selected.size > 0 ? `${selected.size} ` : ""}lead
            {selected.size !== 1 ? "s" : ""}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
