export async function downloadMediaFile(fileUrl: string, fileName: string): Promise<void> {
  const response = await fetch(fileUrl)

  if (!response.ok) {
    throw new Error("Nao foi possivel preparar o download da imagem")
  }

  const blob = await response.blob()
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement("a")

  link.href = objectUrl
  link.download = buildDownloadFilename(fileName, fileUrl, blob.type)
  document.body.appendChild(link)
  link.click()
  link.remove()

  URL.revokeObjectURL(objectUrl)
}

export function getDownloadBaseName(
  rawName: string | null | undefined,
  fallbackName: string,
): string {
  return sanitizeFileName(stripFileExtension(rawName || fallbackName || "imagem-post"))
}

function buildDownloadFilename(fileName: string, fileUrl: string, mimeType?: string): string {
  const baseName = sanitizeFileName(stripFileExtension(fileName || "imagem-post"))
  const extension =
    getFileExtension(fileName) || getFileExtension(fileUrl) || getExtensionFromMimeType(mimeType)

  return `${baseName}.${extension || "png"}`
}

function getFileExtension(value: string | null | undefined): string {
  if (!value) return ""

  const normalizedValue = (value.includes("?") ? value.split("?")[0] : value) || ""
  const lastSegment = normalizedValue.split("/").pop() || normalizedValue
  const extension = lastSegment.split(".").pop()

  if (!extension || extension === lastSegment) return ""
  return extension.toLowerCase()
}

function stripFileExtension(value: string): string {
  return value.replace(/\.[^.]+$/, "")
}

function sanitizeFileName(value: string): string {
  const normalizedValue = value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[<>:"/\\|?*]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()

  return normalizedValue || "imagem-post"
}

function getExtensionFromMimeType(mimeType: string | undefined): string {
  switch (mimeType) {
    case "image/jpeg":
      return "jpg"
    case "image/png":
      return "png"
    case "image/webp":
      return "webp"
    case "image/gif":
      return "gif"
    case "image/svg+xml":
      return "svg"
    default:
      return ""
  }
}
