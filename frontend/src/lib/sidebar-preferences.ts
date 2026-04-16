export const SIDEBAR_COLLAPSED_COOKIE = "prospector-sidebar-collapsed"

export function parseSidebarCollapsedCookie(value: string | undefined): boolean {
  return value === "true"
}
