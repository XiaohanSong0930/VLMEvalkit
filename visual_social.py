import os, cv2
import string
import os.path as osp
import numpy as np
from collections import defaultdict
import pandas as pd
import matplotlib.pyplot as plt
import multiprocessing as mp
from PIL import Image, ImageFont, ImageDraw
import json
import base64
from uuid import uuid4
import hashlib
from pathlib import Path
import re


def encode_image_to_base64(img, target_size=-1):
    if img.mode in ('RGBA', 'P'):
        img = img.convert('RGB')
    tmp = osp.join('/tmp', str(uuid4()) + '.jpg')
    if target_size > 0:
        img.thumbnail((target_size, target_size))
    img.save(tmp)
    with open(tmp, 'rb') as image_file:
        image_data = image_file.read()
    ret = base64.b64encode(image_data).decode('utf-8')
    os.remove(tmp)
    return ret

def encode_image_file_to_base64(image_path, target_size=-1):
    image = Image.open(image_path)
    return encode_image_to_base64(image, target_size=target_size)

def md5(s):
    hash = hashlib.new('md5')
    if osp.exists(s):
        with open(s, 'rb') as f:
            for chunk in iter(lambda: f.read(2**20), b''):
                hash.update(chunk)
    else:
        hash.update(s.encode('utf-8'))
    return str(hash.hexdigest())

def encode_images(image_list, image_folder):
    base64_images = []
    for image_name in image_list:
        image_name = Path(image_name).name
        image_path = os.path.join(image_folder, image_name)
        if os.path.exists(image_path):
            with open(image_path, "rb") as img_file:
                base64_images.append(base64.b64encode(img_file.read()).decode("utf-8"))
        else:
            print(f"Warning: {image_path} not found.")
    return ";".join(base64_images)

def _norm_text(s: str) -> str:
    if s is None:
        return ""
    s = s.strip()
    s = re.sub(r'[\s\.\!\?;:]+$', '', s)
    s = re.sub(r'\s+', ' ', s)
    return s.lower()

def get_answer_letter_from_item(item: dict) -> str:
    ans = str(item.get("answer", "")).strip()

    m = re.match(r'^\s*([ABCD])\s*[\)\.\:：]?\s*$', ans, re.I)
    if m:
        return m.group(1).upper()

    options = {k: str(item.get(k, "")).strip() for k in ["A", "B", "C", "D"] if k in item}
    norm_ans = _norm_text(ans)

    for k, v in options.items():
        if _norm_text(v) == norm_ans:
            return k

    for k, v in options.items():
        if norm_ans and _norm_text(v).startswith(norm_ans):
            return k

    print(f"Warning: cannot match answer '{ans}' to options {options}")
    return ""


def process_json_to_tsv(json_file, image_folder, output_tsv):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    rows = []
    index = 0
    
    for item in data:
        answer_letter = get_answer_letter_from_item(item)

        messages = item.get("messages", [])
        for message in messages:
            content = message.get("content", [])
            images = []
            question = ""

            for entry in content:
                if entry.get("type") == "image":
                    images.append(entry.get("image", ""))
                elif entry.get("type") == "text":
                    if not question:
                        question = entry.get("text", "")

            encoded_images = encode_images(images, image_folder)
            rows.append([index, encoded_images, question, answer_letter])
            index += 1

    df = pd.DataFrame(rows, columns=["index", "image", "question", "answer"])
    df.to_csv(output_tsv, sep="\t", index=False, encoding="utf-8")
    print(f"TSV file saved to {output_tsv}")


json_file = ""  
image_folder = ""  
output_tsv = "visual_social_grouped.tsv"  

process_json_to_tsv(json_file, image_folder, output_tsv)
