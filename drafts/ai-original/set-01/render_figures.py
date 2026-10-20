#!/usr/bin/env python3
"""Deterministic, dependency-free SVG diagrams derived from specs/exam.json.
Run without flags to write assets; --check compares regeneration with committed SVGs.
No fonts, scripts, remote resources or generated-model raster images are embedded.
"""
from pathlib import Path
import hashlib, html, json, math, sys
BASE=Path(__file__).resolve().parent
SPEC_PATH=BASE/'specs/exam.json'
RAW=SPEC_PATH.read_bytes(); SPEC=json.loads(RAW)
HASH=hashlib.sha256(RAW).hexdigest()
FIGURES={}
class SVG:
 def __init__(self,w,h,ident,title,desc):
  self.ident=ident; self.parts=[f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',f'<title id="title">{html.escape(title)}</title>',f'<desc id="desc">{html.escape(desc)}</desc>', '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#111"/></marker></defs>', '<style>text{font-family:Arial,DejaVu Sans,sans-serif;fill:#111} .line{fill:none;stroke:#111;stroke-width:2.4;stroke-linecap:round;stroke-linejoin:round}</style>',f'<metadata>{html.escape(json.dumps({"figure_id":ident,"spec_sha256":HASH,"renderer":"render_figures.py/v1"},sort_keys=True))}</metadata>',f'<rect width="{w}" height="{h}" fill="white"/>']
 def text(self,x,y,s,size=22,anchor='middle',bold=False):
  self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}"'+(' font-weight="700"' if bold else '')+'>'+html.escape(str(s))+'</text>')
 def line(self,x1,y1,x2,y2,arrow=False,dash=False,extra=''):
  self.parts.append(f'<path class="line" d="M{x1},{y1} L{x2},{y2}"'+(' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="8 6"' if dash else '')+(' '+extra if extra else '')+'/>')
 def path(self,d,arrow=False,dash=False,extra=''):
  self.parts.append(f'<path class="line" d="{d}"'+(' marker-end="url(#arrow)"' if arrow else '')+(' stroke-dasharray="8 6"' if dash else '')+(' '+extra if extra else '')+'/>')
 def rect(self,x,y,w,h,label=None,ident=None,size=22):
  self.parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="4" fill="white" stroke="#111" stroke-width="2.4"'+(f' data-node="{html.escape(str(ident))}"' if ident is not None else '')+'/>')
  if label is not None:self.text(x+w/2,y+h/2+size*.35,label,size)
 def node(self,x,y,label,ident=None,r=32):
  self.parts.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="white" stroke="#111" stroke-width="2.4"'+(f' data-node="{html.escape(str(ident))}"' if ident is not None else '')+'/>')
  self.text(x,y+7,label,22)
 def edge(self,loc,u,v,label=None,dash=False,curve=None,r=32):
  x,y=loc[u];X,Y=loc[v];dx=X-x;dy=Y-y;l=math.hypot(dx,dy)
  ex=f'data-edge="{html.escape(str(u))}--{html.escape(str(v))}"'
  if curve:self.path(curve,dash=dash,extra=ex)
  else:self.line(round(x+r*dx/l,2),round(y+r*dy/l,2),round(X-r*dx/l,2),round(Y-r*dy/l,2),dash=dash,extra=ex)
  if label is not None:
   mx=(x+X)/2;my=(y+Y)/2-9
   self.parts.append(f'<rect x="{mx-16}" y="{my-20}" width="32" height="27" fill="white"/>');self.text(mx,my,label,21)
 def finish(self):return '\n'.join(self.parts+['</svg>'])+'\n'
 def save(self,name): FIGURES[name]=self.finish()

s=SVG(720,400,'q05','Q05 BFS tree and a non-tree edge','Solid edges sa,sb,ac,bd form T. Dashed cd is e.');pos={'s':(85,190),'a':(320,80),'b':(320,300),'c':(580,80),'d':(580,300)}
for u,v in SPEC['q05']['tree_edges']:s.edge(pos,u,v)
for u,v in SPEC['q05']['extra_edges']:s.edge(pos,u,v,dash=True)
for n,xy in pos.items():s.node(*xy,n,n)
s.text(605,197,'e',24);s.text(350,377,'Solid: T     Dashed: e (not in T)',21);s.save('q05-bfs.svg')

