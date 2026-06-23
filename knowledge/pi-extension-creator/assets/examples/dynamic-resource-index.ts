import { existsSync } from "node:fs";
import path from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

export default function dynamicResources(pi: ExtensionAPI) {
  pi.on("resources_discover", async (_event, ctx) => {
    const skillDir = path.join(ctx.cwd, ".pi", "generated-skills");
    if (!existsSync(skillDir)) return {};

    return {
      skillPaths: [skillDir],
    };
  });
}
