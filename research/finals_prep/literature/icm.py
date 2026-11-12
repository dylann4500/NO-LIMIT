from functools import lru_cache
P=(50,30,20)
def icm(stacks):
    stacks=tuple(stacks)
    @lru_cache(None)
    def f(rem,place):
        # rem: tuple of (idx,stack); returns dict idx->equity
        out={i:0.0 for i,_ in rem}
        if place>=len(P) or not rem: return out
        tot=sum(s for _,s in rem)
        for k,(i,s) in enumerate(rem):
            if s<=0: continue
            p=s/tot
            out[i]+=p*P[place]
            sub=f(rem[:k]+rem[k+1:],place+1)
            for j,v in sub.items(): out[j]+=p*v
        return out
    d=f(tuple((i,s) for i,s in enumerate(stacks) if s>0),0)
    return [d.get(i,0.0) for i in range(len(stacks))]
# 8 equal stacks; collision between seat0 and seat1
base=icm([2000]*8)
after=icm([4000,0]+[2000]*6)
print("8 equal:",round(base[0],3),"winner",round(after[0],3),"bystander",round(after[2],3),"gain",round(after[2]-base[2],3))
print("call threshold hand1:", round(base[0]/after[0],4))
for n in (7,6,5,4,3):
    b=icm([16000/n]*n); a=icm([2*16000/n,0]+[16000/n]*(n-2))
    print(n,"equal: each",round(b[0],2),"winner",round(a[0],2),"bystander gain",round(a[2]-b[2],2),"call needs",round(b[0]/a[0],3), "pair loses jointly",round(2*b[0]-a[0],2))
# shove EV vs fold: stealing blinds value at equal stacks 8 players, blinds 100/200 (10bb)
b=icm([2000]*8); s=icm([2300,1900,1800]+[2000]*5)
print("steal 1.5bb at 10bb: ",round(s[0]-b[0],3),"pts; bust costs",round(b[0],2))
print("--- tight survivor with a short stack")
for st in ([1500]+[3625]*4, [1000]+[3750]*4, [1500]+[14500/3]*3, [1000]+[5000]*3, [2000]+[14000/3]*3):
    print([round(x) for x in st], "short stack equity", round(icm(st)[0],2))
print("--- 3 left, correct bust value 20")
b=icm([16000/3]*3)[0]; a=icm([32000/3,0,16000/3])[0]
print("call needs", round((b-20)/(a-20),3))
