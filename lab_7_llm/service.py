"""
Web service for model inference.
"""
# pylint: disable=undefined-variable
import json

import pandas as pd
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic.dataclasses import dataclass

from config.constants import PROJECT_ROOT
from lab_7_llm.main import LLMPipeline, TaskDataset


@dataclass
class Query:
    """
    Abstraction which contains text of the query.
    """
    question: str


def init_application() -> tuple[FastAPI, LLMPipeline]:
    """
    #doctest: +SKIP
    Initialize core application.

    Run: uvicorn reference_service.server:app --reload

    Returns:
        tuple[fastapi.FastAPI, LLMPipeline]: instance of server and pipeline
    """
    server = FastAPI()
    server.mount("/assets", StaticFiles(directory="assets"), name="assets")

    with open(PROJECT_ROOT / 'lab_7_llm' / 'settings.json', 'r', encoding='utf-8') as settings_file:
        configs = json.load(settings_file)

    dataset = TaskDataset(pd.DataFrame())
    llm = LLMPipeline(configs['parameters']['model'], dataset, 120, 1, 'cpu')
    return server, llm


app, pipeline = init_application()


@app.get("/", response_class=HTMLResponse)
async def root(request: Request) -> HTMLResponse:
    """
    Root endpoint.

    Args:
        request (Request): request.

    Returns:
        HTMLResponse: start page of the webservice.
    """
    templates = Jinja2Templates(directory='assets')
    return templates.TemplateResponse('index.html', {'request': request})


@app.post("/infer")
async def infer(query: Query) -> dict:
    """
    Infer a query from webservice.

    Args:
        query (Query): user's query.

    Returns:
        dict: a dictionary with a prediction.
    """
    sample = (query.question.split('|'))
    labels_mapping = pipeline.get_config()['id2label']
    if len(sample) == 1:
        sample_tuple = (sample[0], sample[0])
    else:
        sample_tuple = (sample[0], sample[1])
    prediction = pipeline.infer_sample(sample_tuple)
    return {'infer': labels_mapping.get(prediction)}


if __name__ == "__main__":
    uvicorn.run("service:app", host='127.0.0.1', port=8000, reload=True)
