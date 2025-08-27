Klar – hier ist die offizielle Vorgehensweise, um ein Bild + Text an Gemini 2.5 Flash Image zu senden und ein Bild zurückzubekommen (API):

Python (google-genai SDK)

# pip install google-genai pillow

from google import genai
from PIL import Image
from io import BytesIO

client = genai.Client() # liest GOOGLE_API_KEY aus der Umgebung

prompt = (
"Enhance lip volume by ~25% with a natural clinic-style look. "
"Preserve identity, skin texture and lighting. Edit lips only."
)

# Bild laden (PIL-Image oder Bytes sind ok)

img = Image.open("face.jpg")

resp = client.models.generate_content(
model="gemini-2.5-flash-image-preview",
contents=[prompt, img], # <— Text + Bild als Input
)

# Bild aus der Antwort speichern (inline_data ist Base64-Bild)

for part in resp.candidates[0].content.parts:
if getattr(part, "inline_data", None):
out = Image.open(BytesIO(part.inline_data.data))
out.save("edited_face.png")
print("Saved:", "edited_face.png")

Quelle/Beispielstruktur: „Image generation / editing (text-and-image-to-image)“ in den Gemini-API Docs.
Google AI for Developers

Node.js (offizielles @google/genai)
// npm i @google/genai
import { GoogleGenAI } from "@google/genai";
import \* as fs from "node:fs";

const ai = new GoogleGenAI({ apiKey: process.env.GOOGLE_API_KEY });

const imagePath = "face.jpg";
const base64Image = fs.readFileSync(imagePath).toString("base64");

const contents = [
{ text: "Enhance lip volume by ~25% naturally; preserve identity/skin; edit lips only." },
{
inlineData: {
mimeType: "image/jpeg",
data: base64Image, // <— Bild + Text zusammen senden
},
},
];

const resp = await ai.models.generateContent({
model: "gemini-2.5-flash-image-preview",
contents
});

// Bildteil extrahieren und speichern
for (const part of resp.candidates[0].content.parts) {
if (part.inlineData) {
fs.writeFileSync("edited_face.png", Buffer.from(part.inlineData.data, "base64"));
console.log("Saved edited_face.png");
}
}

Offizielle JS-Beispiele für Text+Bild→Bild inkl. Base64-Handling findest du in derselben Doku-Seite.
Google AI for Developers

REST (cURL)
IMG_BASE64="$(base64 -w0 face.jpg)"
curl -s -X POST \
  "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-image-preview:generateContent" \
  -H "x-goog-api-key: $GOOGLE_API_KEY" \
  -H "Content-Type: application/json" \
  -d "{
    \"contents\": [{
      \"parts\": [
        {\"text\": \"Enhance lip volume by ~25% naturally; preserve identity/skin; edit lips only.\"},
        {\"inline_data\": {\"mime_type\": \"image/jpeg\", \"data\": \"$IMG_BASE64\"}}
]
}]
}" \
| grep -o '"data": "[^"]\*"' | head -n1 | cut -d'"' -f4 | base64 --decode > edited_face.png

Das REST-Pattern (Text + inline_data Bild) ist in der offiziellen Seite inkl. Beispiel gezeigt.
Google AI for Developers
