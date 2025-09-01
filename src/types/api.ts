// If fetch is ever missing in the Dev Host, install undici and uncomment:
// // @ts-ignore
// import 'undici/register';

const SERVICE_URL = 'http://127.0.0.1:8001/speak';


type SpeakResponse = { audio_b64: string; mime: string };

export async function speakText(text: string): Promise<{ audioB64: string; mime: string }> {
  const resp = await fetch(SERVICE_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text })
  });
  if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${await resp.text()}`);

  const data = (await resp.json()) as SpeakResponse;
  if (!data?.audio_b64 || !data?.mime) throw new Error('Unexpected response from /speak');

  // return camelCase for the extension
  return { audioB64: data.audio_b64, mime: data.mime };
}
