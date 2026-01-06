# from langchain.document_loaders import DirectoryLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
# from langchain.embeddings import OpenAIEmbeddings
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader,PyPDFLoader
import openai 
from dotenv import load_dotenv
import os
import shutil
from langchain_huggingface import HuggingFaceEmbeddings
# import nltk
# import sys
# sys.path.append('/home/kyzhang24/.local/lib/python3.10/site-packages')
# nltk.download('punkt')
# Load environment variables. Assumes that project contains .env file with API keys
load_dotenv()
#---- Set OpenAI API key 
# Change environment variable name from "OPENAI_API_KEY" to the name given in 
# your .env file.

# API_SECRET_KEY = "sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"
# BASE_URL = "https://svip.xty.app/v1"
# os.environ["OPENAI_API_KEY"] = API_SECRET_KEY
# os.environ["OPENAI_API_BASE"] = BASE_URL
# openai.api_key = os.environ['OPENAI_API_KEY']


# API_SECRET_KEY = "sk-r0WeYOdkMjzYdnSxEcC8B931Aa904e4bBaCcAc2a57D803F1"
# BASE_URL = "https://svip.xty.app/v1"
# os.environ["OPENAI_API_KEY"] = API_SECRET_KEY
# os.environ["OPENAI_API_BASE"] = BASE_URL
# openai.api_key = os.environ['OPENAI_API_KEY']


embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")

CHROMA_PATH = "chroma"


def main():
    generate_data_store()


def generate_data_store():
    documents = load_documents()
    chunks = split_text(documents)
    save_to_chroma(chunks)


def load_documents():
    # loader = TextLoader(DATA_PATH)
    # documents = loader.load()
    # return documents
    loaders = [TextLoader('./term.txt', encoding='utf-8'),TextLoader('./corpus.txt', encoding='utf-8'),TextLoader('./law_explanation.txt', encoding='utf-8')]
    docs = []
    for loader in loaders:
        pages = loader.load()
        docs.extend(pages)
    return docs


def split_text(documents: list[Document]):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=300,
        chunk_overlap=100,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    document = chunks[10]
    print(document.page_content)
    print(document.metadata)

    return chunks


def save_to_chroma(chunks: list[Document]):
    # Clear out the database first.
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # Create a new DB from the documents.
    # old: OpenAIEmbeddings(model="text-embedding-3-large")
    db = Chroma.from_documents(
        chunks, embeddings, persist_directory=CHROMA_PATH
    )
    db.persist()
    print(f"Saved {len(chunks)} chunks to {CHROMA_PATH}.")


if __name__ == "__main__":
    main()
