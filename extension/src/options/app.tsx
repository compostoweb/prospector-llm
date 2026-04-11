import { useEffect, useState } from "react";

import { MESSAGE_TYPES } from "../shared/contracts";
import type { ExtensionConfig } from "../shared/types";

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

export function OptionsApp() {
  const [config, setConfig] = useState<ExtensionConfig>({
    apiBaseUrl: "http://localhost:8000",
  });
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    void sendMessage<ExtensionConfig>({ type: MESSAGE_TYPES.GET_CONFIG }).then(
      setConfig,
    );
  }, []);

  async function handleSave() {
    await sendMessage({ type: MESSAGE_TYPES.SAVE_CONFIG, payload: config });
    setMessage("Configuracao salva.");
  }

  return (
    <div className="options-shell">
      <h1>Prospector LinkedIn Capture</h1>
      <p>
        Use esta pagina para ajustar o endpoint da API consumido pela extensao.
      </p>
      <label className="options-field">
        <span>API base URL</span>
        <input
          value={config.apiBaseUrl}
          onChange={(event) => setConfig({ apiBaseUrl: event.target.value })}
          className="options-input"
        />
      </label>
      <button onClick={handleSave} className="options-button">
        Salvar
      </button>
      {message ? <p className="options-success">{message}</p> : null}
    </div>
  );
}
