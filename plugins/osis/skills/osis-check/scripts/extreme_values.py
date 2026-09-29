import argparse
from pathlib import Path
import pandas as pd
from pyosis import OSISEngine


def find_safety_factor_column(df: pd.DataFrame) -> str | None:
    return '安全系数' if '安全系数' in df.columns else None


def summarize_extreme_values(engine: OSISEngine, top_n: int) -> None:
    results = engine.result.check_all()
    records = []

    for name, df in results.items():
        sf_col = find_safety_factor_column(df)
        if sf_col is None:
            continue

        valid = df[df[sf_col] != 9999]
        if valid.empty:
            continue

        min_idx = valid[sf_col].idxmin()
        row = valid.loc[min_idx]
        pos_col = next((c for c in ['单元', '单元编号'] if c in df.columns), None)
        loc_col = '验算位置' if '验算位置' in df.columns else None

        if pos_col:
            pos_parts = [str(row[pos_col])]
            if loc_col and loc_col in df.columns:
                pos_parts.append(str(row[loc_col]))
            pos = '-'.join(pos_parts)
        else:
            pos = '-'

        records.append({
            '验算项': name.split('_', 2)[1] if '_' in name else name,
            '位置': pos,
            '结果': row.get('结果', '-'),
            '安全系数': float(row[sf_col]),
        })

    if not records:
        print('未找到安全系数数据')
        return

    summary = pd.DataFrame(records).sort_values('安全系数')
    summary['安全系数'] = summary['安全系数'].apply(lambda v: f'*{v:.4f}*' if v < 1 else f'{v:.4f}')

    print('## 各验算项极值汇总（按危险程度排序）')
    print(summary[['验算项', '位置', '结果', '安全系数']].head(top_n).to_string(index=False))


def summarize_by_unit(engine: OSISEngine, top_n: int) -> None:
    results = engine.result.check_all()
    unit_map: dict[int, list[tuple[str, float]]] = {}

    for name, df in results.items():
        pos_col = next((c for c in ['单元', '单元编号'] if c in df.columns), None)
        sf_col = find_safety_factor_column(df)
        if pos_col is None or sf_col is None:
            continue

        valid = df[df[sf_col] != 9999]
        if valid.empty:
            continue

        for uid, grp in valid.groupby(pos_col):
            min_sf = float(grp[sf_col].min())
            check_item = name.split('_', 2)[1] if '_' in name else name
            unit_map.setdefault(int(uid), []).append((check_item, min_sf))

    if not unit_map:
        print('未找到可汇总的单元安全系数数据')
        return

    rows = []
    for uid, items in unit_map.items():
        items.sort(key=lambda x: x[1])
        min_item, min_sf = items[0]
        rows.append({'单元': uid, '最不利验算': min_item, '最小安全系数': min_sf})

    summary = pd.DataFrame(rows).sort_values('最小安全系数')
    pd.options.display.float_format = '{:.4f}'.format
    print('## 单元级最不利安全系数汇总')
    print(summary.head(top_n).to_string(index=False))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='生成验算极值汇总报告')
    parser.add_argument('--top', type=int, default=20, help='输出前多少条最危险记录')
    parser.add_argument('--by-unit', action='store_true', help='按单元汇总最不利安全系数')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    engine = OSISEngine()

    if args.by_unit:
        summarize_by_unit(engine, args.top)
    else:
        summarize_extreme_values(engine, args.top)


if __name__ == '__main__':
    main()
