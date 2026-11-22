import subprocess
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

load_dotenv()

from controller.meeting import router as meeting_router
from controller.prize import router as prize_router
from controller.manager import router as manager_router
from controller.employee import router as employee_router
from controller.nominate import router as nominate_router
from controller.judge import router as judge_router
from controller.vote import router as vote_router
from controller.report import router as report_router
from controller.template import router as template_router
from core.config import STATIC_DIR
from core.database import connect_db, disconnect_db, engine
# Redis 目前沒有任何功能使用，暫時停用。部署環境（例如 Railway）不需要提供 Redis。
# 需要時取消以下註解，並恢復 lifespan 中的兩行與 requirements.txt 中的 Redis 套件
# from core.redis import Redis
#
# redis = Redis()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # await redis.create_redis_pool()
    # app.state.redis = redis
    await connect_db()
    yield
    await disconnect_db()
    # await redis.close_redis_pool()


app = FastAPI(title="Employee Recognition API", lifespan=lifespan)

@app.get("/health")
async def health():
    return {"status": "ok"}

# webClient 的靜態檔案。資料夾不存在時（例如部署環境沒有 webClient）不掛載，伺服器仍可正常啟動
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(meeting_router)
app.include_router(prize_router)
app.include_router(manager_router)
app.include_router(employee_router)
app.include_router(nominate_router)
app.include_router(judge_router)
app.include_router(vote_router)
app.include_router(report_router)
app.include_router(template_router)   # webClient 頁面，放在最後，避免與 API 路徑衝突
