"""Reuse the sealed private 2022 source cut for the SDK stock-Gradle policy check."""
import argparse
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);result=importlib.util.module_from_spec(spec);spec.loader.exec_module(result);return result
def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('operation',choices=['seal','sdk','boundary']);parser.add_argument('--tag',required=True);parser.add_argument('--manifest',required=True);args=parser.parse_args()
 if args.operation=='boundary':
  runner=module('ads126_stockpolicy',ROOT/'Verification/Tools/Review126/run_advertising126.py');runner.OUT=ROOT/'Verification/Evidence/Review126/Toolchain';return runner.run('boundary',args.tag,args.manifest)
 runner=module('native125_stockpolicy',ROOT/'Verification/Tools/Review125/native_client125.py');runner.OUT=ROOT/'Verification/Evidence/Review126/Toolchain'
 if args.operation=='seal':runner.rebase(args.tag,args.manifest);return 0
 return runner.run('sdk',args.tag,args.manifest)
if __name__=='__main__':raise SystemExit(main())
