import os
from openai import OpenAI

class LLMHandler:
    def __init__(self, api_key: str = os.environ.get("OPENAI_API_KEY")):
        self.client = OpenAI(api_key=api_key)

        self.context = """
        Please respond with a comma separated list of the kitchen objects in this list that best match the user query.
        The list of kitchen objects is:
        1. Pepper
        2. Salt
        3. Paprika
        4. Garlic
        5. Onion
        6. Tomato
        7. Cucumber
        8. Lettuce
        9. Carrot
        10. Potato
        11. Spatula
        12. Whisk
        13. Heavy Cream
        14. Olive Oil
        15. Butter
        16. Sugar
        17. Flour
        18. Baking Powder
"""

    def query_llm(self, query: str, model: str = "gpt-3.5-turbo"):
        try:
            response = self.client.chat.completions.create(model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "system", "content": self.context},
                {"role": "user", "content": query}
            ])
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"An error occurred: {e}"

if __name__ == "__main__":
    llm_handler = LLMHandler(api_key=os.environ.get("OPENAI_API_KEY"))
    while True:
        user_input = input("Enter your query: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting...")
            break
        response = llm_handler.query_llm(user_input)
        print(response)