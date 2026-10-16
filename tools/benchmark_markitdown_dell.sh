#!/usr/bin/env bash
# Dell A6000 主机上的 PDF 抽取器小样本对照（阶段1）。
# 只读源 PDF，全部产物写 build/_scratch/。单进程 + nice，无 GPU。
#
# 依赖：系统 poppler(pdftotext/pdfinfo/pdfseparate) + 隔离 venv 内的 markitdown。
#   python3 -m venv --without-pip "$VENV"
#   curl -fsSL https://bootstrap.pypa.io/get-pip.py | "$VENV/bin/python" -I -
#   "$VENV/bin/pip" install "markitdown[pdf]"
#
# 用法：VENV=/path/to/venv tools/benchmark_markitdown_dell.sh [仓库根目录]
set -euo pipefail

ROOT=${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}
VENV=${VENV:-/home/fjd/workspaces/408-question-bank-dell/venv}
OUT="$ROOT/build/_scratch"
MD="$OUT/md"
TEXT_PDF="sources/exams/papers/2026.pdf"
SCAN_PDF="sources/mock-2027/pdf/mock2027-set2-paper.pdf"
NICE=(nice -n 10)
TIMEFMT='TIME=%es MAXRSS=%MKB'

command -v pdftotext >/dev/null || { echo "缺 poppler pdftotext" >&2; exit 1; }
[ -x "$VENV/bin/markitdown" ] || { echo "缺 $VENV/bin/markitdown" >&2; exit 1; }

mkdir -p "$MD"
cd "$ROOT"

echo "== 文本层普查 =="
for f in "$TEXT_PDF" "$SCAN_PDF"; do
  n=$(pdfinfo "$f" | awk '/^Pages/{print $2}')
  printf '%s\n  ' "$f"
  for p in $(seq 1 "$n"); do
    printf 'p%s:%s ' "$p" \
      "$(pdftotext -f "$p" -l "$p" "$f" - 2>/dev/null | tr -d '[:space:]' | wc -c)"
  done
  echo
done

echo "== pdftotext -layout =="
/usr/bin/time -f "$TIMEFMT" "${NICE[@]}" \
  pdftotext -layout "$TEXT_PDF" "$OUT/2026.txt" 2>&1 | tail -1
wc -m -l "$OUT/2026.txt"

echo "== markitdown（文字层卷）=="
/usr/bin/time -f "$TIMEFMT" "${NICE[@]}" env OMP_NUM_THREADS=1 \
  "$VENV/bin/markitdown" "$TEXT_PDF" -o "$MD/2026.md" 2>&1 | tail -1
wc -m -l "$MD/2026.md"

echo "== markitdown（扫描卷第1页）=="
"${NICE[@]}" pdfseparate -f 1 -l 1 "$SCAN_PDF" "$OUT/mock2-p1.pdf"
/usr/bin/time -f "$TIMEFMT" "${NICE[@]}" env OMP_NUM_THREADS=1 \
  "$VENV/bin/markitdown" "$OUT/mock2-p1.pdf" -o "$MD/mock2-p1.md" 2>&1 | tail -1
echo "扫描页输出字节数: $(wc -c < "$MD/mock2-p1.md")  (0 = 无文字层，非成功)"

echo "== 统计对照 =="
for f in "$OUT/2026.txt" "$MD/2026.md"; do
  printf '%s  ' "$f"
  for o in A B C D; do
    printf '%s:%s ' "$o" "$(grep -oE "(^|[^A-Za-z])$o[.、]" "$f" | wc -l)"
  done
  printf 'tableRows:%s\n' "$(grep -c '|' "$f" || true)"
done
