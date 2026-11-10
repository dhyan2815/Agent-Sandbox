"""HTTP API: POST /ask returns an answer with citations.

Run with:  uvicorn hyper_rag.api:app
Set HYPER_RAG_OFFLINE=1 to serve with the fake LLM and hashing embedder (no key, no network).
"""

import os
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from hyper_rag.agent import Agent
from hyper_rag.config import Settings, load_settings
from hyper_rag.llm import LLMError
from hyper_rag.packs import list_packs
from hyper_rag.service import build_agent

app = FastAPI(title="Hyper-RAG", version="0.1.0")


class AskRequest(BaseModel):
    pack: str = Field(examples=["payments"])
    question: str = Field(min_length=3, max_length=500)


class Citation(BaseModel):
    number: int
    title: str
    url: str
    chunk_id: str
    text: str


class AskResponse(BaseModel):
    question: str
    answer: str
    refused: bool
    citations: list[Citation]
    trace: list[str]
    llm_calls: int


@lru_cache
def get_settings() -> Settings:
    return load_settings(offline=os.environ.get("HYPER_RAG_OFFLINE") == "1")


@lru_cache
def get_agent(pack: str) -> Agent:
    # Building an agent loads the index and the embedding model, so keep one per pack.
    return build_agent(pack, get_settings())


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/packs")
def packs() -> dict:
    return {"packs": list_packs(get_settings().packs_dir)}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> dict:
    try:
        agent = get_agent(request.pack)
    except FileNotFoundError as error:  # unknown pack, or pack not ingested yet
        raise HTTPException(status_code=404, detail=str(error)) from error
    try:
        return agent.ask(request.question).to_dict()
    except LLMError as error:  # provider down or rate limited
        raise HTTPException(status_code=503, detail=str(error)) from error
