Hammer — hier ist ein fertiges Prompt-Set + Wiring-Logik für eure App. Es besteht aus:

Einheitlichem System-Prompt (für alle Behandlungen)

User-Prompt-Vorlagen pro Region (Lippen, Wangen, Kinn, Option 4 als Platzhalter) mit ml-Parameter

Heuristik: ml ➜ „Intensität in %“ (für realistische, reproduzierbare Ergebnisse)

Beispiel-Code (TS/Node), der basierend auf der Auswahl im UI und der ml-Angabe den korrekten Prompt baut und an Gemini schickt

1. System-Prompt (gemeinsam für alle)

system.txt

You are a precise, medically-plausible image editor for aesthetic filler simulations.
Edit ONLY within the provided binary mask if one is given (white=edit, black=protect).
Strictly preserve the person’s identity, facial anatomy outside the mask, skin pores,
lighting consistency, color balance, and background. Avoid makeup changes, artificial
skin smoothing, or geometry shifts beyond the requested region and intensity.
Return a single, photorealistic image at the same resolution as the input.

Hinweis: Immer Originalfoto (+ optional Region-Maske) mitsenden.
Masken (binär, 0/255) liefern euch harte Region-Kontrolle und damit deutlich stabilere Ergebnisse.

2. User-Prompt-Vorlagen (mit Platzhaltern)
   (A) Lippen
   Task: Simulate a hyaluronic-acid lip filler treatment.

Parameters:

- Target: lips (upper + lower, respect Cupid’s bow)
- Volume: {{VOLUME_ML}} ml total ⇒ intensity ≈ {{INTENSITY_PERCENT}}%
- Goals: balanced volume, slightly more definition at Cupid’s bow,
  natural vermillion texture preserved, no tooth/gum changes.
- Constraints: no edits outside the lip region/mask; no color cast on surrounding skin.

Output: realistic, clinic-style "after" image with natural lip texture and matching lighting.

(B) Wangen (Malar / Midface)
Task: Simulate cheek (malar) filler for midface volumization and mild lift.

Parameters:

- Target: zygomatic arch + malar eminence (both sides; symmetrical)
- Volume: {{VOLUME_ML}} ml total (split evenly) ⇒ intensity ≈ {{INTENSITY_PERCENT}}%
- Goals: subtle projection increase, soft contour improvement, avoid overcorrection near infraorbital area.
- Constraints: no change to nasolabial fold depth beyond natural spillover; keep tear trough unchanged.

Output: photorealistic "after", consistent shadows/highlights, skin texture preserved.

(C) Kinn (Pogonion/Prejowl)
Task: Simulate chin filler to increase anterior projection and refine contour.

Parameters:

- Target: anterior chin (pogonion) ± slight prejowl smoothing if within mask
- Volume: {{VOLUME_ML}} ml ⇒ intensity ≈ {{INTENSITY_PERCENT}}%
- Goals: modest forward projection and gentle lengthening if needed, harmonious jawline transition.
- Constraints: do not change occlusion, lips, or mandibular angle outside the mask.

Output: realistic "after" image with unchanged identity and lighting.

(D) Option 4 (Platzhalter – z. B. Jawline / Nasolabial)
Task: Simulate {{REGION_LABEL}} filler.

Parameters:

- Target: {{REGION_TARGET_DESC}}
- Volume: {{VOLUME_ML}} ml ⇒ intensity ≈ {{INTENSITY_PERCENT}}%
- Goals: {{GOALS_TEXT}}
- Constraints: strictly no edits beyond mask/region.

Output: photorealistic "after" image, natural texture & lighting preserved.

3. Heuristik: ml ➜ Intensität (%)

Diese Mapping sorgt dafür, dass eure Slider-ml-Angaben zu realistischen Prompt-Stufen werden:

# LIPPEN (gesamt-ml):

0.3 ml → ~12%
0.5 ml → ~22%
0.7 ml → ~28%
1.0 ml → ~38%
1.3 ml → ~45%

# WANGEN (gesamt-ml, beidseitig zusammen):

1.0 ml → ~12%
1.5 ml → ~18%
2.0 ml → ~24%
3.0 ml → ~35%

# KINN (gesamt-ml):

0.5 ml → ~12%
0.8 ml → ~18%
1.0 ml → ~22%
1.5 ml → ~30%
2.0 ml → ~38%

Formel (fallback):

INTENSITY_PERCENT = clamp( round( k \* VOLUME_ML ), 8, 48 )

# k für Lippen ≈ 36–40, Wangen ≈ 10–12, Kinn ≈ 16–20

So bekommt ihr konsistente, natürliche Sprünge; >50 % wirkt schnell unnatürlich.

4. Request-Schema aus dem UI
   {
   "procedure": "lips" | "cheeks" | "chin" | "option4",
   "volume_ml": 0.5,
   "image_base64": "<JPEG/PNG base64>",
   "mask_base64": "<PNG base64 or null>"
   }

5. Prompt-Builder & API-Call (TypeScript/Node)

Beispiel nutzt die Gemini CLI via Child-Process oder später direkt das SDK – beides gleiche Prompt-Texte.

// simulation/promptBuilder.ts
type Procedure = "lips" | "cheeks" | "chin" | "option4";

export function mlToIntensity(proc: Procedure, ml: number): number {
const clamp = (v: number, a: number, b: number) => Math.max(a, Math.min(b, v));
const k = proc === "lips" ? 38 : proc === "cheeks" ? 12 : proc === "chin" ? 18 : 15;
return clamp(Math.round(k \* ml), 8, 48);
}

