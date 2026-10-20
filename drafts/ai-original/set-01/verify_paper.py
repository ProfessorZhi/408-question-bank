#!/usr/bin/env python3
"""Reproducible structural and computational cross-checks for AI408 Set01.

Python stdlib + a C11 compiler (gcc or cc). No network, personal device access,
API secrets, student data or third-party packages are used. C build products are
kept in TemporaryDirectory and discarded. --json PATH writes an optional report.
This is author-run executable checking, NOT an independent expert review.
"""
from __future__ import annotations
import argparse, bisect, collections, ctypes, functools, hashlib, heapq
import ipaddress, itertools, json, math, pathlib, random, re, shutil
import struct, subprocess, tempfile, xml.etree.ElementTree as ET
from fractions import Fraction

BASE=pathlib.Path(__file__).resolve().parent
S=json.loads((BASE/'specs/exam.json').read_text(encoding='utf-8'))
RESULTS={}

def record(n,summary,tests=1,mode='executable-cross-check'):
    RESULTS[str(n)]={'mode':mode,'checks_or_cases':tests,'result':summary}

def choose(n,value,alternatives):
    matches=[chr(65+i) for i,x in enumerate(alternatives) if x==value]
    assert len(matches)==1,(n,value,alternatives)
    assert matches[0]==S['answer_key'][str(n)],(n,matches,S['answer_key'][str(n)])
    return matches[0]

def sections(text):
    marks=list(re.finditer(r'^### 第\s*(\d+)\s*题\s*$',text,re.M))
    return [(int(m.group(1)),text[m.end():marks[i+1].start() if i+1<len(marks) else len(text)])for i,m in enumerate(marks)]

def structure():
    qtext=(BASE/'questions.md').read_text(encoding='utf-8')
    stex=(BASE/'solutions.md').read_text(encoding='utf-8')
    qs=sections(qtext);ss=sections(stex)
    assert [n for n,_ in qs]==list(range(1,48))
    assert [n for n,_ in ss]==list(range(1,48))
    answer_keys={}
    for (n,q),(_,sol) in zip(qs,ss):
        if n<=40:
            opts=re.findall(r'^([ABCD])\.\s+(.+)$',q,re.M)
            assert [o[0] for o in opts]==list('ABCD'),n
            assert len({o[1] for o in opts})==4,n
            m=re.search(r'\*\*答案：([ABCD])。\*\*',sol)
            assert m,n
            answer_keys[str(n)]=m.group(1)
        else:
            assert '评分细则' in sol,n
    assert answer_keys==S['answer_key']
    assert not re.search(r'(?:正确答案|参考答案|答案\s*[:：]\s*[ABCD])',qtext)
    marks={41:13,42:10,43:12,44:11,45:7,46:8,47:9}
    rubrics={41:[4,7,2],42:[4,3,3],43:[2,4,4,2],44:[3,2,3,3],45:[2,4,1],46:[3,3,2],47:[2,3,2,2]}
    for n,body in qs[40:]:
        assert re.search(rf'（{marks[n]}分）',body),n
        assert sum(rubrics[n])==marks[n]
    assert 80+sum(marks.values())==150
    refs=[]
    for text in [qtext,stex]:
        for ref in re.findall(r'!\[[^\]]*\]\(([^)]+)\)',text):
            assert not re.match(r'^[a-zA-Z]+:|^/',ref),ref
            p=(BASE/ref).resolve();assert p.is_relative_to(BASE.resolve()) and p.is_file(),ref
            refs.append(ref)
    assert len(set(refs))==15,len(set(refs))
    assert len(re.findall(r'!\[',qtext))==14
    subprocess.run([__import__('sys').executable,str(BASE/'render_figures.py'),'--check'],check=True)
    spec_hash=hashlib.sha256((BASE/'specs/exam.json').read_bytes()).hexdigest()
    for ref in set(refs):
        root=ET.parse(BASE/ref).getroot()
        assert root.tag=='{http://www.w3.org/2000/svg}svg'
        assert root.find('{http://www.w3.org/2000/svg}title') is not None
        assert root.find('{http://www.w3.org/2000/svg}desc') is not None
        data=json.loads(root.find('{http://www.w3.org/2000/svg}metadata').text)
        assert data['spec_sha256']==spec_hash
        for e in root.iter():
            assert e.tag.split('}')[-1] not in {'script','foreignObject'}
            for k,v in e.attrib.items():
                if k.endswith('href'):assert not re.match(r'https?:|javascript:',v)
    c_source=(BASE/'reference_q41.c').read_text(encoding='utf-8')
    fn=c_source[c_source.index('int longestCommonRun'):].strip()
    assert fn in dict(ss)[41],'displayed Q41 code differs from compiled reference'
    return {'question_count':47,'choice_options':160,'points':150,'question_figures':14,'svg_files':15,'teacher_only_svg':1,'q41_code_matches_display':True}

@functools.lru_cache(None)
def shapes(n):
    if n==0:return (None,)
    return tuple((l,r)for k in range(n)for l in shapes(k)for r in shapes(n-1-k))

def post_for_shape(t,labels):
    it=iter(labels)
    def run(node):
        if node is None:return ''
        key=next(it)
        return run(node[0])+run(node[1])+key
    return run(t)

def graph_bfs(v,edges,root):
    adj={x:[]for x in v}
    for a,b in edges:adj[a].append(b);adj[b].append(a)
    for a in adj:adj[a].sort()
    dist={root:0};par={};q=collections.deque([root])
    while q:
        a=q.popleft()
        for b in adj[a]:
            if b not in dist:dist[b]=dist[a]+1;par[b]=a;q.append(b)
    return dist,par

@functools.lru_cache(None)
def huffman_outcomes(state):
    if len(state)==1:return frozenset({tuple(sorted(state[0][1]))})
    weights=sorted(x[0] for x in state);target=weights[:2];out=set()
    for i,j in itertools.combinations(range(len(state)),2):
        if sorted((state[i][0],state[j][0]))!=target:continue
        a,b=state[i],state[j]
        joined=(a[0]+b[0],tuple(sorted((c,d+1)for c,d in a[1]+b[1])))
        rest=tuple(sorted([state[k]for k in range(len(state))if k not in (i,j)]+[joined]))
        out.update(huffman_outcomes(rest))
    return frozenset(out)

@functools.lru_cache(None)
def optimal_merge(blocks):
    if len(blocks)==1:return 0
    return min(2*(blocks[i]+blocks[j])+optimal_merge(tuple(sorted([blocks[k]for k in range(len(blocks))if k not in(i,j)]+[blocks[i]+blocks[j]])))for i,j in itertools.combinations(range(len(blocks)),2))

