from typing import Annotated, Literal

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from .decoder import decode_record

DotDash = Annotated[str, Field(min_length=1, max_length=60, pattern=r"^[.-]+$")]
CandidateWord = Annotated[str, Field(min_length=1, max_length=12, pattern=r"^[A-Z]+$")]


class DecodeRequest(BaseModel):
    model_config = {"extra": "forbid"}

    record: DotDash
    candidates: Annotated[list[CandidateWord], Field(min_length=1, max_length=20)]


class DecodeResponse(BaseModel):
    words: list[str]
    morse: str
    edits: int


app = FastAPI(
    title="缺分隔电报码校读 API",
    description="在 1～6 个候选词的所有无分隔拼接中全局寻找编辑距离最小的序列。",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"detail": jsonable_encoder(exc.errors())},
    )

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"service": "morse-decoder", "decode_endpoint": "/api/decode"}


@app.get("/health", tags=["system"])
def health() -> dict[Literal["status"], str]:
    return {"status": "ok"}


@app.post("/api/decode", response_model=DecodeResponse, tags=["decode"])
def decode(request: DecodeRequest) -> DecodeResponse:
    words, morse, edits = decode_record(request.record, request.candidates)
    return DecodeResponse(words=words, morse=morse, edits=edits)
