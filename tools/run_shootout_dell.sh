#!/usr/bin/env bash
# PDF→Markdown 解析器横向实测（CPU-only，Dell）。
#
# 对 build/_scratch/shootout/samples/ 下每个单页样本 PDF，分别跑各解析器，
# 输出到 build/_scratch/shootout/out/<tool>/，并把耗时/峰值内存记为 CSV。
#
# 资源纪律：nice 15、OMP/MKL=1、单进程、CPU-only、无网络服务。
# 仅为基准；产物是草稿，不得入库。
set -uo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
BASE=/home/fjd/workspaces/408-question-bank-dell
VENV=$BASE/venv              # pymupdf / markitdown / rapidocr
VENV2=$BASE/venv-compare     # pymupdf4llm
SAMPLES=$ROOT/build/_scratch/shootout/samples
OUT=$ROOT/build/_scratch/shootout/out
CSV=$ROOT/build/_scratch/shootout/metrics.csv

cd "$ROOT"
mkdir -p "$OUT" "$OUT"/{pdftotext,markitdown,pymupdf,pymupdf4llm,rapidocr}
echo "tool,sample,seconds,maxrss_kb,bytes" > "$CSV"

NICE=(nice -n 15 env OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1)

for pdf in "$SAMPLES"/*.pdf; do
  name=$(basename "$pdf" .pdf)
  echo "== $name =="

  /usr/bin/time -f "%e,%M" ${NICE[@]} pdftotext -layout "$pdf" "$OUT/pdftotext/$name.txt" 2>"$OUT/.t"
  printf 'pdftotext,%s,%s,%s\n' "$name" "$(tail -1 "$OUT/.t" | tr -d "\r")" "$(stat -c%s "$OUT/pdftotext/$name.txt")" >> "$CSV"

  /usr/bin/time -f "%e,%M" ${NICE[@]} "$VENV/bin/markitdown" "$pdf" -o "$OUT/markitdown/$name.md" 2>"$OUT/.t"
  printf 'markitdown,%s,%s,%s\n' "$name" "$(tail -1 "$OUT/.t" | tr -d "\r")" "$(stat -c%s "$OUT/markitdown/$name.md")" >> "$CSV"

  /usr/bin/time -f "%e,%M" ${NICE[@]} "$VENV/bin/python" -I -c \
    'import pymupdf,sys;d=pymupdf.open(sys.argv[1]);sys.stdout.write("\n".join(p.get_text() for p in d))' \
    "$pdf" > "$OUT/pymupdf/$name.txt" 2>"$OUT/.t"
  printf 'pymupdf,%s,%s,%s\n' "$name" "$(tail -1 "$OUT/.t" | tr -d "\r")" "$(stat -c%s "$OUT/pymupdf/$name.txt")" >> "$CSV"

  /usr/bin/time -f "%e,%M" ${NICE[@]} "$VENV2/bin/python" -I -c \
    'import pymupdf4llm,sys;sys.stdout.write(pymupdf4llm.to_markdown(sys.argv[1]))' \
    "$pdf" > "$OUT/pymupdf4llm/$name.md" 2>"$OUT/.t"
  printf 'pymupdf4llm,%s,%s,%s\n' "$name" "$(tail -1 "$OUT/.t" | tr -d "\r")" "$(stat -c%s "$OUT/pymupdf4llm/$name.md")" >> "$CSV"

  /usr/bin/time -f "%e,%M" ${NICE[@]} "$VENV/bin/python" -I tools/ocr_cpu_pilot.py \
    "$pdf" -p 1 --scale 2 -o "$OUT/rapidocr/$name.txt" --scratch "$OUT/rapidocr/png" \
    > "$OUT/rapidocr/$name.json" 2>"$OUT/.t" || true
  printf 'rapidocr,%s,%s,%s\n' "$name" "$(tail -1 "$OUT/.t" | tr -d "\r")" "$(stat -c%s "$OUT/rapidocr/$name.txt" 2>/dev/null || echo 0)" >> "$CSV"
done

echo "--- metrics.csv ---"; cat "$CSV"
