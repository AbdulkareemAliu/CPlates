import os
from llm_handler import LLMHandler
from speech_handler import SpeechHandler

if __name__ == "__main__":

    speech_handler = SpeechHandler("ml/vosk-model-small-en-us-0.15", "p")

    llm_handler = LLMHandler()

    query = speech_handler.record()

    if query:
        response = llm_handler.query_llm(query)
        print("User Query:", query)
        print("LLM Response:", response)
    else:
        print("No query recorded.")
