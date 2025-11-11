from fastapi import FastAPI
from fastapi.responses import JSONResponse
import requests, json, os

app = FastAPI()

@app.get("/")
def root():
    return {"message": "Onshape API server running!"}

@app.get("/test")
def test():
    return {"status": "ok"}
