import { spawnSync } from "node:child_process";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const repositoryDirectory = fileURLToPath(new URL("../..", import.meta.url));
export const schemaUrl = new URL("../openapi-schema.yaml", import.meta.url);

function normalizeText(value) {
  return `${value.replace(/^\uFEFF/, "").replace(/\r\n/g, "\n").trimEnd()}\n`;
}

export function exportAuthoritativeSchema() {
  const result = spawnSync(
    "docker",
    [
      "compose",
      "exec",
      "-T",
      "backend",
      "python",
      "manage.py",
      "spectacular",
      "--validate",
      "--fail-on-warn",
    ],
    {
      cwd: repositoryDirectory,
      encoding: "utf8",
      maxBuffer: 10 * 1024 * 1024,
    },
  );

  if (result.error) {
    throw new Error(`Unable to run Docker Compose: ${result.error.message}`);
  }

  if (result.status !== 0) {
    if (result.stderr) {
      process.stderr.write(result.stderr);
    }
    throw new Error(`Django OpenAPI export failed with exit code ${result.status}.`);
  }

  if (!result.stdout.trim()) {
    throw new Error("Django OpenAPI export returned an empty schema.");
  }

  return normalizeText(result.stdout);
}

export async function readCheckedInSchema() {
  return normalizeText(await readFile(schemaUrl, "utf8"));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  try {
    const schema = exportAuthoritativeSchema();
    await writeFile(schemaUrl, schema, "utf8");
    console.log(`Exported validated Django OpenAPI schema to ${fileURLToPath(schemaUrl)}`);
  } catch (error) {
    console.error(error instanceof Error ? error.message : error);
    process.exit(1);
  }
}