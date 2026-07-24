import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import networkx as nx
import config
from graph_loader import load_graph
from gbsa import GbSA
from modularity import calculate_modularity
from llm import analyze_results, suggest_parameters, chat_qa
from autotune import run_autotune

app = FastAPI(title="GbSA Community Detection")

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.post("/api/run")
async def run_gbsa(
    file: UploadFile | None = File(default=None),
    population_size: int = Form(default=20),
    iterations: int = Form(default=50),
):
    # بارگذاری گراف
    if file is not None and file.filename:
        # ذخیره فایل آپلودی در temp
        suffix = os.path.splitext(file.filename)[1] or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        graph = load_graph(tmp_path)
        os.unlink(tmp_path)
        source = file.filename
    else:
        # گراف پیش‌فرض
        if os.path.exists(config.dataset_path):
            graph = load_graph(config.dataset_path)
        else:
            graph = nx.karate_club_graph()
        source = "karate (default)"

    nodes = list(graph.nodes())
    # نرمال‌سازی برچسب نودها به ایندکس 0..n-1 برای خروجی یکدست
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    edges = [
        {"source": node_to_idx[u], "target": node_to_idx[v]}
        for u, v in graph.edges()
    ]

    # اجرای GbSA
    algorithm = GbSA(
        graph=graph,
        population_size=population_size,
        iterations=iterations,
    )
    best_partition, history = algorithm.run()
    best_q = calculate_modularity(graph, best_partition)

    # ساخت دیکشنری communityها
    communities = {}
    for i, node in enumerate(nodes):
        comm_id = best_partition[i]
        communities.setdefault(comm_id, []).append(node_to_idx[node])

    return JSONResponse(
        {
            "source": source,
            "num_nodes": len(nodes),
            "num_edges": len(edges),
            "nodes": [{"id": node_to_idx[node]} for node in nodes],
            "edges": edges,
            "partition": best_partition,
            "communities": {str(k): v for k, v in communities.items()},
            "modularity": best_q,
            "history": history,
            "num_communities": len(communities),
        }
    )


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---------- LLM endpoints ----------

class AnalyzeRequest(BaseModel):
    data: dict


@app.post("/api/llm/analyze")
def llm_analyze(req: AnalyzeRequest):
    if not config.llm_enabled:
        return JSONResponse({"error": "LLM is disabled in config.py"}, status_code=400)
    try:
        report = analyze_results(req.data)
        return {"report": report}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/llm/suggest")
def llm_suggest(req: AnalyzeRequest):
    if not config.llm_enabled:
        return JSONResponse({"error": "LLM is disabled in config.py"}, status_code=400)
    try:
        params = suggest_parameters(
            num_nodes=req.data.get("num_nodes", 34),
            num_edges=req.data.get("num_edges", 78),
        )
        return params
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


class ChatRequest(BaseModel):
    data: dict
    question: str


@app.post("/api/llm/chat")
def llm_chat(req: ChatRequest):
    if not config.llm_enabled:
        return JSONResponse({"error": "LLM is disabled in config.py"}, status_code=400)
    try:
        answer = chat_qa(req.data, req.question)
        return {"answer": answer}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/llm/autotune")
async def llm_autotune(
    file: UploadFile | None = File(default=None),
    population_size: int = Form(default=20),
    iterations: int = Form(default=50),
    max_attempts: int = Form(default=3),
    threshold: float = Form(default=0.4),
):
    """
    حلقه خودتنظیم Executor + Critic:
    اجرای GbSA، نقد نتیجه، پیشنهاد پارامتر، تکرار تا N بار / آستانه Q / بدون بهبود.
    """
    # بارگذاری گراف (همان منطق /api/run)
    if file is not None and file.filename:
        suffix = os.path.splitext(file.filename)[1] or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        graph = load_graph(tmp_path)
        os.unlink(tmp_path)
        source = file.filename
    else:
        if os.path.exists(config.dataset_path):
            graph = load_graph(config.dataset_path)
        else:
            graph = nx.karate_club_graph()
        source = "karate (default)"

    try:
        result = run_autotune(
            graph=graph,
            population_size=population_size,
            iterations=iterations,
            max_attempts=max_attempts,
            threshold=threshold,
        )
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    # نرمال‌سازی خروجی گراف مثل /api/run
    nodes = list(graph.nodes())
    node_to_idx = {node: i for i, node in enumerate(nodes)}
    edges = [
        {"source": node_to_idx[u], "target": node_to_idx[v]}
        for u, v in graph.edges()
    ]
    partition = result["best_partition"]
    communities = {}
    for i, node in enumerate(nodes):
        comm_id = partition[i]
        communities.setdefault(comm_id, []).append(node_to_idx[node])

    return JSONResponse(
        {
            "source": source,
            "num_nodes": result["num_nodes"],
            "num_edges": result["num_edges"],
            "nodes": [{"id": node_to_idx[node]} for node in nodes],
            "edges": edges,
            "partition": partition,
            "communities": {str(k): v for k, v in communities.items()},
            "modularity": result["best_modularity"],
            "history": result["history"],
            "num_communities": result["num_communities"],
            "best_params": result["best_params"],
            "attempts": result["attempts"],
            "stop_reason": result["stop_reason"],
            "explanation_fa": result["explanation_fa"],
            "threshold": result["threshold"],
            "max_attempts": result["max_attempts"],
        }
    )


def serve():
    """اجرای سرور FastAPI با uvicorn"""
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    serve()