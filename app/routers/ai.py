import sys
sys.path.append(r"C:\Users\user\Desktop\yolov5\yolov5")  # YOLOv5 소스코드 폴더 경로

import os
import torch
from datetime import datetime
from collections import defaultdict
from fastapi import APIRouter, UploadFile, File
from PIL import Image

router = APIRouter()

# 현재 파일의 경로를 기준으로 상대 경로 설정
base_dir = os.path.dirname(__file__)
yolo_dir = os.path.abspath(os.path.join(base_dir, "../yolov5"))
weights_path = os.path.abspath(os.path.join(base_dir, "../../yolov5/yolov5/runs/train/my_yolo_model/weights/best.pt"))
detect_py_path = os.path.abspath(os.path.join(base_dir, "../../yolov5/yolov5/detect.py"))

# YOLOv5 모델 로드
model_data = torch.load(weights_path, map_location='cuda' if torch.cuda.is_available() else 'cpu', weights_only=False)
model = model_data['model'].float().fuse().eval()

# 클래스 이름 리스트 (data.yaml 기준 순서에 따라 맞춰야 함)
class_names = ['crack', 'scratch']

def generate_rental_id(item_id, user_id):
    date_str = datetime.now().strftime('%Y%m%d')
    return f"{item_id}_{user_id}_{date_str}"

def run_yolo_with_system(image_path, rental_id, folder_name):
    output_dir = f"results/{rental_id}/{folder_name}"
    os.makedirs(output_dir, exist_ok=True)

    # detect.py 명령어 구성
    command = (
        f"python \"{detect_py_path}\" "
        f"--weights \"{weights_path}\" "
        f"--source \"{image_path}\" "
        f"--conf 0.5 "
        f"--project results/{rental_id} "
        f"--name {folder_name} "
        f"--exist-ok "
        f"--save-txt"
    )

    # 실행
    return_code = os.system(command)
    print(f"Command executed: {command}")
    print(f"Return code: {return_code}")
    if return_code != 0:
        print(f"Error occurred during detection. Command return code: {return_code}")
    else:
        print(f"Detection completed successfully for {image_path}")

    label_txt_dir = f"results/{rental_id}/{folder_name}/labels"
    class_counts = defaultdict(int)

    if os.path.exists(label_txt_dir):
        # detect.py는 원본 이미지가 'source'에 들어간 이름이랑 같은 이름으로 라벨 만듦
        # image_path가 파일이면 파일 이름을 뽑아서 사용
        img_name = os.path.splitext(os.path.basename(image_path))[0]

        txt_path = os.path.join(label_txt_dir, f"{img_name}.txt")
        if not os.path.exists(txt_path):
            # 빈 파일 생성
            open(txt_path, 'w').close()
    else:
        # 라벨 디렉토리 자체가 없으면 새로 만들어서 빈 파일이라도 만들어두기
        os.makedirs(label_txt_dir, exist_ok=True)
        img_name = os.path.splitext(os.path.basename(image_path))[0]
        txt_path = os.path.join(label_txt_dir, f"{img_name}.txt")
        open(txt_path, 'w').close()

    for label_file in os.listdir(label_txt_dir):
        file_path = os.path.join(label_txt_dir, label_file)
        with open(file_path, 'r') as f:
            for line in f:
                cls_id = int(line.split()[0])  # 첫 번째 값은 클래스 ID
                class_name = class_names[cls_id] if cls_id < len(class_names) else f"class_{cls_id}"
                class_counts[class_name] += 1

    return dict(class_counts)

def is_item_damaged(item_id, user_id, before_img, after_img):
    rental_id = generate_rental_id(item_id, user_id)

    before_counts = run_yolo_with_system(before_img, rental_id, 'before')  # 등록 이미지 분석
    after_counts = run_yolo_with_system(after_img, rental_id, 'after')   # 반납 이미지 분석

    print("Before counts:", before_counts)
    print("After counts:", after_counts)


    damage_detected = False
    increased_classes = {}

    all_classes = set(before_counts.keys()).union(set(after_counts.keys()))

    for cls in all_classes:
        before = before_counts.get(cls, 0)
        after = after_counts.get(cls, 0)
        if after > before:  # 파손이 발생했을 경우
            damage_detected = True
            increased_classes[cls] = after - before

    return rental_id, damage_detected, increased_classes


def return_rental(item_id, rental_id):
    # item_id와 rental_id에 해당하는 'before'와 'after' 이미지를 가져옵니다.
    before_img = get_image(item_id, rental_id, "before")  # 'before' 이미지 가져오기
    after_img = get_image(item_id, rental_id, "after")    # 'after' 이미지 가져오기

    # is_item_damaged 함수 호출
    rental_key, damage_detected, damage_info = is_item_damaged(item_id, rental_id, before_img, after_img)

    # damage_detected, damage_info 등을 활용한 후속 처리
    if damage_detected:
        print(f"Damage detected in rental {rental_key}. Damage details: {damage_info}")
    else:
        print(f"No damage detected in rental {rental_key}.")



def get_image(item_id, user_id, img_type):
    """
    이미지를 가져오는 함수
    :param item_id: 아이템 ID
    :param user_id: 사용자 ID
    :param img_type: 이미지 유형 ('before' 또는 'after')
    :return: 이미지 파일 경로
    """
    # 기본 경로 설정 (아이템 ID와 사용자 ID로 경로 생성)
    base_path = os.path.join("images", str(item_id), str(user_id))

    # 이미지 파일 경로 (before 또는 after에 해당하는 파일)
    image_path = os.path.join(base_path, f"{img_type}_image.jpg")

    # 파일이 존재하는지 확인
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"{img_type.capitalize()} image not found for item {item_id} and user {user_id}.")

    return image_path


@router.post("/check_damage/")
async def check_damage(
    item_id: str = File(...),
    user_id: str = File(...),
    before_file: UploadFile = File(...),
    after_file: UploadFile = File(...),
):
    # 업로드된 파일 저장
    os.makedirs("temp", exist_ok=True)
    before_file_path = f"temp/{before_file.filename}"
    after_file_path = f"temp/{after_file.filename}"

    with open(before_file_path, "wb") as f:
        f.write(await before_file.read())

    with open(after_file_path, "wb") as f:
        f.write(await after_file.read())

    # 파손 판단
    rental_id, damaged, damage_info = is_item_damaged(item_id, user_id, before_file_path, after_file_path)

    # 임시 파일 삭제
    os.remove(before_file_path)
    os.remove(after_file_path)

    if damaged:
        return {
            "rental_id": rental_id,
            "damage_detected": True,
            "damage_info": damage_info
        }
    else:
        return {
            "rental_id": rental_id,
            "damage_detected": False
        }
