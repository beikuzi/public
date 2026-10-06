#!/usr/bin/env python3
"""Acquire the official free demo, verify exact bytes, and extract; never run it."""
import argparse,hashlib,tarfile,urllib.request
from pathlib import Path
URL='https://cdn.fhs.sh/ks/bin/a1v5/%5B4ls%5D_katawa_shoujo_act1_v5_%5Blinux-x86%5D%5B97624142%5D.tar.bz2'
SHA256='2c1c95aa8c23968a458c5c9cab4a6d337f0c61093172ea925cc4412bef772e8a'
SIZE=189876864

def main():
 p=argparse.ArgumentParser();p.add_argument('--destination',type=Path,required=True);p.add_argument('--archive',type=Path,help='Use a previously downloaded official archive');args=p.parse_args()
 args.destination.mkdir(parents=True,exist_ok=True)
 if any(args.destination.iterdir()):raise SystemExit('Destination must be empty; existing files are never overwritten.')
 archive=args.archive or args.destination/'official-demo.tar.bz2'
 if not args.archive:
  with urllib.request.urlopen(URL,timeout=90) as r,archive.open('xb') as f:
   n=0
   while chunk:=r.read(1024*1024):
    n+=len(chunk)
    if n>SIZE:raise SystemExit('Download exceeds known official archive size.')
    f.write(chunk)
 data=archive.read_bytes()
 if len(data)!=SIZE or hashlib.sha256(data).hexdigest()!=SHA256:raise SystemExit('Checksum mismatch; archive not extracted.')
 with tarfile.open(archive) as t:
  members=t.getmembers()
  if sum(m.size for m in members)>1024**3:raise SystemExit('Expanded archive exceeds 1 GiB limit.')
  if any(m.issym() or m.islnk() or not(m.isfile() or m.isdir()) for m in members):raise SystemExit('Unexpected special file/link.')
  t.extractall(args.destination,members=members,filter='data')
 print(args.destination/'Katawa Shoujo Act 1 v5-linux-x86/game')
if __name__=='__main__':main()
