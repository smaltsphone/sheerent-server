import sys
sys.path.append(r"C:\Users\radpion\Desktop\yolov5\yolov5")  # YOLOv5 소스코드 경로

from fastapi import APIRouter, UploadFile, File
import os
import uuid
from collections import defaultdict
import torch

router = APIRouter()

# YOLOv5 모델 경로
weights_path = r"C:\Users\radpion\Desktop\yolov5\yolov5\runs\train\my_yolo_model\weights\best.pt"
model_data = torch.load(weights_path, map_location='cpu', weights_only=False)
model = model_data['model'].float().fuse().eval()

# 클래스 이름 (data.yaml 기준)
class_names = ['crack', 'scratch']

# YOLO 분석 함수 (폴더 단위)
def run_yolo_with_folder(folder_path):
    temp_id = uuid.uuid4().hex
    output_dir = f"results/{temp_id}"
    os.makedirs(output_dir, exist_ok=True)

    command = (
        f"python \"C:/Users/radpion/Desktop/yolov5/yolov5/detect.py\" "
        f"--weights \"{weights_path}\" "
        f"--source \"{folder_path}\" "
        f"--conf 0.5 "
        f"--project {output_dir} "
        f"--name results "
        f"--exist-ok "
        f"--save-txt"
    )
    os.system(command)

    label_txt_dir = os.path.join(output_dir, "results", "labels")
    class_counts = defaultdict(int)

    if not os.path.exists(label_txt_dir):
        return {}

    for label_file in os.listdir(label_txt_dir):
        file_path = os.path.join(label_txt_dir, label_file)
        with open(file_path, 'r') as f:
            for line in f:
                cls_id = int(line.split()[0])
                class_name = class_names[cls_id] if cls_id < len(class_names) else f"class_{cls_id}"
                class_counts[class_name] += 1

    return dict(class_counts)

# 파손 판단 로직
def is_item_damaged(item_id, rental_id):
    before_folder = f"images/before/item_{item_id}"
    after_folder = f"images/after/rental_{rental_id}"

    before_counts = run_yolo_with_folder(before_folder)
    after_counts = run_yolo_with_folder(after_folder)

    damage_detected = False
    increased_classes = {}

    all_classes = set(before_counts.keys()).union(set(after_counts.keys()))
    for cls in all_classes:
        before = before_counts.get(cls, 0)
        after = after_counts.get(cls, 0)
        if after > before:
            damage_detected = True
            increased_classes[cls] = after - before

    return f"{item_id}_{rental_id}", damage_detected, increased_classes

# API 엔드포인트
@router.post("/check_damage/")
async def check_damage(
    item_id: str,
    rental_id: str,
    after_file: UploadFile = File(...)
):
    after_dir = f"images/after/rental_{rental_id}"
    os.makedirs(after_dir, exist_ok=True)
    after_file_path = os.path.join(after_dir, "after.jpg")

    with open(after_file_path, "wb") as f:
        f.write(await after_file.read())

    rental_key, damaged, damage_info = is_item_damaged(item_id, rental_id)

    if damaged:
        return {
            "rental_id": rental_key,
            "damage_detected": True,
            "damage_info": damage_info
        }
    else:
        return {
            "rental_id": rental_key,
            "damage_detected": False
        }
