from pathlib import Path
from pyosis import OSISEngine


def main() -> None:
    engine = OSISEngine()
    results = engine.result.check_all()

    ng_total = 0
    ok_total = 0
    for name, df in results.items():
        ng = sum(1 for row in df.itertuples(index=False) for v in row if 'NG' in str(v))
        ok = len(df) - ng
        ng_total += ng
        ok_total += ok
        status = 'NG' if ng else 'OK'
        print(f'{name}: {status}  ({len(df)} 项, OK={ok}, NG={ng})')

    print('\n总计: OK={ok_total}, NG={ng_total}'.format(ok_total=ok_total, ng_total=ng_total))


if __name__ == '__main__':
    main()
