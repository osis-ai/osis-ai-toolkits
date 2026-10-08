from pathlib import Path
from pyosis import OSISEngine


def count_results(df) -> tuple[int, int]:
    result_col = next((c for c in df.columns if str(c).strip() == '结果'), None)
    if result_col is None:
        raise ValueError('验算结果缺少「结果」列')
    values = df[result_col].astype(str).str.strip()
    ok = int(values.str.contains('OK', na=False).sum())
    ng = int(values.str.contains('NG', na=False).sum())
    return ok, ng


def main() -> None:
    engine = OSISEngine()
    results = engine.result.check_all()

    ng_total = 0
    ok_total = 0
    for name, df in results.items():
        ok, ng = count_results(df)
        ng_total += ng
        ok_total += ok
        status = 'EMPTY' if len(df) == 0 else ('NG' if ng else 'OK')
        print(f'{name}: {status}  ({len(df)} 项, OK={ok}, NG={ng})')

    print('\n总计: OK={ok_total}, NG={ng_total}'.format(ok_total=ok_total, ng_total=ng_total))


if __name__ == '__main__':
    main()
