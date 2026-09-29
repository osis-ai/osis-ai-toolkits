import argparse
from pathlib import Path
from pyosis import OSISEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='按 .lcc 文件名或模式加载 OSIS 验算结果')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--file', help='单个 .lcc 文件名（不含后缀）')
    group.add_argument('--pattern', help='glob 模式，自动添加 .lcc 后缀，例如 "*.lcc" 或 "混凝土_*.lcc"')
    group.add_argument('--list', action='store_true', help='列出 Check 目录下所有 .lcc 文件')
    return parser.parse_args()


def load_single(engine: OSISEngine, target: str) -> None:
    proj_dir = Path(engine.project.get_directory())
    lcc_path = proj_dir / 'Check' / (target + '.lcc')
    if not lcc_path.exists():
        raise FileNotFoundError(f'文件不存在: {lcc_path}')

    parts = target.split('_', 2)
    if len(parts) != 3:
        raise ValueError('文件名格式不符，需为 sheetType_checkItem_checkName')

    df = engine.result.check(*parts)
    ng = sum(1 for row in df.itertuples(index=False) for v in row if 'NG' in str(v))
    print(f'{target}: OK={len(df)-ng}, NG={ng}, 总行数={len(df)}')
    print(df.to_string(max_rows=50, index=False))


def load_pattern(engine: OSISEngine, pattern: str) -> None:
    proj_dir = Path(engine.project.get_directory())
    check_dir = proj_dir / 'Check'
    if not pattern.endswith('.lcc'):
        pattern += '.lcc'

    lcc_files = sorted(check_dir.glob(pattern))
    if not lcc_files:
        print(f'无匹配 {pattern} 的 .lcc 文件')
        return

    for f in lcc_files:
        parts = f.stem.split('_', 2)
        if len(parts) != 3:
            print(f'跳过不符合命名规则的文件: {f.name}')
            continue
        try:
            df = engine.result.check(*parts)
            ng = sum(1 for row in df.itertuples(index=False) for v in row if 'NG' in str(v))
            status = 'NG' if ng else 'OK'
            print(f'[{status}] {f.stem}: OK={len(df)-ng}, NG={ng}')
        except Exception as exc:
            print(f'[ERR] {f.stem}: {exc}')


def list_files(engine: OSISEngine) -> None:
    proj_dir = Path(engine.project.get_directory())
    check_dir = proj_dir / 'Check'
    if not check_dir.exists():
        raise FileNotFoundError('Check 目录不存在，请先执行验算')

    files = sorted(check_dir.glob('*.lcc'))
    print(f'共 {len(files)} 个 .lcc 文件:')
    for f in files:
        print(f'  {f.stem}')


def main() -> None:
    args = parse_args()
    engine = OSISEngine()

    if args.list:
        list_files(engine)
    elif args.file:
        load_single(engine, args.file)
    elif args.pattern:
        load_pattern(engine, args.pattern)


if __name__ == '__main__':
    main()
