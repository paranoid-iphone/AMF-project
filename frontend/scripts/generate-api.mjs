import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

import openapiTS, { astToString } from "openapi-typescript";

const schemaUrl = new URL("../openapi-schema.yaml", import.meta.url);
const outputUrl = new URL("../src/api/schema.d.ts", import.meta.url);

export async function generateApiTypes() {
  await readFile(schemaUrl, "utf8");
  const nodes = await openapiTS(schemaUrl, {
    alphabetize: true,
    defaultNonNullable: false,
  });
  return astToString(nodes);
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const generated = await generateApiTypes();
  await writeFile(outputUrl, generated, "utf8");
  console.log(`Generated ${fileURLToPath(outputUrl)}`);
}
