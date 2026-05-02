import { exchangeGrant, fetchBootstrap, startExtensionSession } from "./api";
import {
  clearBootstrap,
  clearSession,
  getConfig,
  setBootstrap,
  setSession,
} from "./storage";
import type { ExtensionBootstrap, ExtensionSession } from "../shared/types";

function parseExpectedIdentityRedirectOrigin(): URL {
  return new URL(chrome.identity.getRedirectURL());
}

function validateAuthFlowRedirectUrl(redirectUrl: string): URL {
  const callbackUrl = new URL(redirectUrl);
  const expectedUrl = parseExpectedIdentityRedirectOrigin();

  if (callbackUrl.origin !== expectedUrl.origin) {
    throw new Error("Origem de callback OAuth inesperada.");
  }

  if (!callbackUrl.pathname.startsWith(expectedUrl.pathname)) {
    throw new Error("Path de callback OAuth inesperado.");
  }

  return callbackUrl;
}

function getExtensionVersion(): string {
  return chrome.runtime.getManifest().version;
}

export async function loginWithGoogle(): Promise<{
  session: ExtensionSession;
  bootstrap: ExtensionBootstrap;
}> {
  const config = await getConfig();
  const extensionVersion = getExtensionVersion();
  const authStart = await startExtensionSession(config, extensionVersion);
  const redirectUrl = await chrome.identity.launchWebAuthFlow({
    url: authStart.authorization_url,
    interactive: true,
  });

  if (!redirectUrl) {
    throw new Error("Fluxo OAuth nao retornou redirect final.");
  }

  const callbackUrl = validateAuthFlowRedirectUrl(redirectUrl);
  const error = callbackUrl.searchParams.get("error");
  if (error) {
    throw new Error(error);
  }

  const grantCode = callbackUrl.searchParams.get("grant_code");
  if (!grantCode) {
    throw new Error("Grant da extensao ausente no callback.");
  }

  const session = await exchangeGrant(config, grantCode);
  const bootstrap = await fetchBootstrap(config, session, extensionVersion);
  await setSession(session);
  await setBootstrap(bootstrap);
  return { session, bootstrap };
}

export async function logout(): Promise<void> {
  await clearSession();
  await clearBootstrap();
}
