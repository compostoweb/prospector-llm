import { useEffect, useState } from "react";

import { EXTENSION_STORAGE_KEYS } from "../background/storage";
import { MESSAGE_TYPES } from "../shared/contracts";
import {
  buildCaptureRequest,
  buildPreviewKey,
  normalizeWhitespace,
} from "../shared/linkedin-normalizer";
import type {
  ActiveTabPostScanDiagnostic,
  ActiveTabPostScanResult,
  CaptureDestinationType,
  CapturePreview,
  CaptureResponse,
  EngagementSessionSummary,
  ExtensionState,
} from "../shared/types";

type ExtensionSurfaceMode = "popup" | "sidepanel";
type PopupStepKey = "selection" | "selected" | "destination" | "review";
type LoadStateOptions = {
  preferredSessionId?: string | null;
  showLoading?: boolean;
};
type ImportFailure = {
  candidateKey: string;
  label: string;
  message: string;
};

async function sendMessage<T>(message: object): Promise<T> {
  const response = (await chrome.runtime.sendMessage(message)) as {
    ok: boolean;
    data?: T;
    error?: string;
  };
  if (!response.ok) {
    throw new Error(response.error ?? "Erro desconhecido");
  }
  return response.data as T;
}

function truncateText(value: string, limit: number): string {
  return value.length > limit ? `${value.slice(0, limit)}...` : value;
}

