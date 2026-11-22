import uuid

from fastapi.responses import JSONResponse

from util.logger import get_logger

logger = get_logger()

 
class HttpResponseMethod:
 
    @staticmethod
    def _build_content(result: bool, data: object, message: str) -> dict:
        return {
            "result": result,
            "data": data,
            "message": message,
        }
 
    @staticmethod
    async def ok(data: object = None, message: str = "Success") -> JSONResponse:
        return JSONResponse(
            status_code=200,
            content=HttpResponseMethod._build_content(True, data, message),
        )
 
    @staticmethod
    async def bad_request(data: object = None, message: str = "Bad Request") -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content=HttpResponseMethod._build_content(False, data, message),
        )

    @staticmethod
    async def not_found(data: object = None, message: str = "Not Found") -> JSONResponse:
        return JSONResponse(
            status_code=404,
            content=HttpResponseMethod._build_content(False, data, message),
        )

    @staticmethod
    async def internal_server_error(data: object = None, message: str = "Internal Server Error") -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=HttpResponseMethod._build_content(False, data, message),
        )

    @staticmethod
    async def server_error(e: Exception) -> JSONResponse:
        """
        D6：不把例外訊息回傳給客戶端。
        產生錯誤代碼並記錄完整例外，客戶端只會收到錯誤代碼，方便回報後追查。
        """
        error_id = uuid.uuid4().hex[:8]
        logger.error("Unhandled exception [error_id=%s]", error_id, exc_info=e)
        return await HttpResponseMethod.internal_server_error(
            data={"error_id": error_id},
            message="Internal Server Error",
        )