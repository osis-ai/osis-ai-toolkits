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
    ng_cols = [col for col in df.columns if df[col].astype(str).str.contains('NG', na=False).any()]

    print(f'## {target}')
    print(f'总行数: {len(df)}')
    print(f'列: {list(df.columns)}')
    print(f'含 NG 的列: {ng_cols}')

    if ng_cols:
        print('\n### NG 详情:')
        for col in ng_cols:
            ng_mask = df[col].astype(str).str.contains('NG', na=False)
            print(f'\n--- {col} (共 {ng_mask.sum()} 条) ---')
            ng_df = df[ng_mask]
            print(ng_df.to_string(max_rows=args.max_rows, index=False))
    else:
        print('\n全部通过')


if __name__ == '__main__':
    main()