def tests_ds():
    cases=0
    for n in range(1,7):
        for a in itertools.product((-1,0,1),repeat=n):
            j=0;inc=0;outer=0
            for i in range(n):
                outer+=1
                while j<n and a[j]<=a[i]:j+=1;inc+=1
            assert inc<=n and outer==n;cases+=1
    choose(1,'linear',['logarithmic','nlogn','linear','quadratic']);record(1,'monotone pointer increments <= n; outer visits exactly n (general proof in solution)',cases)
    p=S['q02'];possible=set()
    def dfs(nexti,stack,out):
        if len(out)==len(p['input']):possible.add(tuple(out));return
        if nexti<len(p['input']) and len(stack)<p['capacity']:dfs(nexti+1,stack+[p['input'][nexti]],out)
        if stack:dfs(nexti,stack[:-1],out+[stack[-1]])
    dfs(0,[],[])
    bad=[i for i,o in enumerate(p['options']) if tuple(o)not in possible]
    assert bad==[0];choose(2,0,[0,1,2,3]);record(2,{'legal_sequences':len(possible),'invalid_option':'A'},len(possible))
    p=S['q03'];vals=[t for t in shapes(len(p['preorder']))if post_for_shape(t,p['preorder'])==p['postorder']]
    choose(3,len(vals),[2,4,8,16]);record(3,{'matching_trees':len(vals)},len(shapes(5)))
    w=S['q04']['weights'];state=tuple(sorted((v,((c,0),))for c,v in w.items()));outs=huffman_outcomes(state)
    costs={sum(w[c]*d for c,d in x)for x in outs};maxlen={max(d for _,d in x)for x in outs}
    assert costs=={12} and maxlen=={2,3};choose(4,(True,False,True),[(True,False,False),(False,True,True),(True,True,True),(True,False,True)])
    record(4,{'all_WPL':sorted(costs),'max_lengths':sorted(maxlen),'distinct_code_length_assignments':len(outs)},len(outs))
    p=S['q05'];edges=p['tree_edges']+p['extra_edges'];d,par=graph_bfs(p['vertices'],edges,p['source']);dp,_=graph_bfs(p['vertices'],p['tree_edges'],p['source']);assert d==dp
    assert graph_bfs(p['vertices'],edges,'c')[0]['d']==1
    assert graph_bfs(p['vertices'],p['tree_edges'],'c')[0]['d']==4
    trials=0
    for n in range(2,6):
        v=list(range(n));complete=list(itertools.combinations(v,2))
        for mask in range(1,1<<len(complete)):
            edges=[e for i,e in enumerate(complete)if(mask>>i)&1]
            if len(graph_bfs(v,edges,0)[0])!=n:continue
            for src in v:
                d,par=graph_bfs(v,edges,src);tree={tuple(sorted((x,y)))for x,y in par.items()}
                for e in edges:
                    if e in tree:continue
                    dd,pp=graph_bfs(v,[x for x in edges if x!=e],src)
                    assert dd==d and pp==par,(v,edges,src,e);trials+=1
    choose(5,(True,False,True),[(True,False,False),(True,False,True),(False,True,True),(True,True,True)])
    record(5,{'example_c_to_d':[1,4],'source_distances_preserved':True,'same_sorted_adjacency_BFS_tree_preserved':True},trials)
    p=S['q06'];best=math.inf;trees=[];subsets=0
    for es in itertools.combinations(p['edges'],len(p['vertices'])-1):
        subsets+=1
        if len(graph_bfs(p['vertices'],[(a,b)for a,b,_ in es],p['vertices'][0])[0])<len(p['vertices']):continue
        cost=sum(w for _,_,w in es)
        if cost<best:best=cost;trees=[es]
        elif cost==best:trees.append(es)
    assert best==5 and len(trees)==6
    def classify(e):
        count=sum(any((a,b)==e for a,b,_ in tree)for tree in trees)
        return 'all' if count==len(trees)else'none' if count==0 else'some'
    value=tuple(classify(e)for e in [('A','B'),('D','E'),('A','D')])
    choose(6,value,[('all','all','none'),('some','all','some'),('all','some','none'),('some','all','none')]);record(6,{'MST_weight':best,'MST_count':len(trees),'classes':value},subsets)
    p=S['q07'];valid=[]
    for colors in itertools.product('BR',repeat=3):
        c=dict(p['known_colors']);c.update(zip(map(str,p['unknown_order']),colors))
        def blackheight(n,lo=-math.inf,hi=math.inf):
            if n is None:return 1
            assert lo<n<hi
            u=str(n);a,b=p['children'][u]
            if c[u]=='R':assert all(v is None or c[str(v)]=='B'for v in(a,b))
            l=blackheight(a,lo,n);r=blackheight(b,n,hi);assert l==r
            return l+int(c[u]=='B')
        try:
            assert c[str(p['root'])]=='B';blackheight(p['root']);valid.append(colors)
        except AssertionError:pass
    assert valid==[('B','B','R')]
    choose(7,valid[0],[('B','R','B'),('R','B','R'),('B','B','R'),('B','B','B')]);record(7,{'unique_colors':valid},8)
    p=S['q08'];leaf=bisect.bisect_right(p['separators'],p['lower']);reads=0;result=[];stop=False
    for block in p['leaves'][leaf:]:
        reads+=1
        for key in block:
            if key>p['upper']:stop=True;break
            if key>=p['lower']:result.append(key)
        if stop:break
    choose(8,(reads,len(result)),[(2,4),(3,4),(3,5),(4,4)]);record(8,{'leaf_reads':reads,'records':result})
    p=S['q09'];prefix=p['pattern'][:p['matched_prefix_length']];k=max([0]+[k for k in range(1,len(prefix))if prefix[:k]==prefix[-k:]])
    choose(9,(k,len(prefix)-k),[(3,2),(2,3),(1,4),(0,5)]);record(9,{'fallback':k,'shift':len(prefix)-k})
    a=[tuple(x)for x in S['q10']['records']];pivot=a[-1][0];i=-1
    for j in range(len(a)-1):
        if a[j][0]<pivot:i+=1;a[i],a[j]=a[j],a[i]
    a[i+1],a[-1]=a[-1],a[i+1]
    order=[tag for key,tag in a if key==2]
    choose(10,(order==['a','b'],a==[(1,'x'),(2,'a'),(2,'b')]),[(True,True),(True,False),(False,True),(False,False)])
    record(10,{'records':a,'equal_key_order_preserved':False})
    blocks=tuple(sorted(S['q11']['run_blocks']));cost=optimal_merge(blocks)
    h=list(blocks);greedy=0
    while len(h)>1:
        s=heapq.heappop(h)+heapq.heappop(h);greedy+=2*s;heapq.heappush(h,s)
    assert cost==greedy;choose(11,cost,[95,190,200,300]);record(11,{'min_block_IO':cost,'independent_greedy_agrees':True},optimal_merge.cache_info().currsize)

