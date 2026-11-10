"""Wires the pieces together. The CLI and the API both build their agent here."""

from hyper_rag.agent import Agent
from hyper_rag.config import Settings
from hyper_rag.index import load_retriever
from hyper_rag.llm import build_llm
from hyper_rag.packs import load_pack


def build_agent(pack_name: str, settings: Settings) -> Agent:
    pack = load_pack(settings.packs_dir, pack_name)
    return Agent(
        retriever=load_retriever(pack, settings),
        llm=build_llm(settings, "generator"),
        pack_description=pack.config.description,
        max_rewrites=settings.max_rewrites,
        control_llm=build_llm(settings, "control"),
    )
