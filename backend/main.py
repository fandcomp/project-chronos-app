# backend/main.py
from fastapi import FastAPI
from api import process_nlp, process_pdf, suggest_slot

app = FastAPI()

# Gabungkan semua rute dari file API Anda
app.include_router(process_nlp.app.router)
app.include_router(process_pdf.app.router)
app.include_router(suggest_slot.app.router)

@app.get("/")
def read_root():
    return {"Hello": "From Chronos Backend"}