def signed(x,bits):return x-(1<<bits) if x&(1<<(bits-1)) else x

def pipeline(program,code_base,initial,word_memory):
    """Cycle-level model: writes in WB, wrong-path instructions flushed in ID/IF."""
    regs=[0]*8
    for k,v in initial.items():regs[int(k)]=v&0xffffffff
    pc=code_base;uid=0
    def fetch():
        nonlocal pc,uid
        index=(pc-code_base)//4
        if pc<code_base or pc>=code_base+4*len(program):return None
        assert (pc-code_base)%4==0
        instruction={'seq':uid,'index':index,'address':pc,'op':program[index][0],'rd':program[index][1],'rs':program[index][2],'arg':program[index][3]};uid+=1;pc+=4
        return instruction
    stages=[fetch(),None,None,None,None];cycle=0;trace=[];retired=[];stall_count=0;branches=[]
    def sources(it):
        if it is None:return []
        return [it['rs'],it['arg']] if it['op']=='ADD' else [it['rs']]
    while any(x is not None for x in stages):
        cycle+=1;assert cycle<200
        trace.append({'cycle':cycle,'stages':[(x['index']+1,x['seq'])if x else None for x in stages]})
        f,d,e,m,w=stages
        if w:
            if w['op']!='BNZ' and w['rd']!=0:regs[w['rd']]=w['result']&0xffffffff
            retired.append((w['index']+1,cycle,w['seq']))
        if m and m['op']=='LW':m['result']=word_memory[m['ea']]&0xffffffff
        def read_for_ex(r):
            if r==0:return 0
            if m and m['op']!='BNZ' and m['rd']==r:
                assert m['op']!='LW','unresolved load-use'
                return m['result']
            return regs[r]
        taken=False;target=None
        if e:
            x=read_for_ex(e['rs']);op=e['op']
            if op=='ADD':e['result']=(x+read_for_ex(e['arg']))&0xffffffff
            elif op=='ADDI':e['result']=(x+e['arg'])&0xffffffff
            elif op=='LW':e['ea']=(x+e['arg'])&0xffffffff
            elif op=='BNZ':
                taken=(x!=0);target=(e['address']+4+4*e['arg'])&0xffffffff
                branches.append({'index':e['index']+1,'cycle':cycle,'taken':taken,'target':target})
            else:raise AssertionError(op)
        stalled=bool(d and e and e['op']=='LW' and e['rd']!=0 and e['rd'] in sources(d))
        if taken:
            pc=target
            stages=[fetch(),None,None,e,m]
        elif stalled:
            stall_count+=1;stages=[f,d,None,e,m]
        else:
            stages=[fetch(),f,d,e,m]
    return {'cycles':cycle,'regs':regs,'trace':trace,'retired':retired,'load_stalls':stall_count,'branches':branches}

