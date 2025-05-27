import os
from datetime import datetime
from collections import defaultdict

def generate_rental_id(item_id, user_id):
    date_str = datetime.now().strftime('%Y%m%d')
    return f"{item_id}_{user_id}_{date_str}"

def run_yolo_with_system(image_path, rental_id, folder_name):
    output_dir = f"results/{rental_id}/{folder_name}"
    os.makedirs(output_dir, exist_ok=True)

    # YOLOv5 모델 경로
    weights_path = r"C:\Users\user\Desktop\yolov5\yolov5\runs\train\my_yolo_model\weights\best.pt"

    # detect.py 실행d
    command = (
        f"python yolov5/detect.py "
        f"--weights \"{weights_path}\" "
        f"--source \"{image_path}\" "
        f"--conf 0.5 "
        f"--project results/{rental_id} "
        f"--name {folder_name} "
        f"--exist-ok "
        f"--save-txt"
    )
    os.system(command)

    # 클래스 이름 리스트 (data.yaml 기준 순서!)
    class_names = ['crack', 'scratch']  # ← 사용자의 클래스 순서에 맞게 수정

    label_txt_dir = f"results/{rental_id}/{folder_name}/labels"
    class_counts = defaultdict(int)

    if not os.path.exists(label_txt_dir):
        return {}

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

    before_counts = run_yolo_with_system(before_img, rental_id, '등록')
    after_counts = run_yolo_with_system(after_img, rental_id, '반납')

    print(f"[등록] 감지된 객체: {before_counts}")
    print(f"[반납] 감지된 객체: {after_counts}")

    # 파손 감지 여부 판단
    damage_detected = False
    increased_classes = {}

    all_classes = set(before_counts.keys()).union(set(after_counts.keys()))

    for cls in all_classes:
        before = before_counts.get(cls, 0)
        after = after_counts.get(cls, 0)
        if after > before:
            damage_detected = True
            increased_classes[cls] = after - before

    return rental_id, damage_detected, increased_classes

# ===== 테스트 실행 =====
item_id = 'item1'
user_id = 'user123'
before = 'before.jpg'
after = 'after.jpg'

rental_id, damaged, damage_info = is_item_damaged(item_id, user_id, before, after)

if damaged:
    print(f"[{rental_id}] 파손 감지: {damage_info}")
else:
    print(f"[{rental_id}] 파손 없음")
    print("AI 기능 테스트")
