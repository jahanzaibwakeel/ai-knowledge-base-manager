import { readFile, rm } from "fs/promises";
import { join } from "path";
import { execFile } from "child_process";

async function globalTeardown() {
  const pidFile = join(process.cwd(), ".playwright-server-pid");
  try {
    const pid = (await readFile(pidFile, "utf8")).trim();
    await new Promise<void>((resolve) => {
      execFile("taskkill", ["/PID", pid, "/T", "/F"], () => resolve());
    });
    await rm(pidFile, { force: true });
  } catch {
    // Reused server or already stopped.
  }
}

export default globalTeardown;
