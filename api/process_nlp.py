# api/process_nlp.py
from fastapi import FastAPI, Request
import spacy

# Muat model spaCy. Ini mungkin memakan waktu saat pertama kali dijalankan (cold start).
nlp = spacy.load("en_core_web_sm")

app = FastAPI()

@app.post("/api/process_nlp")
async def process_nlp(request: Request):
    body = await request.json()
    text = body.get("text")

    doc = nlp(text)

    # Ekstrak entitas
    date = None
    time = None
    entities = {ent.label_: ent.text for ent in doc.ents}

    if "DATE" in entities:
        date = entities["DATE"]
    if "TIME" in entities:
        time = entities["TIME"]

    # Ekstrak subjek tugas (teks selain tanggal dan waktu)
    non_entity_parts = []
    last_end = 0
    for ent in doc.ents:
        if ent.label_ in ["DATE", "TIME", "CARDINAL"]:
            non_entity_parts.append(text[last_end:ent.start_char])
            last_end = ent.end_char
    non_entity_parts.append(text[last_end:])
    title = "".join(non_entity_parts).strip()


    return {
        "title": title,
        "date": date,
        "time": time,
        "original_text": text
    }