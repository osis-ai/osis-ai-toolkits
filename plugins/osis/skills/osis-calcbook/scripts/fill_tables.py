import json
import re
import os
import sys

def json_to_markdown_table(json_data):
    """将JSON数据(header+data)转换为Markdown表格"""
    if not json_data or "header" not in json_data or "data" not in json_data:
        return ""
    header = json_data["header"]
    data = json_data["data"]
    
    lines = []
    lines.append("| " + " | ".join(str(h) for h in header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for row in data:
        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
    
    return "\n".join(lines)

def main():
    if len(sys.argv) < 3:
        print("Usage: python fill_tables.py <input.md> <output.md>")
        print("Example: python fill_tables.py 计算书模板.md 计算书.md")
        sys.exit(1)
    
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    base_dir = os.path.dirname(os.path.abspath(input_path))
    
    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 正则匹配所有 | {{TABLE:path}} | 占位符（包含外层的 | ）
    pattern = re.compile(r"\| \{\{TABLE:([^}]+)\}\} \|")
    
    while True:
        match = pattern.search(content)
        if not match:
            break
        
        json_path = match.group(1)
        full_path = os.path.join(base_dir, json_path)
        
        if os.path.exists(full_path):
            with open(full_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
            table_md = json_to_markdown_table(json_data)
        else:
            table_md = "(数据文件不存在: {})".format(json_path)
        
        content = content[:match.start()] + table_md + content[match.end():]
    
    # 清理多余空行
    content = re.sub(r"\n{3,}", "\n\n", content)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)
    
    remaining = content.count("{{TABLE:")
    print(f"输出文件: {output_path}")
    print(f"剩余表格占位符: {remaining}")
    print("表格填充完成！")

if __name__ == "__main__":
    main()
