"""FastAPI 应用：缺分隔电报码校读接口。"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from .morse import InvalidInput, best_correction, validate_input

app = FastAPI(
    title="缺分隔电报码校读 API",
    description="对无分隔点划记录在候选词拼接空间中做全局最小编辑距离校读。",
    version="1.0.0",
)


class CorrectRequest(BaseModel):
    record: str
    words: list[str]


class CorrectResponse(BaseModel):
    words: list[str]
    morse: str
    edits: int


@app.exception_handler(InvalidInput)
async def invalid_input_handler(_request: Request, exc: InvalidInput) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(RequestValidationError)
async def validation_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    # 字段缺失 / 类型不符 / JSON 非法等一律按契约返回 400
    return JSONResponse(status_code=400, content={"detail": exc.errors()})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/correct", response_model=CorrectResponse)
async def correct(payload: CorrectRequest) -> CorrectResponse:
    record, words = validate_input(payload.record, payload.words)
    result = best_correction(record, words)
    return CorrectResponse(**result)
