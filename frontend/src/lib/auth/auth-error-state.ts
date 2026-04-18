export type AuthErrorTone = "danger" | "warning" | "info"

export interface AuthErrorState {
  code: string
  title: string
  description: string
  banner: string
  tone: AuthErrorTone
  showRetry: boolean
  supportText: string
  nextSteps: string[]
}

const DEFAULT_ERROR_STATE: AuthErrorState = {
  code: "default",
  title: "Não foi possível concluir seu acesso",
  description:
    "O login não terminou como esperado. Tente novamente em instantes ou volte para a tela inicial de acesso.",
  banner: "Ocorreu um erro. Tente novamente.",
  tone: "danger",
  showRetry: true,
  supportText:
    "Se o problema persistir, valide se você está usando a conta Google correta para acessar o Prospector.",
  nextSteps: [
    "Volte para a tela de login e tente novamente.",
    "Se você tiver mais de uma conta Google, escolha a conta corporativa correta.",
  ],
}

const AUTH_ERROR_STATES: Record<string, AuthErrorState> = {
  auth_failed: {
    code: "auth_failed",
    title: "Falha na autenticação",
    description:
      "O Prospector recebeu o retorno do login, mas não conseguiu finalizar sua sessão com segurança.",
    banner: "Falha na autenticação. Tente novamente.",
    tone: "danger",
    showRetry: true,
    supportText:
      "Esse erro costuma acontecer quando o login é interrompido no meio do fluxo ou quando a sessão anterior expirou.",
    nextSteps: [
      "Tente entrar novamente usando o botão do Google.",
      "Se o erro voltar, feche a aba atual e reinicie o login do zero.",
    ],
  },
  session_expired: {
    code: "session_expired",
    title: "Sua sessão expirou",
    description:
      "Por segurança, o Prospector encerrou sua sessão atual e precisa validar seu acesso novamente.",
    banner: "Sessão expirada. Faça login novamente.",
    tone: "warning",
    showRetry: true,
    supportText: "Sessões expiram naturalmente após um período sem renovação válida do token.",
    nextSteps: [
      "Entre novamente para restaurar o acesso.",
      "Se isso ocorrer com frequência, revise as configurações do ambiente de autenticação.",
    ],
  },
  OAuthCallback: {
    code: "OAuthCallback",
    title: "Erro no callback OAuth",
    description: "O retorno do Google não chegou no formato esperado para concluir a autenticação.",
    banner: "Erro no callback OAuth. Tente novamente.",
    tone: "danger",
    showRetry: true,
    supportText:
      "Esse cenário normalmente indica callback interrompido, parâmetros ausentes ou redirecionamento incompleto.",
    nextSteps: [
      "Reinicie o login pelo botão do Google.",
      "Se continuar, verifique a configuração das URLs de callback do ambiente.",
    ],
  },
  no_token: {
    code: "no_token",
    title: "Login incompleto",
    description: "O frontend não recebeu o token necessário para abrir sua sessão no Prospector.",
    banner: "Não foi possível concluir o login.",
    tone: "warning",
    showRetry: true,
    supportText:
      "Sem o token de sessão, o sistema bloqueia o acesso para evitar inconsistência de autenticação.",
    nextSteps: [
      "Volte ao login e repita a autenticação.",
      "Se persistir, revise o callback configurado entre backend e frontend.",
    ],
  },
  email_not_registered: {
    code: "email_not_registered",
    title: "Este email ainda não tem acesso",
    description:
      "Sua autenticação no Google funcionou, mas o email escolhido não está cadastrado entre os usuários autorizados do Prospector.",
    banner: "Seu email não está cadastrado no sistema.",
    tone: "warning",
    showRetry: true,
    supportText:
      "Se você tiver outra conta Google autorizada, pode tentar novamente com ela. Caso contrário, o acesso precisa ser liberado no sistema primeiro.",
    nextSteps: [
      "Tente entrar com outra conta Google autorizada.",
      "Se esse email deveria ter acesso, peça ao administrador para cadastrá-lo antes de tentar novamente.",
    ],
  },
  user_inactive: {
    code: "user_inactive",
    title: "Sua conta está inativa",
    description:
      "O usuário existe no sistema, mas está marcado como inativo e não pode concluir o login neste momento.",
    banner: "Sua conta está inativa.",
    tone: "warning",
    showRetry: false,
    supportText:
      "Esse caso normalmente depende de reativação por alguém com permissão administrativa.",
    nextSteps: [
      "Entre em contato com um administrador do Prospector.",
      "Após a reativação, volte ao login e tente novamente.",
    ],
  },
  invalid_state: {
    code: "invalid_state",
    title: "A sessão de login expirou",
    description:
      "O retorno do Google chegou com um estado inválido ou expirado, então o login foi interrompido por segurança.",
    banner: "A sessão de login expirou ou é inválida.",
    tone: "warning",
    showRetry: true,
    supportText:
      "Esse comportamento é esperado quando o callback demora demais ou quando o fluxo é retomado em uma aba antiga.",
    nextSteps: [
      "Recomece o login a partir da tela inicial.",
      "Evite reutilizar abas antigas do fluxo de autenticação.",
    ],
  },
  google_unverified_email: {
    code: "google_unverified_email",
    title: "O Google não confirmou esse email",
    description:
      "A conta escolhida não retornou um email verificado, então o Prospector não pode confiar nesse acesso.",
    banner: "Seu email do Google ainda não foi verificado.",
    tone: "warning",
    showRetry: true,
    supportText: "O Prospector exige email verificado no Google para liberar o acesso.",
    nextSteps: [
      "Use uma conta Google com email já verificado.",
      "Se necessário, confirme o email na própria conta Google antes de tentar novamente.",
    ],
  },
  user_without_tenant: {
    code: "user_without_tenant",
    title: "Seu usuário está sem vínculo ativo",
    description:
      "A autenticação foi aceita, mas o usuário não está vinculado a nenhum tenant ativo para abrir a aplicação.",
    banner: "Seu usuário não está vinculado a nenhum tenant ativo.",
    tone: "warning",
    showRetry: false,
    supportText: "Esse acesso depende de associação válida com um tenant ativo no backend.",
    nextSteps: [
      "Peça ao administrador para revisar o vínculo do seu usuário com o tenant correto.",
      "Depois da correção, volte ao login e tente novamente.",
    ],
  },
  google_oauth_unconfigured: {
    code: "google_oauth_unconfigured",
    title: "Login com Google indisponível neste ambiente",
    description:
      "O ambiente atual não está configurado corretamente para concluir o OAuth do Google.",
    banner: "O login com Google não está disponível neste ambiente.",
    tone: "danger",
    showRetry: false,
    supportText: "Esse erro indica problema de configuração do ambiente, não da sua conta.",
    nextSteps: [
      "Não adianta repetir o login até a configuração ser corrigida.",
      "Revise as variáveis de ambiente e a configuração do OAuth no backend.",
    ],
  },
  google_token_exchange_failed: {
    code: "google_token_exchange_failed",
    title: "O Google não confirmou o código de acesso",
    description:
      "O Prospector recebeu o retorno do Google, mas não conseguiu trocar esse retorno por um token válido.",
    banner: "Não foi possível validar o retorno do Google.",
    tone: "danger",
    showRetry: true,
    supportText:
      "Esse problema costuma estar ligado a callback, credenciais OAuth ou código já expirado.",
    nextSteps: [
      "Reinicie o login para gerar um novo retorno do Google.",
      "Se persistir, revise client id, client secret e redirect URI do backend.",
    ],
  },
  google_profile_fetch_failed: {
    code: "google_profile_fetch_failed",
    title: "Não foi possível obter seus dados do Google",
    description:
      "O token do Google foi recebido, mas a leitura do perfil do usuário falhou antes de o Prospector abrir sua sessão.",
    banner: "Não foi possível obter seu perfil no Google.",
    tone: "danger",
    showRetry: true,
    supportText:
      "Sem o perfil do Google, o backend não consegue validar email, nome e permissões de acesso.",
    nextSteps: [
      "Tente novamente em instantes.",
      "Se continuar, revise a conectividade do backend com os endpoints do Google.",
    ],
  },
  google_email_missing: {
    code: "google_email_missing",
    title: "O Google não informou um email utilizável",
    description:
      "A autenticação retornou sem email válido, então o Prospector não conseguiu identificar qual usuário deveria ser autenticado.",
    banner: "O Google não informou um email para esta conta.",
    tone: "warning",
    showRetry: true,
    supportText:
      "Sem email, o sistema não tem como aplicar a política de acesso por usuário cadastrado.",
    nextSteps: [
      "Escolha outra conta Google com email disponível.",
      "Se o problema ocorrer sempre com a mesma conta, revise as permissões e dados da conta no Google.",
    ],
  },
  oauth_access_denied: {
    code: "oauth_access_denied",
    title: "A autenticação foi cancelada",
    description:
      "O fluxo do Google foi interrompido antes da autorização final, então o Prospector não recebeu permissão para concluir o login.",
    banner: "A autenticação com Google foi cancelada.",
    tone: "info",
    showRetry: true,
    supportText:
      "Isso acontece quando o acesso é negado manualmente, a janela é fechada ou o consentimento não é concluído.",
    nextSteps: [
      "Volte ao login e refaça a autorização no Google.",
      "Se você cancelou por engano, basta tentar novamente.",
    ],
  },
}

export function resolveAuthErrorState(
  error?: string | null,
  message?: string | null,
): AuthErrorState {
  const normalizedError = error?.trim() || "default"
  const state = AUTH_ERROR_STATES[normalizedError] ?? DEFAULT_ERROR_STATE
  if (!message || message === state.description || message === state.banner) {
    return state
  }
  return {
    ...state,
    description: message,
  }
}
