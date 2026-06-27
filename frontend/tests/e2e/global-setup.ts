import { spawn } from "child_process";
import { writeFile } from "fs/promises";
import { join } from "path";

const serverUrl = "http://127.0.0.1:3000";

async function waitForServer() {
  const deadline = Date.now() + 120_000;
  while (Date.now() < deadline) {
    try {
      const response = await fetch(serverUrl);
      if (response.status < 500) return;
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
  }
  throw new Error("Timed out waiting for Next.js dev server");
}

async function globalSetup() {
  try {
    const response = await fetch(serverUrl);
    if (response.status < 500) return;
  } catch {
    // Start a fresh server below.
  }

  const child = spawn(process.execPath, ["node_modules/next/dist/bin/next", "dev", "--hostname", "127.0.0.1"], {
    cwd: process.cwd(),
    detached: true,
    stdio: "ignore",
    windowsHide: true
  });
  child.unref();
  await writeFile(join(process.cwd(), ".playwright-server-pid"), String(child.pid), "utf8");
  await waitForServer();
}

export default globalSetup;
