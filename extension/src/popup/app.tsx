import { useEffect, useState } from "react";

import { MESSAGE_TYPES } from "../shared/contracts";
import {
  buildCaptureRequest,
  buildPreviewKey,
} from "../shared/linkedin-normalizer";
import type {
  ActiveTabPostScanDiagnostic,
  ActiveTabPostScanResult,
  CaptureDestinationType,
  CapturePreview,
  EngagementSessionSummary,
  ExtensionState,
} from "../shared/types";

type ExtensionSurfaceMode = "popup" | "sidepanel";
type PopupTabKey = "capture" | "destination" | "diagnostic";

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
  const [activeTab, setActiveTab] = useState<PopupTabKey>("capture");
  const [destination, setDestination] =
    useState<CaptureDestinationType>("reference");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadState();
    void loadAvailablePosts();
  }, []);

  async function loadState(preferredSessionId?: string | null) {
    setLoading(true);
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.GET_STATE,
      });
      setState(nextState);
      const nextSessions =
        nextState.bootstrap?.recent_engagement_sessions ?? [];
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
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao carregar estado",
      );
    } finally {
      setLoading(false);
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
      setState(nextState);
      await loadAvailablePosts();
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha no login",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleSelectPreview(preview: CapturePreview) {
    setBusy("select-preview");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.SAVE_CAPTURED_POST,
        payload: preview,
      });
      setState(nextState);
      setResultMessage("Post selecionado para importacao.");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao selecionar post",
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
      await loadState(session.id);
      setResultMessage("Nova sessao de engagement criada.");
    } catch (nextError) {
      setError(
        nextError instanceof Error
          ? nextError.message
          : "Falha ao criar sessao",
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
      setState(nextState);
      setResultMessage(null);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha no logout",
      );
    } finally {
      setBusy(null);
    }
  }

  async function handleImport(preview: CapturePreview) {
    setBusy("import");
    setError(null);
    setResultMessage(null);

    try {
      const payload = buildCaptureRequest(
        preview,
        destination,
        destination === "engagement" ? sessionId : null,
        chrome.runtime.getManifest().version,
      );
      const result = await sendMessage<{ destination: string; result: string }>(
        {
          type: MESSAGE_TYPES.IMPORT_CAPTURE,
          payload,
        },
      );
      await loadState();
      setAvailablePosts((prev) =>
        prev.filter((p) => buildPreviewKey(p) !== buildPreviewKey(preview)),
      );
      void loadAvailablePosts();
      setResultMessage(
        `Importacao concluida: ${result.destination} (${result.result}).`,
      );
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha ao importar",
      );
    } finally {
      setBusy(null);
    }
  }

  const preview = state?.preview ?? null;
  const sessions = state?.bootstrap?.recent_engagement_sessions ?? [];
  const selectedPreviewKey = preview ? buildPreviewKey(preview) : null;
  const discardReasonEntries = Object.entries(
    scanDiagnostic?.discard_reason_counts ?? {},
  ).sort((left, right) => right[1] - left[1]);

  function formatSessionLabel(session: EngagementSessionSummary): string {
    const sourceLabel = session.scan_source === "manual" ? "Manual" : "Scanner";
    const statusLabel =
      session.status === "running"
        ? "Em andamento"
        : session.status === "completed"
          ? "Concluida"
          : "Parcial";
    return `${sourceLabel} · ${statusLabel} · ${new Date(session.created_at).toLocaleString("pt-BR")}`;
  }

  const tabCountLabel = `${availablePosts.length} ${availablePosts.length === 1 ? "post" : "posts"}`;

  return (
    <div
      className={`popup-shell ${surfaceMode === "sidepanel" ? "is-sidepanel" : ""}`}
    >
      <div className="popup-header">
        <div>
          <div className="popup-kicker">LinkedIn Capture V1</div>
          <h1 className="popup-title">Prospector</h1>
          <div className="popup-subtitle">
            Capture, organize e importe posts do LinkedIn com menos atrito.
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
          <section className="popup-card">
            <div className="popup-account-row">
              <div>
                <div className="popup-card-title">
                  {state.session.user.name ?? state.session.user.email}
                </div>
                <div className="popup-muted">{state.session.user.email}</div>
              </div>
              <div className="popup-status-pill">
                LinkedIn {state.bootstrap?.linkedin.connected ? "ok" : "pendente"}
              </div>
            </div>
          </section>

          <section className="popup-tabs">
            <button
              type="button"
              onClick={() => setActiveTab("capture")}
              className={`popup-tab ${activeTab === "capture" ? "is-active" : ""}`}
            >
              Captura
              <span className="popup-tab-badge">{tabCountLabel}</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("destination")}
              className={`popup-tab ${activeTab === "destination" ? "is-active" : ""}`}
            >
              Destino
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("diagnostic")}
              className={`popup-tab ${activeTab === "diagnostic" ? "is-active" : ""}`}
            >
              Diagnóstico
            </button>
          </section>

          {activeTab === "capture" ? (
            <>
              <section className="popup-card">
                <div className="popup-card-title popup-card-title--spaced">
                  Posts detectados na página
                </div>
                <div className="popup-card-actions">
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
                      <strong>{scanDiagnostic.candidate_container_count}</strong>
                    </div>
                    <div className="popup-diagnostic-summary__row">
                      <span>Posts aceitos:</span>
                      <strong>{scanDiagnostic.accepted_post_count}</strong>
                    </div>
                  </div>
                ) : null}
                {availablePosts.length === 0 ? (
                  <p className="popup-empty">
                    Nenhum post foi detectado na aba ativa. Abra um feed ou post do
                    LinkedIn e clique em Atualizar lista.
                  </p>
                ) : null}
                {availablePosts.length > 0 ? (
                  <div className={`popup-post-list ${surfaceMode === "sidepanel" ? "is-sidepanel" : ""}`}>
                    {availablePosts.map((candidate, index) => {
                      const candidateKey = buildPreviewKey(candidate);
                      const isSelected = candidateKey === selectedPreviewKey;
                      return (
                        <button
                          key={`${candidateKey}-${index}`}
                          type="button"
                          onClick={() => void handleSelectPreview(candidate)}
                          disabled={busy !== null}
                          className={`popup-post-item ${isSelected ? "is-active" : ""}`}
                        >
                          <div className="popup-post-item__eyebrow">
                            {candidate.captured_from === "post_detail" ? "Post detalhado" : "Publicação no feed"}
                          </div>
                          <div className="popup-post-item__title">
                            {candidate.author_name ?? "Autor nao identificado"}
                          </div>
                          <div className="popup-post-item__meta">
                            {candidate.author_title ?? "Sem headline visivel"}
                          </div>
                          <div className="popup-post-item__text">
                            {candidate.post_text.slice(0, surfaceMode === "sidepanel" ? 190 : 140)}
                            {candidate.post_text.length > (surfaceMode === "sidepanel" ? 190 : 140) ? "..." : ""}
                          </div>
                          <div className="popup-post-item__footer">
                            {isSelected ? "Selecionado" : "Selecionar este post"}
                          </div>
                        </button>
                      );
                    })}
                  </div>
                ) : null}
              </section>

              <section className="popup-card">
                <div className="popup-card-title popup-card-title--spaced">
                  Post selecionado
                </div>
                {!preview ? (
                  <p className="popup-empty">
                    Selecione um post detectado acima ou use o botão Selecionar post
                    dentro do LinkedIn.
                  </p>
                ) : null}
                {preview ? (
                  <div className="popup-stack">
                    <div className="popup-card-title">
                      {preview.author_name ?? "Autor nao identificado"}
                    </div>
                    <div className="popup-muted">
                      {preview.author_title ?? "Sem headline visivel"}
                    </div>
                    <div className="popup-preview-text">
                      {preview.post_text.slice(0, surfaceMode === "sidepanel" ? 420 : 320)}
                      {preview.post_text.length > (surfaceMode === "sidepanel" ? 420 : 320) ? "..." : ""}
                    </div>
                    <div className="popup-meta">
                      {preview.likes} curtidas · {preview.comments} comentarios · {" "}
                      {preview.shares} compartilhamentos
                    </div>
                    <button
                      onClick={() => handleImport(preview)}
                      disabled={
                        busy !== null ||
                        (destination === "engagement" && !sessionId)
                      }
                      className="popup-button popup-button--primary"
                    >
                      {busy === "import" ? "Importando..." : "Importar agora"}
                    </button>
                  </div>
                ) : null}
              </section>
            </>
          ) : null}

          {activeTab === "destination" ? (
            <section className="popup-card">
              <div className="popup-card-title popup-card-title--spaced">
                Destino de importação
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
              <div className="popup-meta popup-meta--spaced">
                Referência salva o post como inspiração. Engagement anexa o post a uma sessão ativa.
              </div>
              {destination === "engagement" ? (
                <div className="popup-stack popup-stack--section">
                  <select
                    aria-label="Selecionar sessao de engagement"
                    value={sessionId ?? ""}
                    onChange={(event) => setSessionId(event.target.value || null)}
                    className="popup-select"
                  >
                    <option value="">Selecione uma sessao</option>
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
                    {busy === "create-session" ? "Criando sessao..." : "Nova sessao"}
                  </button>
                </div>
              ) : (
                <div className="popup-empty-card">
                  O próximo clique em Importar agora vai salvar este post como referência no Prospector.
                </div>
              )}
            </section>
          ) : null}

          {activeTab === "diagnostic" ? (
            <section className="popup-card">
            <div className="popup-card-title popup-card-title--spaced">
              Diagnóstico da detecção
            </div>
            {scanDiagnostic ? (
              <div className="popup-diagnostic-summary">
                <div className="popup-diagnostic-summary__row">
                  <span>Cards:</span>
                  <strong>{scanDiagnostic.static_container_count}</strong>
                </div>
                <div className="popup-diagnostic-summary__row">
                  <span>Barras de acao:</span>
                  <strong>{scanDiagnostic.action_bar_count}</strong>
                </div>
                <div className="popup-diagnostic-summary__row">
                  <span>Candidatos:</span>
                  <strong>{scanDiagnostic.candidate_container_count}</strong>
                </div>
                <div className="popup-diagnostic-summary__row">
                  <span>Posts aceitos:</span>
                  <strong>{scanDiagnostic.accepted_post_count}</strong>
                </div>
              </div>
            ) : null}
            {scanDiagnostic?.error_message ? (
              <p className="popup-feedback popup-feedback--warning">
                {scanDiagnostic.error_message}
              </p>
            ) : null}
            {scanDiagnostic ? (
              <div className="popup-diagnostic-panel is-open">
                <div className="popup-diagnostic-panel__content">
                  <div className="popup-meta">
                    Fonte: {scanDiagnostic.captured_from} · URL: {scanDiagnostic.page_url ?? "indisponivel"}
                  </div>
                  {discardReasonEntries.length > 0 ? (
                    <div className="popup-diagnostic-block">
                      <div className="popup-diagnostic-title">Motivos de descarte</div>
                      {discardReasonEntries.map(([reason, count]) => (
                        <div key={reason} className="popup-diagnostic-item">
                          <span>{reason}</span>
                          <strong>{count}</strong>
                        </div>
                      ))}
                    </div>
                  ) : null}
                  {scanDiagnostic.sample_candidates.length > 0 ? (
                    <div className="popup-diagnostic-block">
                      <div className="popup-diagnostic-title">Amostra de candidatos</div>
                      {scanDiagnostic.sample_candidates.map((candidate, index) => (
                        <div key={`${candidate.tag_name}-${index}`} className="popup-diagnostic-candidate">
                          <div className="popup-diagnostic-candidate__head">
                            <strong>{candidate.discard_reason ? "Descartado" : "Aceito"}</strong>
                            <span>{candidate.tag_name}</span>
                          </div>
                          <div className="popup-diagnostic-candidate__flags">
                            URL {candidate.has_post_url ? "sim" : "nao"} · Autor {candidate.has_author_name ? "sim" : "nao"} · Titulo {candidate.has_author_title ? "sim" : "nao"} · Metricas {candidate.has_metrics ? "sim" : "nao"}
                          </div>
                          {candidate.discard_reason ? (
                            <div className="popup-diagnostic-candidate__reason">
                              motivo: {candidate.discard_reason}
                            </div>
                          ) : null}
                          {candidate.text_excerpt ? (
                            <div className="popup-diagnostic-candidate__text">
                              {candidate.text_excerpt}
                            </div>
                          ) : null}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ) : null}
            </section>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
