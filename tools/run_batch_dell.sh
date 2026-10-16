#!/usr/bin/env bash
# Dell 上跑全库逐页抽取的受控启动器（CPU-only、单进程、低优先级）。
#
# 资源纪律：nice -n 15、ionice -c3、OMP/MKL/OPENBLAS=1、单 worker。
# 互斥：flock 独占锁 —— 已有实例在跑时直接退出，绝不并发第二个。
# 断点：batch_extract.py 自带逐页缓存，已缓存的页自动跳过。
#
# 用法： tools/run_batch_dell.sh [--scope all] [--limit-pages 0] [--timeout 1800]
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VENV=${VENV:-/home/fjd/workspaces/408-question-bank-dell/venv}
LOGDIR="$ROOT/build/_scratch/logs"
LOCK="$LOGDIR/batch.lock"
PIDFILE="$LOGDIR/batch.pid"
LOGFILE="$LOGDIR/batch.log"
SCOPE=all
LIMIT=0
MAXSECS=1800

while [ $# -gt 0 ]; do
  case "$1" in
    --scope) SCOPE=$2; shift 2 ;;
    --limit-pages) LIMIT=$2; shift 2 ;;
    --timeout) MAXSECS=$2; shift 2 ;;
    *) echo "未知参数: $1" >&2; exit 2 ;;
  esac
done

mkdir -p "$LOGDIR"
cd "$ROOT"

# 互斥：拿不到锁说明已有 worker 在跑
exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[skip] 已有 batch worker 在运行（锁 $LOCK），本次不启动第二个。" >&2
  exit 3
fi

if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "[skip] PID $(cat "$PIDFILE") 仍存活，不启动第二个。" >&2
  exit 3
fi

echo "$$" > "$PIDFILE"
echo "[start] pid=$$ scope=$SCOPE limit=$LIMIT timeout=${MAXSECS}s $(date -Is)" >> "$LOGFILE"

status=0
timeout "$MAXSECS" ionice -c3 nice -n 15 env \
  OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 \
  "$VENV/bin/python" -I tools/batch_extract.py \
    --scope "$SCOPE" --ocr auto --limit-pages "$LIMIT" >> "$LOGFILE" 2>&1 || status=$?

echo "[exit] status=$status $(date -Is)" >> "$LOGFILE"
rm -f "$PIDFILE"
exit "$status"
