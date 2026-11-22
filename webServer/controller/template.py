from fastapi import APIRouter, Request
from fastapi.responses import FileResponse
from fastapi.templating import Jinja2Templates

from core.config import INDEX_HTML, TEMPLATE_DIR

router = APIRouter(tags=["pages"])

templates = Jinja2Templates(directory=TEMPLATE_DIR)


@router.get("/index")
async def page_index():
    return FileResponse(INDEX_HTML)


@router.get("/")
async def page_login(request: Request):
    return templates.TemplateResponse(request, "meeting.html")


@router.get("/meeting_detail")
async def page_register(request: Request):
    return templates.TemplateResponse(request, "meeting_detail.html")


@router.get("/vote")
async def page_home(request: Request):
    return templates.TemplateResponse(request, "vote.html")


@router.get("/vote_detail")
async def page_edit_clinician_profile(request: Request):
    return templates.TemplateResponse(request, "vote_detail.html")
