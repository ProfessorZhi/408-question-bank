#!/usr/bin/env python3
"""Layout contact sheets for all PDF pages: vector-first raster previews."""
from pathlib import Path
import fitz
ROOT=Path(__file__).resolve().parent
OUT=ROOT/"previews-academic"
for name,prefix in [("Set01_Student_Academic.pdf","Student"),("Set01_Solutions_Academic.pdf","Solutions")]:
    src=fitz.open(OUT/name)
    for base in range(0,len(src),9):
        proof=fitz.open()
        page=proof.new_page(width=900,height=1190)
        for j in range(min(9,len(src)-base)):
            col,row=j%3,j//3
            x,y=22+col*290,42+row*380
            rect=fitz.Rect(x,y,x+268,y+346)
            page.show_pdf_page(rect,src,base+j,keep_proportion=True)
            page.insert_text((x+2,y-9),f"{prefix.upper()}  /  PAGE {base+j+1:02}",fontname="helv",fontsize=8.5,color=(.3,.3,.3))
        target=OUT/f"{prefix}_Pages_{base+1:02}-{min(base+9,len(src)):02}.png"
        page.get_pixmap(matrix=fitz.Matrix(1.35,1.35),alpha=False).save(target)
        proof.close()
        print("MONTAGE",target.name,target.stat().st_size)
    src.close()
