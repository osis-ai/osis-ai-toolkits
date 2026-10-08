import argparse
from pathlib import Path
from pyosis import OSISEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='详细分析单个 .lcc 验算项')
    parser.add_argument('target', help='.lcc 文件名（不含后缀），格式：sheetType_checkItem_checkName')
    parser.add_argument('--max-rows', type=int, default=30, help='输出 NG 详情时最大显示行数')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = OSISEngine()
    target = args.target
    proj_dir = Path(engine.project.get_directory())
    lcc_file = proj_dir / 'Check' / (target + '.lcc')
    if not lcc_file.exists():
        raise FileNotFoundError(f'文件不存在: {lcc_file}')

    parts = target.split('_', 2)
    if len(parts) != 3:
        raise ValueError(f'文件名格式不符: {target}')

    df = engine.result.check(*parts)
    print(f'## {target}')
    print(f'总行数: {len(df)}')
    print(f'列: {list(df.columns)}')
    if df.empty:
        print('\nEMPTY: 验算结果为 0 行，不能视为通过')
        return

    result_col = next((c for c in df.columns if str(c).strip() == '结果'), None)
    if result_col is None:
        raise ValueError('验算结果缺少「结果」列')
    ng_mask = df[result_col].astype(str).str.strip().str.contains('NG', na=False)
    if ng_mask.any():
        print(f'\n### NG 详情（共 {int(ng_mask.sum())} 条）:')
        print(df[ng_mask].to_string(max_rows=args.max_rows, index=False))
    else:
        print('\n全部通过')


if __name__ == '__main__':
    main()
