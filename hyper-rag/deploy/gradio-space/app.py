"""Hyper-RAG on a Gradio-SDK Space (docs/DEPLOY.md).

Docker Spaces need a paid plan; a free account may host Gradio Spaces on ZeroGPU. A Gradio
Space runs this file and expects a server on port 7860, so this serves the FastAPI app
there, with a one-line Gradio page mounted at /gradio because the SDK expects one.

Layout of the Space repository: this file, README.md, requirements.txt, and from
hyper-rag/: config.yaml, src/, packs/ and web/dist/ (built on your machine).
"""

import os
import sys

sys.path.insert(0, "src")
# A Space sets GRADIO_SSR_MODE=True, and mounting Gradio then starts a Node server on the
# Space's port before uvicorn can bind it. This app renders its own pages.
os.environ["GRADIO_SSR_MODE"] = "False"

import gradio as gr  # noqa: E402
import spaces  # noqa: E402
import uvicorn  # noqa: E402

from hyper_rag.api import app  # noqa: E402


@spaces.GPU
def gpu_check() -> str:
    """ZeroGPU looks for a GPU function at start-up. The app itself runs on the CPU."""
    return "ok"


with gr.Blocks() as page:
    gr.Markdown("Hyper-RAG is served at [the root of this Space](/).")

app = gr.mount_gradio_app(app, page, path="/gradio", ssr_mode=False)


def report_to_zerogpu() -> None:
    """ZeroGPU checks for @spaces.GPU functions inside gr.Blocks.launch(), which this file
    never calls (uvicorn serves the app). Without the report the Space is stopped."""
    from spaces.config import Config

    if Config.zero_gpu:
        from spaces.zero import client

        client.startup_report()


if __name__ == "__main__":
    report_to_zerogpu()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "7860")),
        proxy_headers=True,
        forwarded_allow_ips="*",
    )
