from langchain_ollama import OllamaEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser


embeddings=OllamaEmbeddings(model='qwen3-embedding:4b',temperature=0.2,dimensions=1536)

result=embeddings.embed_query("Suggest me a funny name for Subhayu");

print(str(result))





