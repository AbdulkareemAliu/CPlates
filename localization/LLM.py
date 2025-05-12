import os
from openai import OpenAI

class LLMHandler:
    def __init__(self, api_key: str = os.environ.get("OPENAI_API_KEY")):
        self.client = OpenAI(api_key=api_key)

        self.context = """
        Please respond with the id value of kitchen object in this list that best match the user query. Please do not return anything else! If there is a match please give a response in the format "object, id". Otherwise, return "None".
        The list of kitchen objects is:
        
        name | id
        Cheese | E23456780000000000000031 
        Salt | E23456780000000000000031
        Paprika | E23456780000000000000031
        Garlic | E23456780000000000000031
        Onion | E23456780000000000000031
        Tomato | E23456780000000000000031
        Cucumber | E23456780000000000000031
        Lettuce | E23456780000000000000031
        Carrot | E23456780000000000000031
        Potato | E23456780000000000000031
        Spatula | E23456780000000000000031
        Whisk | E23456780000000000000031
        Heavy Cream | E23456780000000000000031
        Olive Oil | E23456780000000000000031
        Butter | E23456780000000000000031
        Sugar | E23456780000000000000031
        Flour | E23456780000000000000031
        Baking Powder | E23456780000000000000031
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