import sys
import tty
import json
import termios
import threading
from queue import Queue
import sounddevice as sd
from vosk import Model, KaldiRecognizer

class SpeechHandler:
    def __init__(self, model_path, start_stop_key="p", exit_key="c"):
        assert start_stop_key != exit_key, "Start/stop key must differ from exit key"
        # download model from https://alphacephei.com/vosk/models

        self.start_stop_key = start_stop_key
        self.exit_key = exit_key

        self.model = Model(model_path)
        self.recognizer = KaldiRecognizer(self.model, 16000)
        self.audio_queue = Queue()
        self.listening = False
        self.transcribed_text = []

    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio error: {status}")
        self.audio_queue.put(bytes(indata))

    def listen_and_transcribe(self):
        with sd.RawInputStream(samplerate=16000, blocksize=1024, dtype='int16',
                               channels=1, callback=self.audio_callback, latency='low'):

            print("Started listening")
            while self.listening:
                data = self.audio_queue.get()
                if self.recognizer.AcceptWaveform(data):
                    result = json.loads(self.recognizer.Result())
                    self.transcribed_text.append(result.get("text", ""))
                    print(" ".join(self.transcribed_text).strip())

    def toggle_listening(self):
        if not self.listening:
            self.listening = True
            threading.Thread(target=self.listen_and_transcribe, daemon=True).start()
        else:
            print("Stopped listening")
            self.listening = False
            text = " ".join(self.transcribed_text)
            self.transcribed_text.clear()
            return text

    def get_key(self):
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            key = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return key
    
    def record(self):
        stop_listening = False
        while not stop_listening:
            key = self.get_key()
            if key == self.start_stop_key and not self.listening:
                self.toggle_listening()
                stop_listening = False
            elif key == self.start_stop_key and self.listening:
                transcribed_text = self.toggle_listening()
                stop_listening = True

        return transcribed_text
        
if __name__ == "__main__":
    handler = SpeechHandler("./ml/vosk-model-small-en-us-0.15", "p")
    transcription = handler.record()
    print(transcription)