def tests_co():
    p=S['q12'];n=p['word_bits'];mod=1<<n;r=(p['x']-p['y'])%mod;borrow=int(p['x']<p['y']);z=signed(p['x'],n)-signed(p['y'],n);overflow=int(not -(1<<(n-1))<=z<(1<<(n-1)))
    choose(12,(r,borrow,overflow),[(127,0,1),(127,1,0),(129,0,1),(127,1,1)]);record(12,{'result_hex':hex(r),'CF':borrow,'OF':overflow})
    fracbits=[];structbits=[]
    for k in S['q13']['exact_offsets_halfulp']:
        offset=Fraction(k,2)
        floor=offset.numerator//offset.denominator;delta=offset-floor
        q=floor+(1 if delta>Fraction(1,2) or delta==Fraction(1,2) and floor%2 else 0)
        fracbits.append(0x3f800000+q)
        structbits.append(struct.unpack('>I',struct.pack('>f',1+k*2**-24))[0])
    assert fracbits==structbits
    alternatives=[(0x3f800000,0x3f800001),(0x3f800001,0x3f800002),(0x3f800001,0x3f800003),(0x3f800000,0x3f800002)]
    choose(13,tuple(fracbits),alternatives);record(13,{'encodings':[f'{x:08X}'for x in fracbits],'exact_rational_matches_binary32_pack':True},2)
    p=S['q15'];sets=p['cache_bytes']//(p['block_bytes']*p['ways']);cache=[[]for _ in range(sets)];counts=[];states=[]
    for _ in range(p['passes']):
        misses=0
        for addr in p['addresses']:
            block=addr//p['block_bytes'];q=cache[block%sets]
            if block in q:q.remove(block)
            else:
                misses+=1
                if len(q)==p['ways']:q.pop(0)
            q.append(block)
        counts.append(misses);states.append([x[:]for x in cache])
    choose(15,tuple(counts),[(5,2),(5,3),(4,2),(4,3)]);record(15,{'misses':counts,'states_LRU_to_MRU':states},12)
    p=S['q16'];offset=p['page_bytes'].bit_length()-1;sets=p['entries']//p['ways'];idxbits=sets.bit_length()-1;tag=p['virtual_bits']-offset-idxbits;group=(p['va']>>offset)&(sets-1)
    choose(16,(tag,group),[(20,1),(18,0),(18,1),(16,1)]);record(16,{'tag_bits':tag,'group':group})
    p=S['q17'];target=p['pc']+p['instruction_bytes']+signed(p['imm_raw'],p['imm_bits'])*p['scale'];choose(17,target,[0xf8,0xfa,0xfe,0x10a]);record(17,{'target':f'{target:04X}'})
    p=S['q18'];offsets={};cursor=0
    for name,size,alignment in p['fields']:
        cursor=((cursor+alignment-1)//alignment)*alignment;offsets[name]=cursor;cursor+=size
    maxalign=max(x[2]for x in p['fields']);size=(cursor+maxalign-1)//maxalign*maxalign
    bb=p['value'].to_bytes(4,'little');addr=p['base']+p['index']*size+offsets['value']+bb.index(p['target_byte'])
    choose(18,addr,[0x1012,0x1014,0x1015,0x1016]);record(18,{'sizeof_record':size,'field_offsets':offsets,'target_addr':f'{addr:04X}'})
    p=S['q19'];assert p['zero_code_reserved'] and p['parallel_between_groups']
    wa=p['groupA_commands'].bit_length();wb=p['groupB_commands'].bit_length()
    width=wa+wb+p['next_address_bits']+p['branch_selector_bits']
    assert (wa,wb,width)==(3,2,15)
    choose(19,width,[13,14,16,15]);record(19,{'group_A_bits':wa,'group_B_bits':wb,'next_address_bits':p['next_address_bits'],'branch_mode_bits':p['branch_selector_bits'],'total_bits':width})
    p=S['q21'];peak=p['clock_hz']*p['bus_bits']/8*p['transfers_per_data_cycle']/1e6;effective=p['words']*(p['bus_bits']/8)/(sum(p[k]for k in ['command_cycles','wait_cycles','data_cycles'])/p['clock_hz'])/1e6
    choose(21,(round(peak,1),round(effective,1)),[(800,457.1),(400,457.1),(800,800),(400,228.6)]);record(21,{'peak_MBps':peak,'effective_MBps':effective})

def safe_sequences(allocation,maximum,available):
    need=[[m-a for m,a in zip(row,al)]for row,al in zip(maximum,allocation)];out=[]
    for perm in itertools.permutations(range(len(need))):
        work=available[:]
        for i in perm:
            if not all(x<=y for x,y in zip(need[i],work)):break
            work=[x+y for x,y in zip(work,allocation[i])]
        else:out.append(perm)
    return out

def tests_os():
    p=S['q25'];remaining=p['bursts'][:];t=0;current=None;completion={};timeline=[]
    while any(remaining):
        ready=[i for i,r in enumerate(remaining)if r and p['arrivals'][i]<=t]
        if not ready:t+=1;continue
        chosen=min(ready,key=lambda i:(remaining[i],0 if i==current else 1,p['arrivals'][i],i))
        current=chosen;timeline.append(chosen);remaining[chosen]-=1;t+=1
        if remaining[chosen]==0:completion[chosen]=t
    waits=[completion[i]-p['arrivals'][i]-p['bursts'][i]for i in range(3)];avg=sum(waits)/3
    choose(25,avg,[1,2,3,6]);record(25,{'waiting':waits,'completion':completion,'average':avg,'unit_timeline':timeline},len(timeline))
    p=S['q26'];out=[];seqs=[]
    assert safe_sequences(p['allocation'],p['maximum'],p['available'])
    for who,request in p['options']:
        a=[r[:]for r in p['allocation']];avail=p['available'][:]
        assert all(request[k]<=avail[k] and request[k]<=p['maximum'][who][k]-a[who][k]for k in range(2))
        a[who]=[x+y for x,y in zip(a[who],request)];avail=[x-y for x,y in zip(avail,request)]
        seq=safe_sequences(a,p['maximum'],avail);out.append(bool(seq));seqs.append(seq)
    assert out==[False,False,True,False];choose(26,out.index(True),[0,1,2,3]);record(26,{'safe_by_option':out,'safe_sequences':seqs},24)
    p=S['q27'];va=p['va'];di=va>>22;ti=(va>>12)&1023;off=va&4095;pte=p['page_table_physical_base']+p['pte_bytes']*ti;physical=p['pfn']*p['page_bytes']+off
    choose(27,(pte,physical),[(0x300003,0x123008),(0x30000c,0x123008),(0x30000c,0x123308),(0x300030,0x123008)]);record(27,{'directory':di,'table_index':ti,'pte_hex':f'{pte:08X}','physical_hex':f'{physical:08X}'})
    p=S['q28'];lru=p['initial_lru'][:];miss=0;history=[]
    for a in p['references']:
        if a in lru:lru.remove(a)
        else:miss+=1;lru.pop(0)
        lru.append(a);history.append(lru[:])
    victim=lru[0];choose(28,(miss,victim),[(2,2),(3,5),(4,2),(3,2)]);record(28,{'misses':miss,'next_victim':victim,'states':history},6)
    p=S['q30'];block=p['offset']//p['block_bytes'];per=p['block_bytes']//p['pointer_bytes'];n=block-p['direct_entries']
    level=0 if n<0 else 1 if n<per else 2
    reads=level+1;choose(30,(level,reads),[(1,2),(2,2),(2,3),(3,4)]);record(30,{'logical_block':block,'index_depth':level,'disk_reads':reads})
    p=S['q31'];above=sorted(x for x in p['requests']if x>=p['start']);below=sorted(x for x in p['requests']if x<p['start']);path=[p['start']]+above
    if below:path+=[p['max_cylinder'],p['min_cylinder']]+below
    distance=sum(abs(a-b)for a,b in zip(path,path[1:]));choose(31,distance,[119,240,318,398]);record(31,{'path':path,'distance':distance})

def tests_network():
    p=S['q33'];tx=[p['packet_bytes']*8/r for r in p['rates_bps']];free=[0.0]*len(tx);history=[]
    for _ in range(p['packet_count']):
        arrived=0.0;times=[]
        for hop,dur in enumerate(tx):
            end=max(arrived,free[hop])+dur;free[hop]=end;arrived=end;times.append(end)
        history.append(times)
    tp=round(history[-1][-1]*1000,8);tm=sum(tx)*p['packet_count']*1000
    choose(33,(tp,tm),[(10,16),(12,12),(12,16),(16,16)]);record(33,{'packet_hop_finish_ms':[[1000*x for x in row]for row in history],'TP_ms':tp,'TM_ms':tm},6)
    p=S['q34'];nyq=2*p['bandwidth_hz']*math.log2(p['symbol_states']);shan=p['bandwidth_hz']*math.log2(1+p['snr_linear']);cap=min(nyq,shan)/1000
    choose(34,cap,[6,12,18,24]);record(34,{'Nyquist_bps':nyq,'Shannon_bps':shan,'upper_kbps':cap})
    p=S['q35'];ports=p['switch_ports'];tables={s:{} for s in ports};edges={}
    for sw,m in ports.items():
        for port,neighbor in m.items():
            if neighbor not in ports:edges[neighbor]=(sw,port)
    hist=[]
    for src,dst in p['frames']:
        sw,inport=edges[src];q=collections.deque([(sw,inport)]);forwarded={}
        while q:
            sw,inport=q.popleft();tables[sw][src]=inport
            out=[tables[sw][dst]]if dst in tables[sw]else list(ports[sw])
            out=[x for x in out if x!=inport];forwarded[sw]=list(map(int,out))
            for port in out:
                neighbor=ports[sw][port]
                if neighbor in ports:
                    reverse=next(k for k,v in ports[neighbor].items()if v==sw);q.append((neighbor,reverse))
        hist.append(forwarded)
    actual=(hist[-1]['S1'],hist[-1]['S2']);choose(35,actual,[([3],[2]),([1,3],[2,3]),([1,3],[2]),([3],[2,3])]);record(35,{'third_frame_ports':hist[-1],'learned_tables':tables,'frames':hist},3)
    p=S['q36'];rx=p['initial_absolute_base'];cache=set();delivered=[]
    for frame in p['receiver_arrival_absolute']:
        assert rx<=frame<rx+p['window']
        cache.add(frame)
        while rx in cache:cache.remove(rx);delivered.append(rx);rx+=1
    tx=p['initial_absolute_base'];acked=set(p['sender_ack_absolute'])
    while tx in acked:tx+=1
    nxt=max(p['sent_absolute'])+1;new=tx+p['window']-nxt
    triple=(tx%p['modulus'],rx%p['modulus'],new)
    choose(36,triple,[(2,2,4),(6,7,0),(7,2,1),(6,2,0)]);record(36,{'window_bases_mod8_and_new':triple,'delivered_mod8':[x%8 for x in delivered],'no_duplicate_delivery':len(set(delivered))==len(delivered)},7)
    prefixes=[('10.40.0.0/16','A'),('10.40.14.0/23','B'),('10.40.8.0/21','C'),('10.40.12.0/22','D')];ip=ipaddress.ip_address('10.40.13.7');matched=[(ipaddress.ip_network(x).prefixlen,hop)for x,hop in prefixes if ip in ipaddress.ip_network(x)];hop=max(matched)[1]
    choose(37,hop,['A','B','C','D']);record(37,{'matching_prefix_lengths':matched,'selected':hop},4)
    p=S['q38'];received=set();nxt=p['rcv_nxt']
    for index in p['arrival_indices'][:p['sample_after_arrivals']]:
        start,length=p['segments'][index];received.update(range(start,start+length))
        while nxt in received:nxt+=1
    empty=p['capacity']-len(received);choose(38,(nxt,empty),[(1401,1600),(1801,1200),(1801,1600),(2201,800)]);record(38,{'ACK_at_T':nxt,'free_buffer':empty,'received_bytes':len(received)},2)
    p=S['q39'];cwnd=p['initial_window_mss'];remaining=p['total_mss'];rounds=[]
    while remaining:
        count=min(cwnd,p['rwnd_mss'],remaining);rounds.append(count);remaining-=count
        cwnd=min(p['threshold_mss'],2*cwnd)if cwnd<p['threshold_mss']else cwnd+1
    ms=len(rounds)*p['rtt_ms'];choose(39,ms,[40,45,50,60]);record(39,{'segments_per_round':rounds,'final_ACK_ms':ms},len(rounds))
    p=S['q40'];rtts=int(not p['tcp_exists'])+int(not p['dns_cached'])+p['html_count']+p['image_count'];choose(40,rtts,[3,4,5,6]);record(40,{'RTTs':rtts,'model':'one persistent nonpipelined HTTP connection; cached DNS'},4)

class CNode(ctypes.Structure):pass
CNode._fields_=[('key',ctypes.c_int),('next',ctypes.POINTER(CNode))]

def c_linked_list(vals):
    if not vals:return None,None
    arr=(CNode*len(vals))()
    for i,v in enumerate(vals):
        arr[i].key=v
        if i+1<len(vals):arr[i].next=ctypes.pointer(arr[i+1])
    return arr,ctypes.pointer(arr[0])

def common_oracle(a,b):
    common=sorted(set(a)&set(b));best=[];run=[]
    for x in common:
        if not run or x==run[-1]+1:run.append(x)
        else:run=[x]
        if len(run)>len(best):best=run[:]
    return (len(best),best[0],best[-1])if best else(0,None,None)

def tests_c():
    compiler=shutil.which('gcc')or shutil.which('cc')
    assert compiler,'C11 compiler is required, not silently skipped'
    with tempfile.TemporaryDirectory(prefix='ai408-check-')as td:
        td=pathlib.Path(td)
        source=(BASE/'reference_q41.c').read_text(encoding='utf-8')+'''\n#include <stdint.h>
#include <limits.h>
_Static_assert(CHAR_BIT==8 && sizeof(int)==4, "Q14 test requires 32-bit int");
void q14_values(int *r, uint32_t *v) { int16_t s=-3; uint16_t u=2; *r=(s<u); *v=s+u; }
'''
        (td/'test.c').write_text(source,encoding='utf-8')
        cp=subprocess.run([compiler,'-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','-fPIC',str(td/'test.c'),'-o',str(td/'test.so')],capture_output=True,text=True)
        assert cp.returncode==0,cp.stderr
        lib=ctypes.CDLL(str(td/'test.so'));f=lib.longestCommonRun;f.argtypes=[ctypes.POINTER(CNode),ctypes.POINTER(CNode),ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_int)];f.restype=ctypes.c_int
        lib.q14_values.argtypes=[ctypes.POINTER(ctypes.c_int),ctypes.POINTER(ctypes.c_uint32)]
        r=ctypes.c_int();v=ctypes.c_uint32();lib.q14_values(ctypes.byref(r),ctypes.byref(v));choose(14,(r.value,v.value),[(0,4294967295),(1,65535),(1,4294967295),(0,65535)]);record(14,{'compiled_C_values':[r.value,v.value],'compiler':pathlib.Path(compiler).name})
        cases=0
        def one(a,b):
            nonlocal cases
            aa,pa=c_linked_list(a);bb,pb=c_linked_list(b);before_a=bytes(aa)if aa is not None else None;before_b=bytes(bb)if bb is not None else None
            lo=ctypes.c_int(123456);hi=ctypes.c_int(654321);length=f(pa,pb,ctypes.byref(lo),ctypes.byref(hi));oracle=common_oracle(a,b)
            assert length==oracle[0],(a,b,length,oracle)
            if length:assert (lo.value,hi.value)==oracle[1:],(a,b,lo.value,hi.value,oracle)
            else:assert(lo.value,hi.value)==(123456,654321)
            assert before_a==(bytes(aa)if aa is not None else None)and before_b==(bytes(bb)if bb is not None else None),'input list mutated'
            cases+=1
        arrays=[list(x)for n in range(5)for x in itertools.combinations_with_replacement(range(-2,3),n)]
        for a in arrays:
            for b in arrays:one(a,b)
        exhaustive=cases;random_cases=10000;rng=random.Random(408202425)
        for _ in range(random_cases):one(sorted(rng.choices(range(-10,11),k=rng.randrange(31))),sorted(rng.choices(range(-10,11),k=rng.randrange(31))))
        for a,b in [([1000000],[1000000]),([-1000000,-999999],[-1000000,-999999]),([-1000000,1000000],[-1000000,1000000]),(S['q41']['a'],S['q41']['b'])]:one(a,b)
        assert common_oracle(S['q41']['a'],S['q41']['b'])==(3,1,3)
        record(41,{'compiled_C_matches_set_oracle':True,'exhaustive_pairs':exhaustive,'random_pairs':random_cases,'boundary_and_example_pairs':4,'input_bytes_unchanged':True,'example':[3,1,3]},cases)

