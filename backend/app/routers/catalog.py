import hashlib
import json

from fastapi import APIRouter, Response

from app import reference
from app.errors import ApiError
from app.services.catalog_read import load_catalog_or_404, search_catalog
from app.utils import paginate_params

router = APIRouter(tags=["catalog"])


@router.get("/catalog")
async def get_catalog(response: Response):
    catalog = await load_catalog_or_404()
    body = json.dumps(catalog, sort_keys=True, default=str).encode("utf-8")
    etag = hashlib.sha256(body).hexdigest()[:16]
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = "public, max-age=60"
    return catalog


@router.get("/catalog/search")
async def search(
    q: str | None = None,
    category: str | None = None,
    language: str | None = None,
    section: str | None = None,
    limit: int = 50,
    offset: int = 0,
):
    if category is not None and category not in reference.category_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{category}" is not a supported category.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "category",
                    "message": "See reference.json categories.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )
    if language is not None and language not in reference.language_codes():
        codes = ", ".join(
            f'{lang["code"]} ({lang["label"]})' for lang in reference.load_reference()["languages"]
        )
        raise ApiError(
            422,
            "validation_error",
            f'"{language}" is not a supported language.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "language",
                    "message": f"Supported languages are: {codes}.",
                    "hint": "Remove the language filter or use one of the supported codes.",
                    "resource": None,
                }
            ],
        )
    if section is not None and section not in reference.section_keys():
        raise ApiError(
            422,
            "validation_error",
            f'"{section}" is not a supported section.',
            [
                {
                    "code": "ENUM_NOT_ALLOWED",
                    "field": "section",
                    "message": "See reference.json sections.",
                    "hint": None,
                    "resource": None,
                }
            ],
        )

    catalog = await load_catalog_or_404()
    limit, offset = paginate_params(limit, offset)
    results, total = search_catalog(catalog, q, category, language, section, limit, offset)
    return {
        "query": {"q": q, "category": category, "language": language, "section": section},
        "catalog_version": catalog.get("catalog_version"),
        "total": total,
        "limit": limit,
        "offset": offset,
        "results": results,
    }
