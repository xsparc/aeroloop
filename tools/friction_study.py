"""Verify raw contact captures and export a portable physics review bundle."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from aeroloop.friction_study import export
from aeroloop.simulation import encoded

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sessions',type=Path,nargs='+',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    try:
        print(encoded(export(args.sessions,args.output)).decode(),end='')
    except (OSError,ValueError,TypeError,KeyError):
        print('Contact evidence is incomplete or invalid; no verified bundle available.',file=sys.stderr)
        return 1
    return 0
if __name__=='__main__':
    raise SystemExit(main())
