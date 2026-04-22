import { execFileSync } from "node:child_process"
import { mkdtempSync, rmSync, writeFileSync } from "node:fs"
import { tmpdir } from "node:os"
import { dirname, join, resolve } from "node:path"
import process from "node:process"
import { fileURLToPath } from "node:url"

const scriptDir = dirname(fileURLToPath(import.meta.url))
const frontendDir = resolve(scriptDir, "..")
const repoRoot = resolve(frontendDir, "..")
const backendDir = resolve(repoRoot, "backend")
const outputPath = resolve(frontendDir, "src/lib/api/schema.d.ts")
const tempDir = mkdtempSync(join(tmpdir(), "prospector-openapi-"))
const openapiPath = join(tempDir, "openapi.json")
const openapiCliPath = resolve(frontendDir, "node_modules", "openapi-typescript", "bin", "cli.js")

const pythonCandidates = [
  process.env.PYTHON_API_SCHEMA_BIN,
  process.env.PYTHON,
  process.env.PYTHON_EXECUTABLE,
  process.platform === "win32" ? "c:/python314/python.exe" : undefined,
  process.platform === "win32" ? "py" : undefined,
  "python",
].filter(Boolean)

const pythonCode = [
  "from api.main import app",
  "import json",
  "print(json.dumps(app.openapi(), ensure_ascii=False))",
].join("\n")

function buildPythonArgs(candidate) {
  if (candidate === "py") {
    return ["-3", "-c", pythonCode]
  }

  return ["-c", pythonCode]
}

let openapiJson = ""
let lastError = null

try {
  for (const candidate of pythonCandidates) {
    try {
      openapiJson = execFileSync(candidate, buildPythonArgs(candidate), {
        cwd: backendDir,
        encoding: "utf8",
        env: {
          ...process.env,
          PYTHONUTF8: "1",
        },
      })
      if (openapiJson.trim().length > 0) {
        break
      }
    } catch (error) {
      lastError = error
    }
  }

  if (openapiJson.trim().length === 0) {
    throw lastError ?? new Error("Falha ao gerar OpenAPI do backend local.")
  }

  writeFileSync(openapiPath, openapiJson, "utf8")
  execFileSync(process.execPath, [openapiCliPath, openapiPath, "-o", outputPath], {
    cwd: frontendDir,
    stdio: "inherit",
  })
} finally {
  rmSync(tempDir, { force: true, recursive: true })
}
