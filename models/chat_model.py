from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

llm=ChatOllama(model="qwen2.5-coder:7b", temperature=0.7)

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a helpful assistant specialized in coding."),
    ("user", "{input}")
])


chain = prompt | llm | StrOutputParser()

if __name__ == "__main__":
    print(chain.invoke({"input": "Write a code to find the factorial of a number in Python."}))