export function buildUserPrompt(proc: Procedure, ml: number): string {
const pct = mlToIntensity(proc, ml);
const blocks: Record<Procedure, string> = {
lips: `Task: Simulate a hyaluronic-acid lip filler treatment.

Parameters:

- Target: lips (upper + lower, respect Cupid’s bow)
- Volume: ${ml} ml total ⇒ intensity ≈ ${pct}%
- Goals: balanced volume, slightly more definition at Cupid’s bow, natural vermillion texture.
- Constraints: no edits outside lip region/mask; no teeth/gum changes.
  Output: clinic-style, photorealistic "after".`,

      cheeks: `Task: Simulate cheek (malar) filler.

Parameters:

- Target: zygomatic arch + malar eminence (both sides)
- Volume: ${ml} ml total (split evenly) ⇒ intensity ≈ ${pct}%
- Goals: subtle projection and contour; avoid infraorbital overfill.
- Constraints: keep tear trough unchanged; no spillover beyond mask.
  Output: realistic "after", texture & lighting preserved.`,

      chin: `Task: Simulate chin filler.

Parameters:

- Target: chin (pogonion) ± slight prejowl smoothing within mask
- Volume: ${ml} ml ⇒ intensity ≈ ${pct}%
- Goals: modest forward projection; harmonious jawline transition.
- Constraints: do not change occlusion or lips; no edits beyond mask.
  Output: photorealistic "after".`,

      option4: `Task: Simulate {{REGION_LABEL}} filler.

Parameters:

- Target: {{REGION_TARGET_DESC}}
- Volume: ${ml} ml ⇒ intensity ≈ ${pct}%
- Goals: {{GOALS_TEXT}}
- Constraints: strict mask-only edits.
  Output: photorealistic "after".`
  };
  return blocks[proc];
  }

CLI-Call (Child-Process):

// simulation/server.ts (Auszug)
import { spawn } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { buildUserPrompt } from "./promptBuilder";

const SYSTEM_PROMPT_PATH = path.join(process.cwd(), "prompts/system.txt");
const TMP_USER = path.join(process.cwd(), "prompts/\_user_tmp.txt");

export async function runGeminiCLI(
userPrompt: string,
imagePath: string,
maskPath?: string
): Promise<string> {
fs.writeFileSync(TMP*USER, userPrompt, "utf8");
const outDir = path.join(process.cwd(), "outputs");
fs.mkdirSync(outDir, { recursive: true });
const outfile = path.join(outDir, `sim*${Date.now()}.png`);

const args = [
"generate",
"--model=gemini-2.5-flash-image-preview",
`--text-file=${SYSTEM_PROMPT_PATH}`,
`--text-file=${TMP_USER}`,
`--image=${imagePath}`,
];
if (maskPath && fs.existsSync(maskPath)) args.push(`--image=${maskPath}`);
args.push(`--output=${outfile}`);

await new Promise<void>((resolve, reject) => {
const p = spawn("gemini", args, { env: process.env });
let err = "";
p.stderr.on("data", d => (err += String(d)));
p.on("close", code => (code === 0 ? resolve() : reject(new Error(err || "CLI failed"))));
});

return outfile;
}

Endpoint (Trigger durch „Generate“ im UI):

// simulation/server.ts (weiter)
import express from "express";
const app = express();
app.use(express.json({ limit: "20mb" }));

app.post("/simulate", async (req, res) => {
try {
const { procedure, volume_ml, image_base64, mask_base64 } = req.body;
const userPrompt = buildUserPrompt(procedure, volume_ml);

    const inDir = path.join(process.cwd(), "inputs");
    fs.mkdirSync(inDir, { recursive: true });
    const imgPath = path.join(inDir, `img_${Date.now()}.jpg`);
    fs.writeFileSync(imgPath, Buffer.from(image_base64, "base64"));
    let maskPath: string | undefined;
    if (mask_base64) {
      maskPath = path.join(inDir, `mask_${Date.now()}.png`);
      fs.writeFileSync(maskPath, Buffer.from(mask_base64, "base64"));
    }

    const outPath = await runGeminiCLI(userPrompt, imgPath, maskPath);
    const b64 = fs.readFileSync(outPath).toString("base64");
    res.json({ image_base64: b64, file: path.basename(outPath) });

} catch (e) {
res.status(500).json({ error: String(e) });
}
});

app.listen(8787, () => console.log("Simulation API on :8787"));

So bindest du’s im UI (4-Auswahlen)

Speichere die User-Auswahl (procedure) in deinem State: "lips" | "cheeks" | "chin" | "option4".

Konvertiere ml ➜ % nicht im UI, sondern serverseitig (wie oben), damit die Logik zentral bleibt.

Beim Klick auf Generate:

Foto + passende Regionen-Maske base64 codieren,

POST /simulate mit { procedure, volume_ml, image_base64, mask_base64 },

Ergebnisbild anzeigen & cachen (für Undo/Vergleich).

Mini-Checkliste

System-Prompt fix

Region-Prompts mit {{VOLUME_ML}} + %-Heuristik

Maskenpflicht (empfohlen) für kontrollierte Edits

Generate-Flow: Auswahl ➜ Prompt-Build ➜ API-Call ➜ Ergebnis

Wenn du mir sagst, was eure „Option 4“ konkret ist, passe ich Prompt + Heuristik sofort an und liefere euch eine masken-Guideline (Landmarks/Flächen) dafür.
