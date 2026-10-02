import { spawnSync } from "node:child_process";

const npmCli = process.env.npm_execpath;

if (!npmCli) {
  console.error("npm_execpath is unavailable. Run this script through npm run verify.");
  process.exit(1);
}

const checks = [
  ["run", "api:check"],
  ["run", "lint"],
  ["run", "typecheck"],
  ["test", "--", "--run"],
  ["run", "build"],
];

for (const arguments_ of checks) {
  const result = spawnSync(process.execPath, [npmCli, ...arguments_], {
    cwd: process.cwd(),
    stdio: "inherit",
  });

  if (result.error) {
    console.error(`Unable to run npm: ${result.error.message}`);
    process.exit(1);
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}