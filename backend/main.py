import os
import random
import string
from contextlib import asynccontextmanager
from datetime import datetime

import psycopg
from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool
from pydantic import BaseModel, HttpUrl

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:test@localhost:5432/postgres"
)
CODE_ALPHABET = string.ascii_letters + string.digits
CODE_LENGTH = 7

pool = ConnectionPool(DATABASE_URL, kwargs={"row_factory": dict_row}, open=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    pool.open()
    yield
    pool.close()


app = FastAPI(title="URL Shortener", lifespan=lifespan)


class ShortenRequest(BaseModel):
    url: HttpUrl


class UrlOut(BaseModel):
    id: int
    code: str
    original_url: str
    created_at: datetime
    click_count: int


def generate_code() -> str:
    return "".join(random.choices(CODE_ALPHABET, k=CODE_LENGTH))


@app.post("/shorten", response_model=UrlOut, status_code=201)
def shorten(body: ShortenRequest):
    with pool.connection() as conn:
        # Retry in the unlikely case the random code already exists.
        for _ in range(5):
            try:
                return conn.execute(
                    """
                    INSERT INTO urls (code, original_url)
                    VALUES (%s, %s)
                    RETURNING id, code, original_url, created_at, click_count
                    """,
                    (generate_code(), str(body.url)),
                ).fetchone()
            except psycopg.errors.UniqueViolation:
                conn.rollback()
    raise HTTPException(status_code=500, detail="Could not generate a unique code")


@app.get("/urls", response_model=list[UrlOut])
def list_urls():
    with pool.connection() as conn:
        return conn.execute(
            "SELECT id, code, original_url, created_at, click_count FROM urls ORDER BY id"
        ).fetchall()


@app.delete("/urls/{url_id}", status_code=204)
def delete_url(url_id: int):
    with pool.connection() as conn:
        deleted = conn.execute("DELETE FROM urls WHERE id = %s", (url_id,)).rowcount
    if deleted == 0:
        raise HTTPException(status_code=404, detail="URL not found")


# Keep this route declared last: "/{code}" matches any path, so more
# specific routes like "/urls" must be registered before it.
@app.get("/{code}")
def redirect(code: str):
    with pool.connection() as conn:
        row = conn.execute(
            "SELECT original_url FROM urls WHERE code = %s", (code,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Short URL not found")
    return RedirectResponse(row["original_url"], status_code=302)
