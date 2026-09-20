from fastapi import FastAPI, UploadFile
from pydantic import BaseModel, Field
from typing import List
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.resolve()))
from gemini import read_tray

app = FastAPI()

@app.post("/trays")
def create_tray(file: UploadFile):
    image_bytes = file.file.read()
    reading = read_tray(image_bytes, file.content_type)
    return reading