class AVL:
    def __init__(self,k,l=None,r=None):self.k=k;self.l=l;self.r=r

def height(t):return 0 if t is None else 1+max(height(t.l),height(t.r))
def bf(t):return height(t.l)-height(t.r)
def right(t):a=t.l;t.l=a.r;a.r=t;return a
def left(t):a=t.r;t.r=a.l;a.l=t;return a

def balance(t,rot):
    if bf(t)>1:
        if bf(t.l)<0:rot.append((t.k,'LR'));t.l=left(t.l)
        else:rot.append((t.k,'LL'))
        return right(t)
    if bf(t)<-1:
        if bf(t.r)>0:rot.append((t.k,'RL'));t.r=right(t.r)
        else:rot.append((t.k,'RR'))
        return left(t)
    return t

def avl_insert(t,k,rot):
    if t is None:return AVL(k)
    if k<t.k:t.l=avl_insert(t.l,k,rot)
    elif k>t.k:t.r=avl_insert(t.r,k,rot)
    return balance(t,rot)

def avl_delete(t,k,rot):
    if t is None:return None
    if k<t.k:t.l=avl_delete(t.l,k,rot)
    elif k>t.k:t.r=avl_delete(t.r,k,rot)
    else:
        if not t.l:return t.r
        if not t.r:return t.l
        pred=t.l
        while pred.r:pred=pred.r
        t.k=pred.k;t.l=avl_delete(t.l,pred.k,rot)
    return balance(t,rot)

