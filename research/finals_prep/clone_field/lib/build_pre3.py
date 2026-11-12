"""Rank every 3-card starting hand class by simulation: equity against one random 3-card hand
when both keep their best two cards (hindsight keep). Writes pre3.json: class -> percentile."""
import itertools, json, multiprocessing, random, sys
import eval7
import clonecore as cc

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1500


def eq(args):
    key, rep = args
    rng = random.Random(key)
    ev = eval7.evaluate
    mine = [cc.CARD[c] for c in rep]
    rest = [c for c in cc.DECK if c not in mine]
    w = 0
    for _ in range(N):
        s = rng.sample(rest, 8)
        b = s[3:]
        a = max(ev(b + [mine[0], mine[1]]), ev(b + [mine[0], mine[2]]), ev(b + [mine[1], mine[2]]))
        o = max(ev(b + [s[0], s[1]]), ev(b + [s[0], s[2]]), ev(b + [s[1], s[2]]))
        w += 2 if a > o else 1 if a == o else 0
    return key, w / (2 * N)


if __name__ == "__main__":
    names = list(cc.CARD)
    cnt, rep = {}, {}
    for h in itertools.combinations(names, 3):
        k = cc.pre_key(h)
        cnt[k] = cnt.get(k, 0) + 1
        rep.setdefault(k, h)
    with multiprocessing.Pool(10) as p:
        res = dict(p.map(eq, list(rep.items()), chunksize=20))
    order = sorted(res, key=res.get)
    tot = sum(cnt.values())
    acc, out = 0, {}
    for k in order:
        out[k] = round((acc + cnt[k] / 2) / tot, 5)
        acc += cnt[k]
    json.dump(out, open(cc.HERE + "/pre3.json", "w"))
    json.dump({k: round(v, 4) for k, v in res.items()}, open(cc.HERE + "/pre3_equity.json", "w"))
    print(len(out), "classes; best", order[-5:], "worst", order[:5])
