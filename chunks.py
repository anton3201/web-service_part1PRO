from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.llms.openai import OpenAI
from langchain_community.vectorstores import FAISS
from langchain.docstore.document import Document
from dotenv import load_dotenv
from openai import OpenAI
import openai
import os
import re
import requests
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

# получим переменные окружения из .env
load_dotenv()

# API-key
api_key = os.environ.get("OPENAI_API_KEY")
os.environ["OPENAI_API_KEY"] = api_key
base_url = "https://api.proxyapi.ru/openai/v1"
os.environ["OPENAI_BASE_URL"] = base_url



# задаем system
default_system = "Ты консультант по правилам СТРАХОВАНИЯ ОТВЕТСТВЕННОСТИ АЭРОПОРТОВ И АВИАЦИОННЫХ ТОВАРОПРОИЗВОДИТЕЛЕЙ, ответь на вопрос клиента на основе документа с информацией. Не придумывай ничего от себя, отвечай максимально по документу. Не упоминай Документ с информацией для ответа клиенту. Клиент ничего не должен знать про Документ с информацией для ответа клиенту"


class Chunk():

    def __init__(self, url_doc: str, sep: str = " ", ch_size: int = 1024) -> object:
        # загружаем базу

        document = self.load_document_text(url_doc)
        separeators = ["\n\n", "\n",";", ".", " ", ""]
        # создаем список чанков
        markdown_text = self.text_to_markdown(document)
        source_chunks, fragments = self.split_text(markdown_text, 120)

        # создаем индексную базу
        embeddings = OpenAIEmbeddings(base_url=base_url)
        self.db = FAISS.from_documents(source_chunks, embeddings)

    def load_document_text(self,url: str) -> str:
        # Extract the document ID from the URL
        match_ = re.search('/document/d/([a-zA-Z0-9-_]+)', url)
        if match_ is None:
            raise ValueError('Invalid Google Docs URL')
        doc_id = match_.group(1)

        # Download the document as plain text
        response = requests.get(f'https://docs.google.com/document/d/{doc_id}/export?format=txt')
        response.raise_for_status()
        text = response.text

        return text

    def text_to_markdown(self, text:str):
        # Добавляем заголовок 1 уровня на основе чисел (без переноса строки)
        # и дублируем его строчкой ниже - иначе эта информация перенесется в метаданные, а порой она бывает полезной.
        def replace_header1(match):
            return f"# {match.group(2)}\n{match.group(2)}"

        text = re.sub(r'^(1|2|3|4|5|6|7|8|9|10|11|12|13|14|15|16)\. (.+)', replace_header1, text, flags=re.M)

        # Добавляем текст, выделенный жирным шрифтом (он заключен между *)
        # и дублируем его строчкой ниже
        def replace_header2(match):
            return f"## {match.group(1)}\n{match.group(1)}"

        text = re.sub(r'\*([^\*]+)\*', replace_header2, text)

        return text

    def split_text(self,text: str, max_count):
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
        ]

        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        fragments = markdown_splitter.split_text(text)


        splitter = RecursiveCharacterTextSplitter(
            chunk_size=max_count,
            chunk_overlap=0,
            separators=["\n\n", "\n", ".", " ", ";", ""],
        )

        source_chunks = [
            Document(page_content=chunk, metadata=fragment.metadata)
            for fragment in fragments
            for chunk in splitter.split_text(fragment.page_content)
        ]

        return source_chunks, fragments

    def get_answer(self, system: str = default_system, query: str = None):
        '''Функция получения ответа от chatgpt
        '''
        client = OpenAI(base_url=base_url)
        # релевантные отрезки из базы
        docs = self.db.similarity_search(query, k=4)
        message_content = '\n'.join([f'{doc.page_content}' for doc in docs])
        messages = [
            {"role": "system", "content": system},
            {"role": "user",
             "content": f"Ответь на вопрос клиента. Не упоминай документ с информацией для ответа клиенту в ответе. Документ с информацией для ответа клиенту: {message_content}\n\nВопрос клиента: \n{query}"}
        ]

        # получение ответа от chatgpt
        completion = client.chat.completions.create(model="gpt-3.5-turbo",
                                                  messages=messages,
                                                  temperature=0)

        return completion.choices[0].message.content