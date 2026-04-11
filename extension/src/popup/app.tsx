import { useEffect, useState } from "react";

import { MESSAGE_TYPES } from "../shared/contracts";
import { buildCaptureRequest } from "../shared/linkedin-normalizer";
import type {
  CaptureDestinationType,
  CapturePreview,
  ExtensionState,
} from "../shared/types";

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

export function PopupApp() {
  const [state, setState] = useState<ExtensionState | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [destination, setDestination] =
    useState<CaptureDestinationType>("reference");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [resultMessage, setResultMessage] = useState<string | null>(null);

  useEffect(() => {
    void loadState();
  }, []);

  async function loadState() {
    setLoading(true);
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.GET_STATE,
      });
      setState(nextState);
      if (nextState.bootstrap?.recent_engagement_sessions[0]?.id) {
        setSessionId(nextState.bootstrap.recent_engagement_sessions[0].id);
      }
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

  async function handleLogin() {
    setBusy("login");
    setError(null);
    try {
      const nextState = await sendMessage<ExtensionState>({
        type: MESSAGE_TYPES.AUTH_LOGIN,
      });
      setState(nextState);
    } catch (nextError) {
      setError(
        nextError instanceof Error ? nextError.message : "Falha no login",
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

  return (
    <div className="popup-shell">
      <div className="popup-header">
        <div>
          <div className="popup-kicker">LinkedIn Capture V1</div>
          <h1 className="popup-title">Prospector</h1>
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
            <div className="popup-card-title">
              {state.session.user.name ?? state.session.user.email}
            </div>
            <div className="popup-muted">{state.session.user.email}</div>
            <div className="popup-meta">
              LinkedIn conectado:{" "}
              {state.bootstrap?.linkedin.connected ? "sim" : "nao"}
            </div>
          </section>

          <section className="popup-card">
            <div className="popup-card-title popup-card-title--spaced">
              Destino
            </div>
            <div className="popup-segmented">
              <button
                onClick={() => setDestination("reference")}
                className={`popup-segment ${destination === "reference" ? "is-active" : ""}`}
              >
                Referencia
              </button>
              <button
                onClick={() => setDestination("engagement")}
                className={`popup-segment ${destination === "engagement" ? "is-active" : ""}`}
              >
                Engagement
              </button>
            </div>
            {destination === "engagement" ? (
              <select
                aria-label="Selecionar sessao de engagement"
                value={sessionId ?? ""}
                onChange={(event) => setSessionId(event.target.value || null)}
                className="popup-select"
              >
                <option value="">Selecione uma sessao</option>
                {sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    {session.status} ·{" "}
                    {new Date(session.created_at).toLocaleString("pt-BR")}
                  </option>
                ))}
              </select>
            ) : null}
          </section>

          <section className="popup-card">
            <div className="popup-card-title popup-card-title--spaced">
              Ultimo post capturado
            </div>
            {!preview ? (
              <p className="popup-empty">
                Clique em Salvar no Prospector em um post do LinkedIn e volte
                aqui.
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
                  {preview.post_text.slice(0, 320)}
                  {preview.post_text.length > 320 ? "..." : ""}
                </div>
                <div className="popup-meta">
                  {preview.likes} curtidas · {preview.comments} comentarios ·{" "}
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
        </div>
      ) : null}
    </div>
  );
}