s=SVG(940,455,'q06','Q06 weighted undirected graph','AB AC BC DE have weight1; BD CD weight2; AD weight4. Crossings without nodes do not connect.');pos={'A':(95,220),'B':(340,95),'C':(340,350),'D':(650,220),'E':(860,220)}
for u,v,w in SPEC['q06']['edges']:
 if (u,v)==('A','D'):
  s.edge(pos,u,v,curve='M95,188 C100,0 650,0 650,188');s.text(374,48,w,22)
 else:s.edge(pos,u,v,w)
for n,xy in pos.items():s.node(*xy,n,n)
s.text(470,430,'Undirected edges; numbers are weights.',21);s.save('q06-mst.svg')

s=SVG(840,395,'q07','Q07 red-black tree with unknown colors','Root4 black,1 and3 red. Unknown colors on2,6,5. Every omitted null pointer is a black NIL leaf.');pos={'4':(410,60),'2':(210,180),'6':(610,180),'1':(95,305),'3':(320,305),'5':(515,305),'nil':(725,305)}
for u,vs in SPEC['q07']['children'].items():
 for v in vs:
  if v is not None:s.edge(pos,u,str(v),r=40)
s.edge(pos,'6','nil',r=40)
for n in ['4','2','6','1','3','5']:s.node(*pos[n],f'{n} ({SPEC["q07"]["known_colors"].get(n,"?")})',n,r=40)
s.rect(695,285,60,40,'NIL',size=18);s.text(420,378,'B = black; R = red; all NIL leaves are black.',20);s.save('q07-rbtree.svg')

s=SVG(1000,365,'q08','Q08 B+ tree range scan','Root separators20,40; leaves3,8,12 then20,25,32 then40,47,51. Root cached.');s.text(500,35,'Root page (cached)',22)
s.rect(390,60,220,60);s.line(500,60,500,120);s.text(445,99,SPEC['q08']['separators'][0]);s.text(555,99,SPEC['q08']['separators'][1])
for i,x in enumerate([50,390,730]):
 s.line(405+i*95,120,x+110,235,arrow=True)
 vals=SPEC['q08']['leaves'][i];s.rect(x,235,220,55,ident=f'leaf-{i}')
 for j,v in enumerate(vals):
  if j:s.line(x+j*220/3,235,x+j*220/3,290)
  s.text(x+(j+.5)*220/3,271,v)
 if i<2:s.line(x+220,263,x+340,263,arrow=True,dash=True)
 s.text(x+110,320,f'L{i+1}',20)
s.save('q08-bplus.svg')

def pipeline(ident,title,detailed=False):
 w=1200;h=450 if detailed else 340
 s=SVG(w,h,ident,title,'Five stages IF ID EX MEM WB with interstage registers. EX/MEM and MEM/WB can forward to EX. Branches in detailed figure resolve at EX end.');xs=[40,270,500,730,960];width=185;y=100
 for i,name in enumerate(SPEC['machine']['stages']):
  s.rect(xs[i],y,width,80,ident=name);s.text(xs[i]+width/2,y+32,name,25,bold=True)
  text=['PC / instruction','register read','ALU / branch','data memory','register write'][i]
  s.text(xs[i]+width/2,y+60,text,17)
  if i<4:
   s.line(xs[i]+width,y+40,xs[i+1],y+40,arrow=True)
   s.line(xs[i]+width+21,y+20,xs[i]+width+21,y+60,extra='stroke-width="5"')
 s.path('M706,140 L706,250 L590,250 L590,180',arrow=True)
 s.text(740,242,'EX/MEM to EX',18,anchor='start')
 s.path('M936,140 L936,295 L548,295 L548,180',arrow=True)
 s.text(956,290,'MEM/WB',18)
 if detailed:
  s.path('M590,100 L590,55 L133,55 L133,100',arrow=True,dash=True);s.text(360,42,'taken branch: flush IF + ID; refetch target',18)
  for i,delay in enumerate(SPEC['machine']['stage_ps']):s.text(xs[i]+width/2,87,f'{delay} ps',20)
  s.text(600,365,'Every stage register: +20 ps',22)
  s.text(600,405,'Load value ready at MEM-end; ALU value ready at EX-end.',20)
 else:s.text(600,40,title,23,bold=True);s.text(600,327,'No same-cycle MEM-end to EX-end use.',20)
 return s
pipeline('q19','Q19 forwarding and load-use').save('q19-pipeline.svg')
pipeline('q43','Q43 teaching machine M',True).save('q43-machine.svg')

