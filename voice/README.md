# VECTOR Voice

The voice front-end for VECTOR. It listens for a wake word, transcribes what you
say, sends it to the VECTOR server, and speaks the reply.

```
 wake word  ──►  speech-to-text  ──►  VECTOR server  ──►  text-to-speech
 (Enter)         (stdin/whisper)      /assistant/command   (print/pyttsx3)
```

Every stage is an interface with a **console fallback**, so you can run the full
loop with no microphone or speaker — great for developing against the server.

## Run it

```bash
pip install -r requirements.txt          # just httpx for console mode
# make sure the server is running (see ../server)
python -m vector_voice
```

Then talk to it:

```
[press Enter to talk to vector]
you> turn on the living room lights and vacuum the floor
vector> Here's what I did:
- on living room lights
- dispatched robot to clean
```

Type `quit` (or Ctrl-D) to exit.

## Configuration

Set via environment variables (see repo-root `.env.example`) or
`config.example.yaml`:

| Variable               | Default                 | Meaning |
|------------------------|-------------------------|---------|
| `VECTOR_SERVER_URL`    | `http://localhost:8000` | Server endpoint |
| `VECTOR_WAKE_WORD`     | `vector`                | Wake word |
| `VECTOR_WAKE_BACKEND`  | `console`               | `console` · `openwakeword` · `porcupine` |
| `VECTOR_STT_BACKEND`   | `console`               | `console` · `whisper` |
| `VECTOR_TTS_BACKEND`   | `console`               | `console` · `pyttsx3` · `piper` |

## Adding real audio

The `openwakeword`, `faster-whisper` and `pyttsx3`/`piper` backends are stubbed
in `wake_word.py`, `stt.py` and `tts.py` with clear `NotImplementedError`
markers showing exactly where to stream microphone audio. Install the optional
dependencies from `requirements.txt`, wire up your mic (e.g. `sounddevice`), and
switch the backend via the config.
