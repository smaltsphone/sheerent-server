from fastapi import APIRouter, Response
import requests

router = APIRouter()

RASPBERRY_PI_SHOOT_URL = "http://192.168.137.187:8000/shoot"

@router.get("/capture")
def capture():
    try:
        raspberry_response = requests.get(RASPBERRY_PI_SHOOT_URL)
        if raspberry_response.status_code == 200:
            return Response(content=raspberry_response.content, media_type="image/jpeg")
        else:
            return {"error": f"라즈베리파이 응답 오류: {raspberry_response.status_code}"}
    except Exception as e:
        return {"error": f"라즈베리파이 연결 실패: {str(e)}"}