s=SVG(1030,390,'q35','Q35 self-learning Ethernet switches','S1 ports1,2,3 to H1,H2,S2; S2 ports1,2,3 to S1,H3,H4.');s.rect(280,160,135,70,'S1','S1');s.rect(610,160,135,70,'S2','S2')
for x,y,n in [(60,55,'H1'),(60,285,'H2'),(845,55,'H3'),(845,285,'H4')]:s.rect(x,y,105,60,n,n)
s.line(165,85,280,175);s.text(258,161,'1',19)
s.line(165,315,280,215);s.text(258,252,'2',19)
s.line(415,195,610,195);s.text(439,178,'3',19);s.text(586,178,'1',19)
s.line(745,175,845,85);s.text(767,160,'2',19)
s.line(745,215,845,315);s.text(767,253,'3',19)
s.text(515,365,'One VLAN; forwarding tables initially empty.',20);s.save('q35-switches.svg')

s=SVG(1000,665,'q36','Q36 selective repeat timeline','Sequence modulus8, window4. Original F6 lost. F7,F0,F1 acknowledged; retransmitted F6 received but ACK6 lost. Diagram not to scale.');L=165;R=835
s.text(L,38,'Sender',24,bold=True);s.text(R,38,'Receiver',24,bold=True);s.line(L,65,L,625,arrow=True);s.line(R,65,R,625,arrow=True)
def event(s,x1,y1,x2,y2,label,lost=False):
 if lost:
  end=x1+(x2-x1)*.65;ey=y1+(y2-y1)*.65;s.line(x1,y1,end,ey,arrow=False,dash=True)
  s.line(end-8,ey-8,end+8,ey+8);s.line(end-8,ey+8,end+8,ey-8);s.text(end,ey+31,'lost',17)
 else:s.line(x1,y1,x2,y2,arrow=True)
 mx=(x1+x2)/2;my=(y1+y2)/2-9;s.parts.append(f'<rect x="{mx-100}" y="{my-19}" width="200" height="24" fill="white"/>');s.text(mx,my,label,18)
event(s,L,87,R,123,'F6',True)
event(s,L,155,R,185,'F7');event(s,R,204,L,235,'ACK7')
event(s,L,266,R,296,'F0');event(s,R,315,L,346,'ACK0')
event(s,L,377,R,407,'F1');event(s,R,426,L,457,'ACK1')
event(s,L,498,R,532,'F6 (retransmit)');event(s,R,552,L,590,'ACK6',True)
s.text(500,645,'Time runs downward; only listed losses occur.',18);s.save('q36-sr.svg')

s=SVG(1000,460,'q38','Q38 TCP reordering and sample time','Three 400B data segments; seq1401 arrives before1001, then1801 later. T is after second arrival. ACK values intentionally not printed.');L=150;R=830
s.text(L,38,'Sender',24,bold=True);s.text(R,38,'Receiver',24,bold=True);s.line(L,60,L,420,arrow=True);s.line(R,60,R,420,arrow=True)
s.line(L,90,R,250,arrow=True);s.text(370,110,'seq=1001, len=400',18)
s.line(L,145,R,190,arrow=True);s.text(615,157,'seq=1401, len=400',18)
s.line(L,205,R,380,arrow=True);s.text(455,260,'seq=1801, len=400',18)
s.line(725,282,915,282,dash=True);s.text(940,289,'T',24,bold=True)
s.text(500,447,'Arrival order: 1401, 1001, 1801; not to scale.',18);s.save('q38-tcp.svg')

s=SVG(1240,305,'q41','Q41 duplicate-aware sorted version lists','The two rows are nondecreasing singly linked lists. Arrows are next pointers, not integer adjacency.');
for row,key in enumerate(['a','b']):
 y=65+row*125;s.text(35,y+30,key.upper(),24,bold=True)
 vals=SPEC['q41'][key]
 for i,v in enumerate(vals):
  x=80+i*95;s.rect(x,y,72,50,ident=f'{key}{i}');s.line(x+49,y,x+49,y+50);s.text(x+24,y+33,v,22)
  if i<len(vals)-1:s.line(x+72,y+25,x+95,y+25,arrow=True)
  else:s.line(x+72,y+25,x+93,y+25,arrow=True);s.text(x+123,y+32,'NULL',17)
s.text(620,288,'Repeated keys count once; next pointer does not imply consecutive integers.',18);s.save('q41-lists.svg')

