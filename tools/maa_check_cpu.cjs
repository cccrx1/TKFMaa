/** Run the unchanged maa-tools check command with CPU resource loading. */
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

if (process.argv[2] !== "check") {
    throw new Error("maa_check_cpu.cjs is only for the maa-tools check command");
}

const root = path.resolve(__dirname, "..");
const requirements = fs.readFileSync(path.join(root, "tools", "requirements.txt"), "utf8");
const version = requirements.match(/^maafw==([\d.]+)$/m)?.[1];
if (!version) throw new Error("Missing pinned maafw version in tools/requirements.txt");
const config = fs.readFileSync(path.join(root, "maatools.config.mts"), "utf8");
if (config.match(/maaVersion:\s*"([\d.]+)"/)?.[1] !== version) {
    throw new Error("maa-tools version differs from tools/requirements.txt");
}

// maa-tools prepares this cache on its first normal check. Do not install or
// replace packages here, and use the same pinned native binding as the CLI.
const entry = path.join(
    os.homedir(),
    ".maa-tools",
    "install",
    version,
    "node_modules",
    "@maaxyz",
    "maa-node",
    "dist",
    "index-client.js",
);
if (!fs.existsSync(entry)) {
    throw new Error("Run npx --no-install @nekosu/maa-tools check once to prepare its pinned native cache");
}
const maa = require(entry);
if (maa.Global.version.replace(/^v/, "") !== version) {
    throw new Error(`Native version differs from the project pin: ${maa.Global.version}`);
}
// Native prototype methods are read-only. Supply a process-local namespace
// whose Resource subclass sets the public inference options on construction.
class CpuResource extends maa.Resource {
    constructor(...args) {
        super(...args);
        this.inference_execution_provider = "CPU";
        this.inference_device = "CPU";
    }
}
globalThis.maa = {...maa, Resource: CpuResource};
console.log(`maa-tools resource loading: CPU, MaaFramework ${version}`);
