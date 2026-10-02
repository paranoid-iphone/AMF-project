import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import {
  exportAuthoritativeSchema,
  readCheckedInSchema,
  schemaUrl,
} from "./export-openapi.mjs";
import { generateApiTypes } from "./generate-api.mjs";

const outputUrl = new URL("../src/api/schema.d.ts", import.meta.url);

try {
  const authoritativeSchema = exportAuthoritativeSchema();
  const checkedInSchema = await readCheckedInSchema();

  if (checkedInSchema !== authoritativeSchema) {
    console.error(
      `Checked-in OpenAPI schema is stale: ${fileURLToPath(schemaUrl)}. Run npm run api:export, then npm run api:generate.`,
    );
    process.exit(1);
  }

  console.log("Checked-in OpenAPI schema matches the validated Django export.");

  const expected = await generateApiTypes();
  let actual;

  try {
    actual = await readFile(outputUrl, "utf8");
  } catch (error) {
    if (error && typeof error === "object" && "code" in error && error.code === "ENOENT") {
      console.error("Generated API types are missing. Run npm run api:generate.");
      process.exit(1);
    }
    throw error;
  }

  if (actual !== expected) {
    console.error(
      `Generated API types are stale: ${fileURLToPath(outputUrl)}. Run npm run api:generate.`,
    );
    process.exit(1);
  }

  console.log("Generated API types are current.");
} catch (error) {
  console.error(error instanceof Error ? error.message : error);
  process.exit(1);
}