s=SVG(920,370,'q42','Q42 initial AVL tree','Root30;10 has right20;50 has left40 and right60.');pos={'30':(440,60),'10':(200,180),'20':(300,300),'50':(680,180),'40':(570,300),'60':(790,300)}
for n,vs in SPEC['q42']['children'].items():
 for v in vs:
  if v is not None:s.edge(pos,n,str(v))
for n,xy in pos.items():s.node(*xy,n,n)
s.save('q42-avl.svg')

s=SVG(1160,370,'q42-answer','Solution Q42 two final AVL states','Left after inserting15; right after replacing50 with predecessor40 and deleting original40.');
for title,offset,nodes,edges in [
 ('After inserting 15',0,{'30':(280,100),'15':(150,210),'50':(410,210),'10':(70,310),'20':(220,310),'40':(340,310),'60':(490,310)},[['30','15'],['30','50'],['15','10'],['15','20'],['50','40'],['50','60']]),
 ('Then deleting 50',580,{'30':(280,100),'15':(150,210),'40':(410,210),'10':(70,310),'20':(220,310),'60':(490,310)},[['30','15'],['30','40'],['15','10'],['15','20'],['40','60']])]:
 s.text(offset+280,40,title,22,bold=True);pp={n:(x+offset,y)for n,(x,y)in nodes.items()}
 for u,v in edges:s.edge(pp,u,v,r=28)
 for n,xy in pp.items():s.node(*xy,n,f'{offset}-{n}',r=28)
s.save('q42-answer.svg')

s=SVG(1140,420,'q45','Q45 one slot and two independent subscribers','Producer P writes version k into one reusable slot; A and B must each read this version before P may overwrite. The figure describes data flow, not a P/V solution.')
s.rect(45,175,190,85,ident='P');s.text(140,223,'Producer P',24,bold=True)
s.rect(405,175,190,85,ident='slot');s.text(500,222,'single slot',23,bold=True)
s.rect(840,65,240,90,ident='A');s.text(960,117,'Subscriber A',23,bold=True)
s.rect(840,265,240,90,ident='B');s.text(960,317,'Subscriber B',23,bold=True)
s.line(235,218,405,218,arrow=True)
s.line(595,198,840,110,arrow=True)
s.line(595,235,840,310,arrow=True)
s.text(320,192,'write k',20);s.text(705,115,'read k',20);s.text(705,310,'read k',20)
s.text(565,395,'Each version must reach both subscribers before replacement.',20)
s.save('q45-buffer.svg')

s=SVG(1400,390,'q47','Q47 one path with a smaller intermediate MTU','TCP traffic travels from H through R1 and R2 to V. Access links have MTU 1500 B at 100 Mb/s; the middle link has MTU 620 B at 12 Mb/s. The RTT is 40 ms.')
s.rect(60,168,110,66,ident='H');s.text(115,207,'H',26,bold=True)
s.rect(395,168,125,66,ident='R1');s.text(457,207,'R1',26,bold=True)
s.rect(825,168,125,66,ident='R2');s.text(887,207,'R2',26,bold=True)
s.rect(1200,168,110,66,ident='V');s.text(1255,207,'V',26,bold=True)
s.line(170,201,395,201);s.line(520,201,825,201);s.line(950,201,1200,201)
s.text(285,107,'100 Mb/s',22);s.text(285,139,f'MTU {SPEC["q47"]["local_mtu_bytes"]} B',21)
s.text(675,107,f'{SPEC["q47"]["bottleneck_link_bps"]//1000000} Mb/s',22)
s.text(675,139,f'MTU {SPEC["q47"]["bottleneck_mtu_bytes"]} B',21)
s.text(1080,107,'100 Mb/s',22);s.text(1080,139,f'MTU {SPEC["q47"]["local_mtu_bytes"]} B',21)
s.text(700,320,f'H - V TCP RTT = {int(SPEC["q47"]["rtt_seconds"]*1000)} ms',23)
s.text(700,358,'DF flag, packet captures and TCP sequence numbers are in the question.',19)
s.save('q47-network.svg')

def main():
 check='--check' in sys.argv
 if not check:(BASE/'assets').mkdir(exist_ok=True)
 for name,content in FIGURES.items():
  p=BASE/'assets'/name
  if check:
   if not p.exists() or p.read_text(encoding='utf-8')!=content:raise SystemExit('SVG mismatch: '+name)
  else:p.write_text(content,encoding='utf-8')
 print(f'[figures] {"verified" if check else "rendered"} {len(FIGURES)} deterministic SVG files; spec sha256 {HASH}')
if __name__=='__main__':main()
