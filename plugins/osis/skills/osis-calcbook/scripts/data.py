# from pyosis.common import output_result_for_calc_book, get_project_directory
#
# output_result_for_calc_book()
#
# project_dir = get_project_directory()

import argparse
import os
import json
import pandas as pd

from pyosis.general import output_result_for_calc_book
from pyosis.project import get_project_directory

try:
    from pyosis.general import output_result_for_calc_book
    from pyosis.project import get_project_directory
    project_dir = get_project_directory()
    print(f"Project Directory: {project_dir}")
    print(output_result_for_calc_book())
except Exception as e:
    project_dir = "./"      # 没找到就先用当前目录
    print(f"Error occurred: {e}")




def parse_value_file(file_path):
    """解析 Temperary 目录下的键值对 txt 文件，返回 {key: value} 字典"""
    result = {}
    if not os.path.exists(file_path):
        return result
    with open(file_path, "r", encoding="gbk", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 2:
                key = parts[0].strip()
                # 优先尝试第 2 列（科学计数法数值），失败再尝试第 3 列
                candidates = [parts[1].strip()]
                if len(parts) >= 3:
                    candidates.append(parts[2].strip())
                for val_str in candidates:
                    if not val_str:
                        continue
                    try:
                        if "." in val_str or "e" in val_str.lower():
                            value = float(val_str)
                            if value == int(value):
                                value = int(value)
                        else:
                            value = int(val_str)
                        result[key] = value
                        break
                    except ValueError:
                        continue
    return result


def flat_list_to_table(json_path, col_count):
    """将扁平列表的 JSON 文件转换为 docx_tool.py 要求的表格字典格式"""
    with open(json_path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    header = data[:col_count]
    body = data[col_count:]
    rows = []
    for i in range(0, len(body), col_count):
        row = body[i : i + col_count]
        rows.append(row)
    return {"header": header, "data": rows}


def format_version(version):
    """将数字版本号格式化为 x.yy.zz 字符串"""
    s = str(int(version)).zfill(5)
    return f"{s[0]}.{s[1:3]}.{s[3:5]}"


def write_table_json(src_path, col_count, dest_path, project_dir):
    """如果源 JSON 存在则生成表格 JSON 并返回相对路径，否则返回 None"""
    if not os.path.exists(src_path):
        return None
    table = flat_list_to_table(src_path, col_count)
    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=4)
    return os.path.relpath(dest_path, project_dir).replace("\\", "/")


def build_project_data(project_dir):
    """根据项目目录下的 Temperary、Check、image 数据构建结构化字典。"""
    # ---------- 1. 读取基本信息 ----------
    node_info = parse_value_file(
        os.path.join(project_dir, "Temperary", "DATA_NodeNum.txt")
    )
    elem_info = parse_value_file(
        os.path.join(project_dir, "Temperary", "DATA_ElemNum.txt")
    )
    bc_info = parse_value_file(os.path.join(project_dir, "Temperary", "DATA_BCNum.txt"))
    # 施工阶段数量从 tCsChar.json 的实际数据行数统计（tCsSize 含内部隐藏步，不可靠）
    cs_char_path = os.path.join(project_dir, "Temperary", "tCsChar.json")
    cs_char_cols = 4
    if os.path.exists(cs_char_path):
        with open(cs_char_path, "r", encoding="utf-8-sig") as f:
            cs_char_data = json.load(f)
        cs_stage_count = (len(cs_char_data) - cs_char_cols) // cs_char_cols
    else:
        cs_stage_count = 0

    version_path = os.path.join(project_dir, "Temperary", "VersionNO.json")
    if os.path.exists(version_path):
        with open(version_path, "r", encoding="utf-8-sig") as f:
            version_raw = json.load(f)[0]
        version_str = format_version(version_raw)
    else:
        version_str = "0.00.00"

    basic_info = {
        "节点数量": int(node_info.get("DATA_NodeNum", 0)),
        "单元数量": int(elem_info.get("DATA_ElemNum", 0)),
        "边界条件数量": int(bc_info.get("DATA_BCNum", 0)),
        "施工阶段数量": cs_stage_count,
        "版本号": version_str,
    }

    # ---------- 2. 自重系数 ----------
    dw_info = parse_value_file(
        os.path.join(project_dir, "Temperary", "Coeff_DeadWeight.txt")
    )
    dead_weight_coeff = float(dw_info.get("Coeff_DeadWeight", 0.0))

    # ---------- 3. 生成 material.json / boundary.json / stage.json / pt_char.json / td_prop.json / tendon_coord.json / creep.json / reaction.json 到 json 目录 ----------
    temp_dir = os.path.join(project_dir, "Temperary")
    json_dir = os.path.join(project_dir, "json")
    os.makedirs(json_dir, exist_ok=True)
    material_json = write_table_json(
        os.path.join(temp_dir, "tMatChar.json"),
        6,
        os.path.join(json_dir, "material.json"),
        project_dir,
    )
    boundary_json = write_table_json(
        os.path.join(temp_dir, "tBdChar.json"),
        9,
        os.path.join(json_dir, "boundary.json"),
        project_dir,
    )
    stage_json = write_table_json(
        os.path.join(temp_dir, "tCsChar.json"),
        4,
        os.path.join(json_dir, "stage.json"),
        project_dir,
    )
    pt_char_json = write_table_json(
        os.path.join(temp_dir, "tPTChar.json"),
        6,
        os.path.join(json_dir, "pt_char.json"),
        project_dir,
    )
    td_prop_json = write_table_json(
        os.path.join(temp_dir, "tTDPChar.json"),
        11,
        os.path.join(json_dir, "td_prop.json"),
        project_dir,
    )
    tendon_coord_json = write_table_json(
        os.path.join(temp_dir, "tTdChar.json"),
        7,
        os.path.join(json_dir, "tendon_coord.json"),
        project_dir,
    )
    creep_json = write_table_json(
        os.path.join(temp_dir, "tCreepChar.json"),
        6,
        os.path.join(json_dir, "creep.json"),
        project_dir,
    )
    reaction_json = write_table_json(
        os.path.join(temp_dir, "strReaction.json"),
        5,
        os.path.join(json_dir, "reaction.json"),
        project_dir,
    )

    # ---------- 4. 整合 check_tool.py：处理 Check 目录 ----------
    check_dir = os.path.join(project_dir, "Check")
    txt_files = []
    if os.path.isdir(check_dir):
        txt_files = [f for f in os.listdir(check_dir) if f.lower().endswith(".txt")]

    check_results = {}

    for file in txt_files:
        file_path = os.path.join(check_dir, file)
        df = pd.read_csv(
            file_path,
            sep=r"\s+",
            header=2,
            encoding="gbk",
            on_bad_lines="skip",
        )
        file_name = os.path.splitext(file)[0]
        
        # ---------- 将完整 DataFrame 导出为 JSON 表格到 json 目录 ----------
        def convert_numpy(obj):
            import numpy as np
            if isinstance(obj, np.generic):
                return obj.item()
            return obj

        table_data = {
            "header": df.columns.tolist(),
            "data": [[convert_numpy(v) for v in row] for row in df.values.tolist()],
        }
        check_json_path = os.path.join(json_dir, f"{file_name}.json")
        with open(check_json_path, "w", encoding="utf-8") as f:
            json.dump(table_data, f, ensure_ascii=False, indent=4)
        json_rel_path = os.path.relpath(check_json_path, project_dir).replace("\\", "/")
        
        entry = {"path": json_rel_path}

        has_ng = "NG" in df["结果"].values if "结果" in df.columns else True

        if "抗弯" in file_name:
            entry["最小弯矩"] = df["γMd"].min().item() / 1000.0
            entry["最大弯矩"] = df["γMd"].max().item() / 1000.0
            entry["满足规范"] = not has_ng
        elif "抗剪" in file_name:
            entry["最小剪力"] = df["γVd"].min().item() / 1000.0
            entry["最大剪力"] = df["γVd"].max().item() / 1000.0
            entry["满足规范"] = not has_ng
        elif "抗裂" in file_name:
            entry["最不利应力"] = df["SigMax"].max().item() / 1000000.0
            entry["满足规范"] = not has_ng
        elif "压应力" in file_name:
            entry["最大压应力"] = df["SigMax"].min().item() / 1000000.0
            entry["满足规范"] = not has_ng
        elif "拉应力" in file_name:
            entry["最大拉应力"] = df["SigMax"].max().item() / 1000000.0
            entry["满足规范"] = not has_ng

        check_results[file_name] = entry

    # 按目标 JSON 中的固定顺序输出（若存在）
    check_order = [
        "斜截面主压应力验算",
        "斜截面抗剪承载能力验算",
        "斜截面频遇组合抗裂验算",
        "施工阶段压应力验算",
        "施工阶段拉应力验算",
        "正截面准永久组合抗裂验算",
        "正截面压应力验算",
        "正截面抗弯承载能力验算",
        "正截面频遇组合抗裂验算",
    ]
    check_results = {k: check_results[k] for k in check_order if k in check_results}

    # ---------- 5. 处理 image 目录 ----------
    image_dir = os.path.join(project_dir, "image")
    img_files = []
    if os.path.isdir(image_dir):
        img_files = [
            f
            for f in os.listdir(image_dir)
            if f.lower().endswith((".jpg", ".jpeg", ".png", ".bmp"))
        ]

    IMG_NAME_MAP = {
        "IMG_Structure.jpg": "计算模型图",
        "IMG_Tendon.jpg": "预应力钢束布置图",
        "IMG_MomentCapacityMax.jpg": "UxMax下正截面抗弯承载能力包络图",
        "IMG_MomentCapacityMin.jpg": "UxMin下正截面抗弯承载能力包络图",
        "IMG_ShearCapacityMax.jpg": "UzMax下斜截面抗剪承载能力包络图",
        "IMG_ShearCapacityMin.jpg": "UzMin下斜截面抗剪承载能力包络图",
    }

    LC_MOMENT_MAP = {
        "DeadLoad": "恒载",
        "VehicleLoad": "汽车荷载",
        "CharacteristicComb": "标准组合",
        "FrequentComb": "频遇组合",
        "QuasiPermanentComb": "准永久组合",
        "FundamentalComb": "基本组合",
        "CreepSecondary": "徐变二次",
        "ShrinkageSecondary": "收缩二次",
        "TendonSecondary": "钢束二次",
        "UniformNegative": "整体降温",
        "UniformPositive": "整体升温",
        "GradientNegative": "梯度降温",
        "GradientPositive": "梯度升温",
    }

    CHECK_IMG_MAP = {
        "正截面频遇组合抗裂验算": "正截面在作用频遇组合下抗裂验算结果",
        "正截面准永久组合抗裂验算": "正截面在作用准永久组合下抗裂验算结果",
        "斜截面频遇组合抗裂验算": "斜截面在作用频遇组合下抗裂验算结果",
        "正截面压应力验算": "正截面混凝土压应力验算结果",
        "斜截面主压应力验算": "斜截面混凝土主压应力验算结果",
        "施工阶段压应力验算": "施工阶段混凝土压应力验算结果",
        "施工阶段拉应力验算": "施工阶段混凝土拉应力验算结果",
    }

    def get_image_key(filename):
        if filename in IMG_NAME_MAP:
            return IMG_NAME_MAP[filename]
        if filename.startswith("IMG_") and filename.lower().endswith(".jpg"):
            inner = filename[4:-4]
            if inner.startswith("LcMoment_"):
                suffix = inner[9:]
                return f"{LC_MOMENT_MAP.get(suffix, suffix)}内力图My"
            if inner in CHECK_IMG_MAP:
                return CHECK_IMG_MAP[inner]
            return inner
        return filename

    image_files = {}
    for f in img_files:
        key = get_image_key(f)
        image_files[key] = "image/" + f

    # 按目标 JSON 中的固定顺序输出（与计算书案例.docx 中图片出现顺序一致）
    img_order = [
        "计算模型图",
        "预应力钢束布置图",
        "恒载内力图My",
        "钢束二次内力图My",
        "收缩二次内力图My",
        "徐变二次内力图My",
        "整体降温内力图My",
        "整体升温内力图My",
        "梯度降温内力图My",
        "梯度升温内力图My",
        "汽车荷载内力图My",
        "基本组合内力图My",
        "标准组合内力图My",
        "频遇组合内力图My",
        "准永久组合内力图My",
        "UxMin下正截面抗弯承载能力包络图",
        "UxMax下正截面抗弯承载能力包络图",
        "UzMin下斜截面抗剪承载能力包络图",
        "UzMax下斜截面抗剪承载能力包络图",
        "正截面在作用频遇组合下抗裂验算结果",
        "正截面在作用准永久组合下抗裂验算结果",
        "斜截面在作用频遇组合下抗裂验算结果",
        "正截面混凝土压应力验算结果",
        "斜截面混凝土主压应力验算结果",
        "施工阶段混凝土压应力验算结果",
        "施工阶段混凝土拉应力验算结果",
    ]
    image_files = {k: image_files[k] for k in img_order if k in image_files}

    # ---------- 6. 组装并返回 ----------
    project_data = {
        "基本信息": basic_info,
        "自重系数": dead_weight_coeff,
        "材料参数": material_json,
        "边界条件": boundary_json,
        "施工阶段": stage_json,
        "钢束属性": td_prop_json,
        "钢束坐标": tendon_coord_json,
        "梯度温度": pt_char_json,
        "收缩徐变": creep_json,
        "支座反力": reaction_json,
        "验算表格": check_results,
        "图片文件": image_files,
    }

    return project_data


def main():
    parser = argparse.ArgumentParser(
        description="将项目输出结果（Temperary、Check、image）结构化为 JSON。"
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        default="项目数据结构.json",
        help="输出 JSON 文件路径（默认：项目数据结构.json）",
    )
    args = parser.parse_args()

    data = build_project_data(project_dir)
    output_path = args.output
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"项目数据结构已生成: {output_path}")


if __name__ == "__main__":
    main()
