import type {
  ActiveTabPostScanResult,
  CaptureRequestPayload,
  CapturePreview,
  ExtensionConfig,
  ExtensionState,
} from "./types";

export const MESSAGE_TYPES = {
  GET_STATE: "GET_STATE",
  AUTH_LOGIN: "AUTH_LOGIN",
  AUTH_LOGOUT: "AUTH_LOGOUT",
  GET_ACTIVE_TAB_POSTS: "GET_ACTIVE_TAB_POSTS",
  GET_ACTIVE_TAB_SCAN: "GET_ACTIVE_TAB_SCAN",
  SAVE_CAPTURED_POST: "SAVE_CAPTURED_POST",
  IMPORT_CAPTURE: "IMPORT_CAPTURE",
  CREATE_ENGAGEMENT_SESSION: "CREATE_ENGAGEMENT_SESSION",
  GET_CONFIG: "GET_CONFIG",
  SAVE_CONFIG: "SAVE_CONFIG",
  REFRESH_BOOTSTRAP: "REFRESH_BOOTSTRAP",
} as const;

export type ExtensionMessage =
  | { type: typeof MESSAGE_TYPES.GET_STATE }
  | { type: typeof MESSAGE_TYPES.AUTH_LOGIN }
  | { type: typeof MESSAGE_TYPES.AUTH_LOGOUT }
  | { type: typeof MESSAGE_TYPES.GET_ACTIVE_TAB_POSTS }
  | { type: typeof MESSAGE_TYPES.GET_ACTIVE_TAB_SCAN }
  | { type: typeof MESSAGE_TYPES.CREATE_ENGAGEMENT_SESSION }
  | { type: typeof MESSAGE_TYPES.REFRESH_BOOTSTRAP }
  | { type: typeof MESSAGE_TYPES.SAVE_CAPTURED_POST; payload: CapturePreview }
  | {
      type: typeof MESSAGE_TYPES.IMPORT_CAPTURE;
      payload: CaptureRequestPayload;
    }
  | { type: typeof MESSAGE_TYPES.GET_CONFIG }
  | { type: typeof MESSAGE_TYPES.SAVE_CONFIG; payload: ExtensionConfig };

export interface ExtensionSuccessResponse<T> {
  ok: true;
  data: T;
}

export interface ExtensionErrorResponse {
  ok: false;
  error: string;
}

export type ExtensionMessageResponse<T> =
  | ExtensionSuccessResponse<T>
  | ExtensionErrorResponse;

export type ExtensionStateResponse = ExtensionMessageResponse<ExtensionState>;
export type ActiveTabPostScanResponse =
  ExtensionMessageResponse<ActiveTabPostScanResult>;
