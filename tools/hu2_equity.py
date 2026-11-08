"""Build-time: heads-up hold'em equity of each 169 class vs a random hand (eval7 MC). Prints a JSON dict."""
import json, multiprocessing as mp, os, sys
import eval7
R = "23456789TJQKA"
def classes():
    out = []
    for i in range(13):
        for j in range(i, 13):
            hi, lo = R[j], R[i]
            if i == j: out.append((hi + lo, hi + "s", lo + "h"))
            else:
                out.append((hi + lo + "s", hi + "s", lo + "s"))
                out.append((hi + lo + "o", hi + "s", lo + "h"))
    return out
RAND = None
def eq(args):
    name, a, b = args
    rng = eval7.HandRange("22+,A2s+,K2s+,Q2s+,J2s+,T2s+,92s+,82s+,72s+,62s+,52s+,42s+,32s,A2o+,K2o+,Q2o+,J2o+,T2o+,92o+,82o+,72o+,62o+,52o+,42o+,32o")
    return name, round(eval7.py_hand_vs_range_monte_carlo([eval7.Card(a), eval7.Card(b)], rng, [], int(sys.argv[1]) if len(sys.argv) > 1 else 40000), 4)
if __name__ == "__main__":
    with mp.Pool(os.cpu_count()) as p:
        d = dict(p.map(eq, classes()))
    print(json.dumps(d, separators=(",", ":")))