def avl_validate(t,lo=-math.inf,hi=math.inf):
    if not t:return []
    assert lo<t.k<hi and abs(bf(t))<=1
    return avl_validate(t.l,lo,t.k)+[t.k]+avl_validate(t.r,t.k,hi)

def tests_big():
    p=S['q42']
    def build(k):
        if k is None:return None
        a,b=p['children'][str(k)];return AVL(k,build(a),build(b))
    root=build(p['root']);avl_validate(root);rot=[];root=avl_insert(root,p['insert'],rot);avl_validate(root)
    assert rot==[(10,'RL')]
    assert root.k==30 and root.l.k==15 and root.l.l.k==10 and root.l.r.k==20
    dr=[];root=avl_delete(root,p['delete'],dr);keys=avl_validate(root);assert not dr and keys==[10,15,20,30,40,60]
    path=[];cur=root
    while cur:
        path.append(cur.k);cur=cur.l if p['unsuccessful_key']<cur.k else cur.r
    def depths(t,d=1):return[]if not t else[d]+depths(t.l,d+1)+depths(t.r,d+1)
    dd=depths(root);assert path==[30,40,60]and Fraction(sum(dd),len(dd))==Fraction(7,3)
    record(42,{'insert_rotations':rot,'delete_rotations':dr,'final_inorder':keys,'failed_search_path':path,'ASL':'7/3'},2)
    p=S['q43'];sim=pipeline(p['instructions'],p['code_base'],p['initial_registers'],{int(k):v for k,v in p['word_memory'].items()})
    assert sim['cycles']==13 and sim['load_stalls']==1
    assert sim['branches']==[{'index':5,'cycle':8,'taken':True,'target':0x4018}]
    assert(sim['regs'][3],sim['regs'][5],sim['regs'][7])==(5,9,100)
    wb={i:c for i,c,u in sim['retired']};assert wb=={1:5,2:7,3:8,4:9,5:10,7:13}
    period=max(S['machine']['stage_ps'])+S['machine']['register_overhead_ps'];assert period==260
    record(43,{'period_ps':period,'last_WB_cycle':sim['cycles'],'total_ps':period*sim['cycles'],'WB':wb,'branches':sim['branches'],'final_registers':sim['regs']},sim['cycles'])
    p=S['q44'];opcodes=S['machine']['opcodes']
    def encode(ins):
        op,rd,rs,arg=ins
        return (opcodes[op]<<26)|(rd<<23)|(rs<<20)|((arg<<17)if op=='ADD'else(arg&((1<<20)-1)))
    def decode(code):
        op={v:k for k,v in opcodes.items()}[code>>26];rd=(code>>23)&7;rs=(code>>20)&7;arg=((code>>17)&7)if op=='ADD'else signed(code&((1<<20)-1),20)
        if op=='BNZ':assert rd==0
        if op=='ADD':assert(code&((1<<17)-1))==0
        return [op,rd,rs,arg]
    for ins in p['instructions']:assert decode(encode(ins))==ins
    bnz=encode(p['instructions'][-1]);assert bnz==0x105ffffb
    bitstring='000100'+'000'+'101'+format((-5)&((1<<20)-1),'020b');assert int(bitstring,2)==bnz
    def emulate(half=False):
        regs=[0]*8;regs[2]=p['data_base'];regs[5]=p['count'];program=[x[:]for x in p['instructions']]
        if half:
            program[0][0]='LH';program[2][3]=2
            raw=b''.join(x.to_bytes(2,'little',signed=True)for x in[-2,5,-4])
        else:raw=bytes(p['data_bytes'])
        memory={p['data_base']+i:x for i,x in enumerate(raw)};code={p['code_base']+i*4:encode(ins)for i,ins in enumerate(program)};pc=p['code_base'];trace=[]
        while pc in code:
            assert len(trace)<30
            op,rd,rs,arg=decode(code[pc]);trace.append(pc);nxt=pc+4
            if op in('LW','LH'):
                length=4 if op=='LW'else 2;ea=(regs[rs]+arg)&0xffffffff
                v=int.from_bytes(bytes(memory[ea+i]for i in range(length)),'little',signed=op=='LH');regs[rd]=v&0xffffffff
            elif op=='ADD':regs[rd]=(regs[rs]+regs[arg])&0xffffffff
            elif op=='ADDI':regs[rd]=(regs[rs]+arg)&0xffffffff
            elif op=='BNZ'and regs[rs]!=0:nxt=pc+4+4*arg
            regs[0]=0;pc=nxt
        return regs,trace,code
    full,trace,codes=emulate();half,_,halfcode=emulate(True)
    vals=[int.from_bytes(bytes(p['data_bytes'][i:i+4]),'little',signed=True)for i in range(0,12,4)]
    pages=sorted({(p['data_base']+i)//p['page_bytes']for i in range(12)})
    assert vals==[-2,5,-4] and(full[2],full[3],full[5])==(0x2008,0xffffffff,0)
    assert half[3]==0xffffffff and half[2]==0x2002 and halfcode[p['code_base']+16]==bnz
    assert pages==[1,2]
    record(44,{'values':vals,'sum_hex':f'{full[3]:08X}','pointer_hex':f'{full[2]:08X}','pages':pages,'BNZ_machine_code':f'{bnz:08X}','imm20':'FFFFB','full_dynamic_instructions':len(trace),'halfword_version_sum':-1,'halfword_BNZ_unchanged':True},len(trace)+5)


def pipeline_sync(mutant=False):
    p=S['q45'];programs=[x[:]for x in p['programs']]
    if mutant:programs[0][0],programs[0][1]=programs[0][1],programs[0][0]
    start=(0,0,0,0,0,0,2,0,0,1,0,0,-1)
    semidx={'empty':6,'readyB':7,'readyC':8,'dev':9};seen={start};q=collections.deque([start]);dead=[];transitions=0;terminal=0
    while q:
        state=q.popleft();enabled=0
        assert state[9]==int(state[12]==-1)
        for thread in range(3):
            pc=state[2*thread];count=state[2*thread+1]
            if count==p['test_records']:continue
            action=programs[thread][pc];new=list(state)
            if action.startswith('P:'):
                name=action[2:];idx=semidx[name]
                if state[idx]==0:continue
                new[idx]-=1
                if name=='dev':assert state[12]==-1;new[12]=thread
            elif action.startswith('V:'):
                name=action[2:];new[semidx[name]]+=1
                if name=='dev':assert state[12]==thread;new[12]=-1
            else:
                slot=count%p['slots'];phase=state[10+slot]
                expected={'capture':0,'check':1,'archive':2}[action]
                assert phase==expected,(mutant,action,state)
                if action in('capture','archive'):assert state[12]==thread
                new[10+slot]=(phase+1)%3
            new[2*thread]+=1
            if new[2*thread]==len(programs[thread]):new[2*thread]=0;new[2*thread+1]+=1
            assert all(0<=new[x]<=p['slots']for x in [6,7,8])
            ns=tuple(new);enabled+=1;transitions+=1
            if ns not in seen:seen.add(ns);q.append(ns)
        done=all(state[2*t+1]==p['test_records']for t in range(3))
        if done:terminal+=1;assert state[6:12]==(2,0,0,1,0,0)
        elif enabled==0:dead.append(state)
    return {'reachable_states':len(seen),'transitions':transitions,'completed_states':terminal,'deadlocks':len(dead),'deadlock_example':dead[0]if dead else None}

def subscriber_model(records, flawed=False):
    """Finite-state check of one-slot delivery to two named subscribers."""
    p=S['q45']; key='flawed' if flawed else 'correct'
    programs=[]
    for program in p[key+'_programs']:
        actions=[]
        for op in program:
            actions.extend([op+':begin',op+':end'] if op in ('readA','readB') else [op])
        programs.append(actions)
    sems=list(p[key+'_semaphores']); ix={name:i for i,name in enumerate(sems)}
    start=((0,0,0),(0,0,0),tuple(p[key+'_semaphores'].values()),0,(0,0),(0,)*(2*records))
    todo=collections.deque([start]); parents={start:None}; bad=[]; dead=[]; transitions=terminals=0; parallel=False
    def trace(state,last=None):
        out=[] if last is None else [last]
        while parents[state] is not None:
            state,action=parents[state];out.append(action)
        return list(reversed(out))
    while todo:
        state=todo.popleft();pc,done,sem,version,active,reads=state
        parallel |= all(active); enabled=0
        for thread in range(3):
            if done[thread]==records:continue
            op=programs[thread][pc[thread]]
            pcs,dones,sems,acts,hist=list(pc),list(done),list(sem),list(active),list(reads)
            ver,errors=version,[]
            if op.startswith('P:'):
                k=ix[op[2:]]
                if not sems[k]:continue
                sems[k]-=1
            elif op.startswith('V:'):sems[ix[op[2:]]]+=1
            elif op=='write':
                if any(acts) or (version and any(hist[r*records+version-1]!=1 for r in range(2))):
                    errors.append('overwrite before both subscribers finish exactly once')
                ver=dones[0]+1
            else:
                who=0 if op.startswith('readA') else 1
                if op.endswith(':begin'):
                    if ver==0 or ver!=dones[thread]+1:errors.append('wrong or repeated version')
                    if acts[who]:errors.append('overlapping own read')
                    acts[who]=ver
                else:
                    if not acts[who] or acts[who]!=ver:errors.append('slot changed during read')
                    if 1<=acts[who]<=records:hist[who*records+acts[who]-1]+=1
                    acts[who]=0
            pcs[thread]+=1
            if pcs[thread]==len(programs[thread]):pcs[thread]=0;dones[thread]+=1
            nxt=(tuple(pcs),tuple(dones),tuple(sems),ver,tuple(acts),tuple(hist))
            action=f'{"PAB"[thread]}:{op}'
            if errors and not bad:bad.append({'error':errors[0],'trace':trace(state,action)})
            transitions+=1;enabled+=1
            if nxt not in parents:parents[nxt]=(state,action);todo.append(nxt)
        if all(n==records for n in done):
            terminals+=1
            if not flawed:assert reads==(1,)*(2*records) and not any(active) and not any(sem)
        elif enabled==0 and not dead:dead.append({'trace':trace(state),'version':version,'reads':reads})
    return {'records':records,'states':len(parents),'transitions':transitions,'completed_states':terminals,
            'unsafe_witness':bad[:1],'deadlock_witness':dead[:1],'parallel_reads_reachable':parallel}


def cow_model():
    """Independently simulate page mappings, frame owners and COW protection faults."""
    p=S['q46']; names=p['processes']
    frames={row['initial_frame']:{'value':row['initial_value'],'owners':set(names)} for row in p['pages']}
    table={proc:{row['vpn']:row['initial_frame'] for row in p['pages']} for proc in names}
    writeable={proc:{row['vpn']:False for row in p['pages']} for proc in names}
    faults=[];copies=[];trace=[];fresh=p['next_fresh_frame'];middle=None
    for step,action in enumerate(p['operations'],1):
        proc=action['process']
        if action['type']=='exit':
            for vpn,frame in table.pop(proc).items():
                frames[frame]['owners'].remove(proc)
            writeable.pop(proc)
            trace.append({'step':step,'event':'exit','proc':proc})
            continue
        vpn=action['vpn'];frame=table[proc][vpn]
        if not writeable[proc][vpn]:
            faults.append(step)
            if len(frames[frame]['owners'])>1:
                new_frame=fresh;fresh+=1
                frames[new_frame]={'value':frames[frame]['value'],'owners':{proc}}
                frames[frame]['owners'].remove(proc);table[proc][vpn]=new_frame
                copies.append({'step':step,'source':frame,'new':new_frame,'vpn':vpn,'proc':proc})
                frame=new_frame
            writeable[proc][vpn]=True
        frames[frame]['value']=action['value']
        trace.append({'step':step,'proc':proc,'vpn':vpn,'frame':frame,'value':action['value']})
        if step==3:
            middle={name:[frames[table[name][row['vpn']]]['value'] for row in p['pages']] for name in names}
            middle_frames={name:[table[name][row['vpn']] for row in p['pages']] for name in names}
    final_parent=[frames[table['P'][row['vpn']]]['value'] for row in p['pages']]
    assert faults==[1,2,3,5],faults
    assert copies==[{'step':1,'source':2,'new':9,'vpn':0,'proc':'C'},
                    {'step':3,'source':5,'new':10,'vpn':1,'proc':'P'}],copies
    assert middle=={'P':[12,21,30],'C':[11,20,30]},middle
    assert middle_frames=={'P':[2,10,8],'C':[9,5,8]},middle_frames
    assert final_parent==[12,21,31] and table['P'][2]==8
    assert frames[8]['owners']=={'P'} and all(writeable['P'].values())
    return {'write_protection_fault_steps':faults,'physical_page_copies':copies,
            'values_before_child_exit':middle,'frames_before_child_exit':middle_frames,
            'values_after_parent_final_write':final_parent,'last_write_frame':table['P'][2],
            'last_write_causes_fault_but_no_copy':5 in faults and not any(c['step']==5 for c in copies),
            'simulation_events':trace}


def routing_model():
    """Shortest paths, mixed forwarding states, TTL drops and all update orders."""
    p=S['q47'];nodes=p['nodes'];dst=p['destination']
    def compute(which):
        dist={n:float('inf') for n in nodes};dist[dst]=0
        for _ in range(len(nodes)):
            modified=False
            for e in p['edges']:
                a,b,w=e['u'],e['v'],e[which+'_cost']
                if dist[a]>dist[b]+w:dist[a]=dist[b]+w;modified=True
                if dist[b]>dist[a]+w:dist[b]=dist[a]+w;modified=True
            if not modified:break
        nxt={}
        for a in nodes:
            if a==dst:continue
            options=[]
            for e in p['edges']:
                v=e['v'] if e['u']==a else e['u'] if e['v']==a else None
                if v is not None:options.append((e[which+'_cost']+dist[v],v))
            best=min(x[0] for x in options)
            winners=[v for cost,v in options if cost==best]
            assert len(winners)==1,(which,a,options)
            nxt[a]=winners[0]
            assert dist[a]==best,(which,a,best,dist)
        return dist,nxt
    olddist,oldnext=compute('old');newdist,newnext=compute('new')
    assert oldnext==p['expected_old_next'] and newnext==p['expected_new_next']
    assert newdist=={'R1':5,'R2':6,'R3':7,'R4':0},newdist
    actors=[x for x in nodes if x!=dst]
    def cycle(tab):
        for origin in actors:
            seen=set();u=origin
            while u!=dst:
                if u in seen:return {'origin':origin,'at':u}
                seen.add(u);u=tab.get(u)
                assert u is not None
        return None
    safe=[];unsafe_examples=[]
    for order in itertools.permutations(actors):
        tab=dict(oldnext);bad=None
        for u in order:
            tab[u]=newnext[u]
            bad=cycle(tab)
            if bad:
                unsafe_examples.append({'order':list(order),'first_bad_update':u,'cycle':bad})
                break
        if not bad:safe.append(list(order))
    assert safe==[p['expected_safe_update_order']],safe
    only=dict(oldnext)
    only[p['first_updated']]=newnext[p['first_updated']]
    ttl=p['initial_ttl'];u=p['source_router'];path=[];drop=None;detail=[]
    while ttl>0:
        path.append(u);ttl-=1
        detail.append({'router':u,'ttl_after_decrement':ttl})
        if ttl==0:drop=u;break
        u=only[u]
        assert len(path)<=10
    assert path==['R1','R2','R1','R2'] and drop=='R2'
    assert [x['ttl_after_decrement'] for x in detail]==[3,2,1,0]
    return {'old_distances':olddist,'old_next_hops':oldnext,'new_distances':newdist,
            'new_next_hops':newnext,'transient_packet_path':path,
            'ttl_trace':detail,'discarded_by':drop,'safe_orders':safe,
            'unsafe_orders_checked':unsafe_examples,'number_of_order_permutations':len(safe)+len(unsafe_examples)}


def tests_final():
    good=[subscriber_model(k) for k in range(1,5)]
    bad=subscriber_model(3,flawed=True)
    assert all(x['completed_states'] and not x['unsafe_witness'] and not x['deadlock_witness'] for x in good)
    assert all(x['parallel_reads_reachable'] for x in good)
    assert bad['unsafe_witness'] and bad['deadlock_witness']
    record(45,{'correct_models':good,'shared_ready_counterexample':bad,
               'scope':'1-4 records; general reasoning remains in solutions.md'},
           sum(x['states'] for x in good)+bad['states'])
    cow=cow_model()
    record(46,cow,len(S['q46']['operations']))
    routes=routing_model()
    record(47,routes,routes['number_of_order_permutations']+2*len(S['q47']['nodes']))

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--json',type=pathlib.Path);args=ap.parse_args()
    structural=structure()
    tests_ds();tests_co();tests_os();tests_network();tests_c();tests_big();tests_final()
    manual=[n for n in range(1,48)if str(n)not in RESULTS]
    for n in manual:record(n,'Definition/semantics and option reasoning checked in solutions.md; not algorithmically certified',0,'author-editorial-proof-only')
    results={str(n):RESULTS[str(n)]for n in range(1,48)}
    report={'status':'pass','scope':'author-run executable cross-check; not independent expert/psychometric certification','structural':structural,'computational_questions':[int(k)for k,v in results.items()if v['mode']=='executable-cross-check'],'editorial_only_questions':manual,'constraint_only_questions':[],'results':results,'limitations':['finite enumeration is not a general proof','not all natural-language option semantics can be established by code','no candidate-response data or independent expert blind review','difficulty equivalence to 2024/2025 remains an editorial target']}
    print('[verify] PASS: 47 question sections, 160 choices, 47 explanations, 7 rubrics, 150 points')
    print(f'[verify] PASS: 15 reproducible SVGs (14 student, 1 teacher-only)')
    print(f'[verify] computational cross-checks: {len(report["computational_questions"])} questions; editorial-only: {manual}; Q46 and Q47 covered by new executable models')
    print(f'[verify] Q41 compiled C: {RESULTS["41"]["checks_or_cases"]} cases')
    print(f'[verify] Q45: subscriber fan-out models explored; flawed shared-ready counterexample found')
    print("[verify] Q46: 4 write-protection faults, 2 page copies; refcount=1 upgrades in place")
    print("[verify] Q47: 6 update orders enumerated, exactly one loop-free; TTL=4 drops at R2")
    print('[verify] Independent expert review and timed pilot: NOT PERFORMED')
    if args.json:
        args.json.parent.mkdir(parents=True,exist_ok=True)
        args.json.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
if __name__=='__main__':main()
