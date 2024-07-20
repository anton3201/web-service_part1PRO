# This is a sample Python script.
from fastapi import FastAPI
from chunks import Chunk
import openai
from pydantic import BaseModel
from dotenv import load_dotenv


# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

class Item(BaseModel):
    text: str


# создаем объект приложения
app = FastAPI()


# функция обработки get запроса + декоратор
@app.get("/")
def read_root():
    return {"message": "answer"}


# функция обработки post запроса + декоратор
@app.post("/api/get_answer")
def get_answer(question: Item):
    ch = Chunk("https://docs.google.com/document/d/11MU3SnVbwL_rM-5fIC14Lc3XnbAV4rY1Zd_kpcMuH4Y")
    answer = ch.get_answer(query=question.text)
    return {"message": answer}
