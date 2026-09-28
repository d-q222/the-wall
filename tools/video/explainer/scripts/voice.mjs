// Generates one narration file per scene with macOS `say`, all in parallel, then
// writes audio/durations.json with the real measured length of each file.
import { readFileSync, writeFileSync } from "node:fs";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
const run = promisify(execFile);
const root = new URL("..", import.meta.url).pathname;
const { voice, rate, tempo = 1, scenes } = JSON.parse(readFileSync(root + "scripts/narration.json", "utf8"));

// Spoken forms only; captions keep the written text.
const speak = (t) =>
  t.replace(/Okafor & Lind/g, "Okafor and Lind")
    .replace(/O-1/g, "O one")
    .replace(/A-number/g, "A number")
    .replace(/USCIS/g, "U.S.C.I.S.")
    .replace(/GBrain/g, "G Brain").replace(/ABA/g, "A.B.A.")
    .replace(/de-identifier/g, "dee-identifier");

const only = process.argv.slice(2);
const todo = only.length ? scenes.filter((s) => only.includes(s.id)) : scenes;
await Promise.all(todo.map(async (s) => {
  const aiff = `${root}audio/${s.id}.aiff`;
  await run("say", ["-v", voice, "-r", String(rate), "-o", aiff, speak(s.text)]);
  await run("ffmpeg", ["-y", "-loglevel", "error", "-i", aiff, "-af", `atempo=${tempo}`, "-ar", "48000", "-ac", "1", "-c:a", "pcm_s16le", `${root}audio/${s.id}.wav`]);
}));
const durations = {};
for (const s of scenes) {
  const { stdout } = await run("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", `${root}audio/${s.id}.wav`]);
  durations[s.id] = Number(Number(stdout).toFixed(3));
}
writeFileSync(root + "audio/durations.json", JSON.stringify(durations, null, 2) + "\n");
console.log(durations, "total", Object.values(durations).reduce((a, b) => a + b, 0).toFixed(2));
