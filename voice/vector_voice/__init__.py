"""VECTOR voice assistant client.

A small, dependency-light pipeline:

    wake word  ->  speech-to-text  ->  VECTOR server  ->  text-to-speech

Every stage is an interface with a lightweight *console* fallback, so the whole
loop runs on a laptop with no microphone. Swap in real backends (openWakeWord,
faster-whisper, Piper) by installing the optional extras and setting the
backend in the config.
"""

__version__ = "0.1.0"
