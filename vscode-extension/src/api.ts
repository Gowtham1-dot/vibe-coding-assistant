// If you ever see "fetch not found" in your environment, uncomment the next two lines:
//@ts-ignore

import 'undici/register';

const SERVICE_URL = 'http://127.0.0.1:5317/speak';

type SpeakResponse = {
  audio_b64: string;
  mime: string;
};

// Return the shape the rest of the extension expects: { audioB64, mime }
export async function speakText(text: string): Promise<{ audioB64: string; mime: string }> {
  const resp = await fetch(SERVICE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });

  if (!resp.ok) {
    const t = await resp.text();
    throw new Error(`HTTP ${resp.status}: ${t}`);
  }

  // json() is typed as unknown → cast and validate
  const data = (await resp.json()) as SpeakResponse;

  if (!data || typeof data.audio_b64 !== 'string' || typeof data.mime !== 'string') {
    throw new Error('Unexpected response shape from local service');
  }

  return { audioB64: data.audio_b64, mime: data.mime };
}
