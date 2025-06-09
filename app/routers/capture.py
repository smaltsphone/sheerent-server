from fastapi import APIRouter, Response
import requests

router = APIRouter(prefix="/locker", tags=["locker"])

RASPBERRY_PI_URL = "http://192.168.137.187:8000"

@router.get("/capture")
def capture():
    try:
        raspberry_response = requests.get(f"{RASPBERRY_PI_URL}/shoot")
        if raspberry_response.status_code == 200:
            return Response(content=raspberry_response.content, media_type="image/jpeg")
        else:
            return {"error": f"라즈베리파이 응답 오류: {raspberry_response.status_code}"}
    except Exception as e:
        return {"error": f"라즈베리파이 연결 실패: {str(e)}"}

@router.post("/open")
def open_door():
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/open")
        if response.status_code == 200:
            return {"message": "문이 열렸습니다."}
        else:
            return {"error": f"문 열기 실패: {response.status_code}"}
    except Exception as e:
        return {"error": f"연결 실패: {str(e)}"}

@router.post("/close")
def close_door():
    try:
        response = requests.post(f"{RASPBERRY_PI_URL}/close")
        if response.status_code == 200:
            return {"message": "문이 닫혔습니다."}
        else:
            return {"error": f"문 닫기 실패: {response.status_code}"}
    except Exception as e:
        return {"error": f"연결 실패: {str(e)}"}