export function PopupApp({
  surfaceMode = "popup",
}: {
  surfaceMode?: ExtensionSurfaceMode;
}) {
  const [state, setState] = useState<ExtensionState | null>(null);
  const [availablePosts, setAvailablePosts] = useState<CapturePreview[]>([]);
  const [scanDiagnostic, setScanDiagnostic] =
    useState<ActiveTabPostScanDiagnostic | null>(null);
  const [loadingPosts, setLoadingPosts] = useState(false);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeStep, setActiveStep] = useState<PopupStepKey>("selection");
  const [destination, setDestination] =
    useState<CaptureDestinationType>("reference");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);
  const [manualUrls, setManualUrls] = useState<Record<string, string>>({});
  const [importProgress, setImportProgress] = useState<string | null>(null);
  const [importFailures, setImportFailures] = useState<ImportFailure[]>([]);

  const selectedPreviews = state?.selected_previews ?? [];
  const selectedPreviewKeys = new Set(
    selectedPreviews.map((preview) => buildPreviewKey(preview)),
  );
  const sessions = state?.bootstrap?.recent_engagement_sessions ?? [];
  const discardReasonEntries = Object.entries(
    scanDiagnostic?.discard_reason_counts ?? {},
  ).sort((left, right) => right[1] - left[1]);
  const availableTextLimit = surfaceMode === "sidepanel" ? 190 : 140;
  const selectedTextLimit = surfaceMode === "sidepanel" ? 420 : 320;

  useEffect(() => {
    void loadState();
    void loadAvailablePosts();

    const handleStorageChange: Parameters<
      typeof chrome.storage.onChanged.addListener
    >[0] = (changes, areaName) => {
      if (areaName !== "local" && areaName !== "session") {
        return;
      }

      const changedKeys = Object.keys(changes);
      const stateStorageKeys = new Set<string>(
        Object.values(EXTENSION_STORAGE_KEYS),
      );
      if (!changedKeys.some((key) => stateStorageKeys.has(key))) {
        return;
      }

      if (changes[EXTENSION_STORAGE_KEYS.selectedPreviews]) {
        setState((current) =>
          current
            ? {
                ...current,
                selected_previews:
                  (changes[EXTENSION_STORAGE_KEYS.selectedPreviews]
                    ?.newValue as CapturePreview[] | undefined) ?? [],
              }
            : current,
        );
      }

      if (changes[EXTENSION_STORAGE_KEYS.preview]) {
        setState((current) =>
          current
            ? {
                ...current,
                preview:
                  (changes[EXTENSION_STORAGE_KEYS.preview]?.newValue as
                    | CapturePreview
                    | null
                    | undefined) ?? null,
              }
            : current,
        );
      }

      if (changes[EXTENSION_STORAGE_KEYS.preview]?.newValue) {
        setResultMessage("Seleção atualizada no LinkedIn.");
        void loadAvailablePosts();
      }

      void loadState({ showLoading: false });
    };

    chrome.storage.onChanged.addListener(handleStorageChange);

    return () => {
      chrome.storage.onChanged.removeListener(handleStorageChange);
    };
  }, []);

  useEffect(() => {
    setManualUrls((current) => {
      const next: Record<string, string> = {};
      for (const preview of selectedPreviews) {
        const candidateKey = buildPreviewKey(preview);
        next[candidateKey] = current[candidateKey] ?? preview.post_url ?? "";
      }
      return next;
    });
  }, [selectedPreviews]);

  useEffect(() => {
    if (selectedPreviews.length === 0 && activeStep !== "selection") {
      setActiveStep("selection");
    }
  }, [activeStep, selectedPreviews.length]);

  function applyState(
    nextState: ExtensionState,
    preferredSessionId?: string | null,
  ) {
    setState(nextState);
    const nextSessions = nextState.bootstrap?.recent_engagement_sessions ?? [];
    setSessionId((currentSessionId) => {
      if (
        preferredSessionId &&
        nextSessions.some((session) => session.id === preferredSessionId)
      ) {
        return preferredSessionId;
      }
      if (
        currentSessionId &&
        nextSessions.some((session) => session.id === currentSessionId)
      ) {
        return currentSessionId;
      }
      return nextSessions[0]?.id ?? null;
    });
  }

  async function loadState(options: LoadStateOptions = {}) {
    const { preferredSessionId = null, showLoading = true } = options;
    if (showLoading) {
      setLoading(true);
    }
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.GET_STATE,
      });
      applyState(nextState, preferredSessionId);
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao carregar estado",
      );
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  async function loadAvailablePosts() {
    setLoadingPosts(true);
    try {
      const scan = await sendMessage<ActiveTabPostScanResult>({
        type: MESSAGE_TYPES.GET_ACTIVE_TAB_SCAN,
      });
      setAvailablePosts(scan.posts);
      setScanDiagnostic(scan.diagnostic);
    } catch (nextError) {
      setScanDiagnostic(null);
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao ler posts da aba ativa",
      );
    } finally {
      setLoadingPosts(false);
    }
  }

  async function handleLogin() {
    setBusy("login");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.AUTH_LOGIN,
      });
      applyState(nextState);
      await loadAvailablePosts();
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha no login",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleTogglePreview(preview: CapturePreview) {
    const candidateKey = buildPreviewKey(preview);
    const isSelected = selectedPreviewKeys.has(candidateKey);
    setBusy("toggle-preview");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>(
        isSelected
          ? {
              type: MESSAGE_TYPES.REMOVE_CAPTURED_POST,
              payload: { candidateKey },
            }
          : {
              type: MESSAGE_TYPES.SAVE_CAPTURED_POST,
              payload: preview,
            },
      );
      applyState(nextState);
      setResultMessage(
        isSelected ? "Post removido da seleção." : "Post adicionado à seleção.",
      );
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao atualizar seleção",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleRemoveSelected(candidateKey: string) {
    setBusy("remove-preview");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.REMOVE_CAPTURED_POST,
        payload: { candidateKey },
      });
      applyState(nextState);
      setResultMessage("Post removido da seleção.");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao remover post",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleClearSelected() {
    setBusy("clear-selection");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.CLEAR_CAPTURED_POSTS,
      });
      applyState(nextState);
      setImportFailures([]);
      setResultMessage("Seleção limpa.");
      setActiveStep("selection");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao limpar seleção",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleCreateSession() {
    setBusy("create-session");
    setError(null);
    try {
      const session = await sendMessage<EngagementSessionSummary>({
        type: MESSAGE_TYPES.CREATE_ENGAGEMENT_SESSION,
      });
      setDestination("engagement");
      await loadState({ preferredSessionId: session.id });
      setResultMessage("Nova sessão de engagement criada.");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao criar sessão",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleLogout() {
    setBusy("logout");
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.AUTH_LOGOUT,
      });
      applyState(nextState);
      setImportFailures([]);
      setResultMessage(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha no logout",
      );
    } finally {
      setBusy(null);
    }
  }

  function handleUrlChange(candidateKey: string, value: string) {
    setManualUrls((current) => ({
      ...current,
      [candidateKey]: value,
    }));
  }

  function getEditablePostUrl(preview: CapturePreview): string {
    return manualUrls[buildPreviewKey(preview)] ?? preview.post_url ?? "";
  }

  async function handleImportSelected() {
    if (selectedPreviews.length === 0) {
      setError("Selecione ao menos um post antes de importar.");
      setActiveStep("selection");
      return;
    }

    if (destination === "engagement" && !sessionId) {
      setError("Selecione ou crie uma sessão de engagement antes de importar.");
      setActiveStep("destination");
      return;
    }

    const missingManualUrls = selectedPreviews.filter((preview) => {
      const candidateKey = buildPreviewKey(preview);
      return (
        !preview.post_url && !normalizeWhitespace(manualUrls[candidateKey])
      );
    });

    if (missingManualUrls.length > 0) {
      setError(
        `Preencha o link manual em ${missingManualUrls.length} ${missingManualUrls.length === 1 ? "post" : "posts"} antes de importar.`,
      );
      setActiveStep("review");
      return;
    }

    setBusy("batch-import");
    setError(null);
    setResultMessage(null);
    setImportFailures([]);

    const manifestVersion = chrome.runtime.getManifest().version;
    const failures: ImportFailure[] = [];
    let successCount = 0;

    try {
      for (const [index, preview] of selectedPreviews.entries()) {
        const candidateKey = buildPreviewKey(preview);
        setImportProgress(
          `Importando ${index + 1} de ${selectedPreviews.length}`,
        );

        try {
          const payload = buildCaptureRequest(
            preview,
            destination,
            destination === "engagement" ? sessionId : null,
            manifestVersion,
            getEditablePostUrl(preview),
          );
          await sendMessage<CaptureResponse>({
            type: MESSAGE_TYPES.IMPORT_CAPTURE,
            payload,
          });
          const nextState = await sendMessage<ExtensionState>({
            type: MESSAGE_TYPES.REMOVE_CAPTURED_POST,
            payload: { candidateKey },
          });
          applyState(nextState);
          setAvailablePosts((current) =>
            current.filter(
              (candidate) => buildPreviewKey(candidate) !== candidateKey,
            ),
          );
          successCount += 1;
        } catch (nextError) {
          failures.push({
            candidateKey,
            label: preview.author_name ?? "Autor não identificado",
            message:
              nextError instanceof Error
                ? nextError.message
                : "Falha ao importar post",
          });
        }
      }

      if (successCount > 0) {
        void loadAvailablePosts();
      }

      if (failures.length === 0) {
        setResultMessage(
          `${successCount} ${successCount === 1 ? "post importado" : "posts importados"} com sucesso.`,
        );
        setActiveStep("selection");
      } else {
        setImportFailures(failures);
        setError(
          `${failures.length} ${failures.length === 1 ? "post falhou" : "posts falharam"} durante a importação.`,
        );
        if (successCount > 0) {
          setResultMessage(
            `${successCount} ${successCount === 1 ? "post importado" : "posts importados"} antes das falhas.`,
          );
        }
      }
    } finally {
      setImportProgress(null);
      setBusy(null);
    }
  }

  function formatSessionLabel(session: EngagementSessionSummary): string {
    const sourceLabel = session.scan_source === "manual" ? "Manual" : "Scanner";
    const statusLabel =
      session.status === "running"
        ? "Em andamento"
        : session.status === "completed"
          ? "Concluída"
          : "Parcial";
    return `${sourceLabel} · ${statusLabel} · ${new Date(session.created_at).toLocaleString("pt-BR")}`;
  }

  const scanCountLabel = `${availablePosts.length} detectados`;
  const selectionCountLabel = `${selectedPreviews.length} selecionados`;
  const missingRequiredUrlCount = selectedPreviews.filter((preview) => {
    return (
      !preview.post_url && !normalizeWhitespace(getEditablePostUrl(preview))
    );
  }).length;
  const destinationStepLabel =
    destination === "reference" ? "Destino: referência" : "Destino: engagement";
  const reviewStepLabel =
    missingRequiredUrlCount > 0
      ? `${missingRequiredUrlCount} links pendentes`
      : "Lote pronto";

  return (
    <div
      className={`popup-shell ${surfaceMode === "sidepanel" ? "is-sidepanel" : ""}`}
    >
      <div className="popup-header">
        <div>
          <div className="popup-kicker">LinkedIn Capture V1</div>
          <h1 className="popup-title">Prospector</h1>
          <div className="popup-subtitle">
            Selecione vários posts, defina o destino e revise os links antes de
            importar.
          </div>
        </div>
        {state?.session ? (
          <button
            onClick={handleLogout}
            disabled={busy !== null}
            className="popup-button popup-button--secondary"
          >
            Sair
          </button>
        ) : null}
      </div>

      {loading ? <p>Carregando...</p> : null}
      {error ? (
        <p className="popup-feedback popup-feedback--error">{error}</p>
      ) : null}
      {resultMessage ? (
        <p className="popup-feedback popup-feedback--success">
          {resultMessage}
        </p>
      ) : null}
      {importProgress ? (
        <p className="popup-feedback popup-feedback--warning">
          {importProgress}
        </p>
      ) : null}

      {!state?.session && !loading ? (
        <div className="popup-stack">
          <p>
            Faça login com Google para liberar a captura e importação no
            Prospector.
          </p>
          <button
            onClick={handleLogin}
            disabled={busy !== null}
            className="popup-button popup-button--primary"
          >
            Entrar com Google
          </button>
        </div>
      ) : null}

      {state?.session ? (
        <div className="popup-stack popup-stack--wide">
          <section className="popup-card popup-card--account">
            <div className="popup-account-row">
              <div>
                <div className="popup-card-title">
                  {state.session.user.name ?? state.session.user.email}
                </div>
                <div className="popup-muted">{state.session.user.email}</div>
              </div>
              <div className="popup-status-pill">
                LinkedIn{" "}
                {state.bootstrap?.linkedin.connected ? "ok" : "pendente"}
              </div>
            </div>
          </section>

          <section className="popup-steps">
            <button
              type="button"
              onClick={() => setActiveStep("selection")}
              className={`popup-step ${activeStep === "selection" ? "is-active" : ""}`}
            >
              <span className="popup-step__header">
                <span className="popup-step__index">1</span>
                <span className="popup-step__title">Selecionar posts</span>
              </span>
              <span className="popup-step__meta">{scanCountLabel}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("selected")}
              disabled={selectedPreviews.length === 0}
              className={`popup-step ${activeStep === "selected" ? "is-active" : ""}`}
            >
              <span className="popup-step__header">
                <span className="popup-step__index">2</span>
                <span className="popup-step__title">Conferir selecionados</span>
              </span>
              <span className="popup-step__meta">{selectionCountLabel}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("destination")}
              disabled={selectedPreviews.length === 0}
              className={`popup-step ${activeStep === "destination" ? "is-active" : ""}`}
            >
              <span className="popup-step__header">
                <span className="popup-step__index">3</span>
                <span className="popup-step__title">Escolher destino</span>
              </span>
              <span className="popup-step__meta">{destinationStepLabel}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveStep("review")}
              disabled={selectedPreviews.length === 0}
              className={`popup-step ${activeStep === "review" ? "is-active" : ""}`}
            >
              <span className="popup-step__header">
                <span className="popup-step__index">4</span>
                <span className="popup-step__title">Revisar e importar</span>
              </span>
              <span className="popup-step__meta">{reviewStepLabel}</span>
            </button>
          </section>

          {activeStep === "selection" ? (
            <>
              <section className="popup-card">
                <div className="popup-card-title popup-card-title--spaced">
                  1. Posts detectados na página
                </div>
                <div className="popup-card-actions">
                  <div className="popup-inline-badge">{scanCountLabel}</div>
                  <button
                    onClick={() => void loadAvailablePosts()}
                    disabled={loadingPosts || busy !== null}
                    className="popup-button popup-button--secondary"
                  >
                    {loadingPosts ? "Atualizando..." : "Atualizar lista"}
                  </button>
                </div>
                {scanDiagnostic ? (
                  <div className="popup-diagnostic-summary popup-diagnostic-summary--compact">
                    <div className="popup-diagnostic-summary__row">
                      <span>Candidatos:</span>
                      <strong>
                        {scanDiagnostic.candidate_container_count}
                      </strong>
                    </div>
                    <div className="popup-diagnostic-summary__row">
                      <span>Posts aceitos:</span>
                      <strong>{scanDiagnostic.accepted_post_count}</strong>
                    </div>
                  </div>
                ) : null}
                {availablePosts.length === 0 ? (
                  <p className="popup-empty">
                    Nenhum post foi detectado na aba ativa. Abra um feed ou post
                    do LinkedIn e clique em Atualizar lista.
                  </p>
                ) : null}
                {availablePosts.length > 0 ? (
                  <div
                    className={`popup-post-list ${surfaceMode === "sidepanel" ? "is-sidepanel" : ""}`}
                  >
                    {availablePosts.map((candidate, index) => {
                      const candidateKey = buildPreviewKey(candidate);
                      const isSelected = selectedPreviewKeys.has(candidateKey);
                      return (
                        <button
                          key={`${candidateKey}-${index}`}
                          type="button"
                          onClick={() => void handleTogglePreview(candidate)}
                          disabled={busy !== null}
                          className={`popup-post-item ${isSelected ? "is-active" : ""}`}
                        >
                          <div className="popup-post-item__eyebrow">
                            {candidate.captured_from === "post_detail"
                              ? "Post detalhado"
                              : "Publicação no feed"}
                          </div>
                          <div className="popup-post-item__title">
                            {candidate.author_name ?? "Autor não identificado"}
                          </div>
                          <div className="popup-post-item__meta">
                            {candidate.author_title ?? "Sem headline visível"}
                          </div>
                          <div className="popup-post-item__text">
                            {truncateText(
                              candidate.post_text,
                              availableTextLimit,
                            )}
                          </div>
                          <div className="popup-post-item__footer">
                            {isSelected
                              ? "Remover da seleção"
                              : "Adicionar à seleção"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </section>

              <div className="popup-actions">
                <button
                  type="button"
                  onClick={() => setActiveStep("selected")}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--primary"
                >
                  Conferir selecionados
                </button>
              </div>

              {scanDiagnostic ? (
                <section className="popup-card">
                  <div className="popup-card-title popup-card-title--spaced">
                    Diagnóstico da detecção
                  </div>
                  <div className="popup-diagnostic-panel is-open">
                    <div className="popup-diagnostic-panel__content">
                      <div className="popup-meta">
                        Fonte: {scanDiagnostic.captured_from} · URL:{" "}
                        {scanDiagnostic.page_url ?? "indisponível"}
                      </div>
                      {discardReasonEntries.length > 0 ? (
                        <div className="popup-diagnostic-block">
                          <div className="popup-diagnostic-title">
                            Motivos de descarte
                          </div>
                          {discardReasonEntries.map(([reason, count]) => (
                            <div key={reason} className="popup-diagnostic-item">
                              <span>{reason}</span>
                              <strong>{count}</strong>
                            </div>
                          ))}
                        </div>
                      ) : null}
                    </div>
                  </div>
                </section>
              ) : null}
            </>
          ) : null}

          {activeStep === "selected" ? (
            <section className="popup-card">
              <div className="popup-card-title popup-card-title--spaced">
                2. Conferir posts selecionados
              </div>
              <div className="popup-meta popup-meta--spaced">
                Revise a curadoria antes de definir o destino do lote.
              </div>
              {selectedPreviews.length === 0 ? (
                <p className="popup-empty">
                  Nenhum post selecionado. Volte para a primeira etapa e monte o
                  lote.
                </p>
              ) : (
                <div className="popup-selected-list">
                  {selectedPreviews.map((preview) => {
                    const candidateKey = buildPreviewKey(preview);
                    return (
                      <div key={candidateKey} className="popup-selected-card">
                        <div className="popup-selected-card__header">
                          <div>
                            <div className="popup-selected-card__title">
                              {preview.author_name ?? "Autor não identificado"}
                            </div>
                            <div className="popup-muted">
                              {preview.author_title ?? "Sem headline visível"}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() =>
                              void handleRemoveSelected(candidateKey)
                            }
                            disabled={busy !== null}
                            className="popup-button popup-button--secondary"
                          >
                            Remover
                          </button>
                        </div>
                        <div className="popup-selected-card__body">
                          {truncateText(preview.post_text, 220)}
                        </div>
                        <div className="popup-selected-card__footer">
                          {preview.likes} curtidas · {preview.comments}{" "}
                          comentários · {preview.shares} compartilhamentos
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              <div className="popup-actions">
                <button
                  type="button"
                  onClick={() => setActiveStep("selection")}
                  disabled={busy !== null}
                  className="popup-button popup-button--secondary"
                >
                  Voltar
                </button>
                <button
                  type="button"
                  onClick={() => void handleClearSelected()}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--secondary"
                >
                  Limpar seleção
                </button>
                <button
                  type="button"
                  onClick={() => setActiveStep("destination")}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--primary"
                >
                  Continuar para destino
                </button>
              </div>
            </section>
          ) : null}

          {activeStep === "destination" ? (
            <section className="popup-card">
              <div className="popup-card-title popup-card-title--spaced">
                3. Destino do lote
              </div>
              <div className="popup-meta popup-meta--spaced">
                {selectionCountLabel}. Posts importados pela extensão entram
                como curadoria manual e não disparam análise por IA nesta etapa.
              </div>
              <div className="popup-segmented">
                <button
                  onClick={() => setDestination("reference")}
                  className={`popup-segment ${destination === "reference" ? "is-active" : ""}`}
                >
                  Referência
                </button>
                <button
                  onClick={() => setDestination("engagement")}
                  className={`popup-segment ${destination === "engagement" ? "is-active" : ""}`}
                >
                  Engagement
                </button>
              </div>
              {destination === "engagement" ? (
                <div className="popup-stack popup-stack--section">
                  <select
                    aria-label="Selecionar sessão de engagement"
                    value={sessionId ?? ""}
                    onChange={(event) =>
                      setSessionId(event.target.value || null)
                    }
                    className="popup-select"
                  >
                    <option value="">Selecione uma sessão</option>
                    {sessions.map((session) => (
                      <option key={session.id} value={session.id}>
                        {formatSessionLabel(session)}
                      </option>
                    ))}
                  </select>
                  <button
                    onClick={handleCreateSession}
                    disabled={busy !== null}
                    className="popup-button popup-button--secondary"
                  >
                    {busy === "create-session"
                      ? "Criando sessão..."
                      : "Nova sessão"}
                  </button>
                </div>
              ) : (
                <div className="popup-empty-card">
                  O lote será salvo como referência curada para consulta dentro
                  do Prospector.
                </div>
              )}
              <div className="popup-actions">
                <button
                  type="button"
                  onClick={() => setActiveStep("selected")}
                  disabled={busy !== null}
                  className="popup-button popup-button--secondary"
                >
                  Voltar
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (destination === "engagement" && !sessionId) {
                      setError(
                        "Selecione ou crie uma sessão de engagement antes de continuar.",
                      );
                      return;
                    }
                    setActiveStep("review");
                  }}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--primary"
                >
                  Continuar para revisão
                </button>
              </div>
            </section>
          ) : null}

          {activeStep === "review" ? (
            <section className="popup-card">
              <div className="popup-card-title popup-card-title--spaced">
                4. Revisar links e importar
              </div>
              <div className="popup-meta popup-meta--spaced">
                Revise o link de cada post. Quando a URL automática não vier, o
                preenchimento manual é obrigatório.
              </div>
              {selectedPreviews.length === 0 ? (
                <div className="popup-empty-card">
                  Nenhum post selecionado. Volte para a etapa anterior e monte o
                  lote.
                </div>
              ) : (
                <div className="popup-selected-list">
                  {selectedPreviews.map((preview) => {
                    const candidateKey = buildPreviewKey(preview);
                    const editablePostUrl = getEditablePostUrl(preview);
                    const requiresManualUrl =
                      !preview.post_url &&
                      !normalizeWhitespace(editablePostUrl);
                    return (
                      <div key={candidateKey} className="popup-selected-card">
                        <div className="popup-selected-card__header">
                          <div>
                            <div className="popup-selected-card__title">
                              {preview.author_name ?? "Autor não identificado"}
                            </div>
                            <div className="popup-muted">
                              {preview.author_title ?? "Sem headline visível"}
                            </div>
                          </div>
                          <button
                            type="button"
                            onClick={() =>
                              void handleRemoveSelected(candidateKey)
                            }
                            disabled={busy !== null}
                            className="popup-button popup-button--secondary"
                          >
                            Remover
                          </button>
                        </div>
                        <div className="popup-selected-card__body">
                          {truncateText(preview.post_text, selectedTextLimit)}
                        </div>
                        <div className="popup-selected-card__footer">
                          {preview.likes} curtidas · {preview.comments}{" "}
                          comentários · {preview.shares} compartilhamentos
                        </div>
                        <div className="popup-field">
                          <label
                            className="popup-field__label"
                            htmlFor={`post-url-${candidateKey}`}
                          >
                            Link do post
                          </label>
                          <input
                            id={`post-url-${candidateKey}`}
                            type="url"
                            value={editablePostUrl}
                            onChange={(event) =>
                              handleUrlChange(candidateKey, event.target.value)
                            }
                            placeholder="https://www.linkedin.com/feed/update/..."
                            className="popup-input"
                          />
                          <div className="popup-field__hint">
                            {preview.post_url
                              ? "URL detectada automaticamente. Você pode editar se necessário."
                              : "Preencha manualmente para concluir a importação deste post."}
                          </div>
                          {requiresManualUrl ? (
                            <div className="popup-feedback popup-feedback--warning">
                              Link obrigatório para este post.
                            </div>
                          ) : null}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
              {importFailures.length > 0 ? (
                <div className="popup-failure-list">
                  {importFailures.map((failure) => (
                    <div
                      key={failure.candidateKey}
                      className="popup-failure-item"
                    >
                      <strong>{failure.label}</strong>
                      <span>{failure.message}</span>
                    </div>
                  ))}
                </div>
              ) : null}
              <div className="popup-actions">
                <button
                  type="button"
                  onClick={() => setActiveStep("destination")}
                  disabled={busy !== null}
                  className="popup-button popup-button--secondary"
                >
                  Voltar
                </button>
                <button
                  type="button"
                  onClick={() => void handleClearSelected()}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--secondary"
                >
                  Limpar seleção
                </button>
                <button
                  type="button"
                  onClick={() => void handleImportSelected()}
                  disabled={busy !== null || selectedPreviews.length === 0}
                  className="popup-button popup-button--primary"
                >
                  {busy === "batch-import"
                    ? "Importando lote..."
                    : `Importar ${selectedPreviews.length} ${selectedPreviews.length === 1 ? "post" : "posts"}`}
                </button>
              </div>
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
