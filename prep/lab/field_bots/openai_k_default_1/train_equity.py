"""Train a tiny CPU equity surrogate using synthetic deals, never simulator data.

Optional development tool; the playing agent only loads the resulting npz.
"""
import os
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"

import argparse
import json
import math
import random
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "..", "..", "fake_sdk"))
import agent as bot


def generate(n):
    rng = random.Random(930571)
    deck = list(bot._CARDS.values())
    rows, ys, cats = [], [], []
    start = time.monotonic()
    for i in range(n):
        length = rng.choice((3, 3, 4, 4, 5, 5, 5))
        kind = rng.random()
        if kind < 0.15:
            # Enrich sets, straights, flushes and full houses for value decisions.
            while True:
                cc = rng.sample(deck, length + 2)
                if bot.eval7.evaluate(cc) >> 24 >= 3:
                    break
        elif kind < 0.32:
            rank = rng.choice(bot.RANKS)
            hero = [bot._CARDS[rank + s] for s in rng.sample("cdhs", 2)]
            cc = hero + rng.sample([c for c in deck if c not in hero], length)
        else:
            cc = rng.sample(deck, length + 2)
        hero, board = cc[:2], cc[2:]
        nobs = rng.randint(8, 80)
        pfr = rng.randint(0, int(nobs * 0.50))
        vpip = rng.randint(pfr, nobs)
        st = [0] * 15
        st[0], st[1], st[2] = nobs, vpip, pfr
        st[4], st[5], st[6], st[7] = [rng.randint(0, 45) for _ in range(4)]
        pfcode = rng.choices([0, 1, 2], [0.10, 0.36, 0.54])[0]
        hp = [pfcode, (2 if rng.random() < 0.13 else 1) if pfcode == 2 else 0,
              0, 1 if pfcode == 1 else 0, [0, 0, 0], [0., 0., 0.]]
        for street in range(length - 2):
            hp[4][street] = rng.choices([0, 1, 2, 4, 8, 6, 12], [.12, .13, .25, .25, .14, .08, .03])[0]
            hp[5][street] = min(2.5, math.exp(rng.uniform(-2.5, 0.8)))
        m = {"s": {0: st}, "h": {"p": {0: hp}}}
        prof = bot._profile(st, hp)
        idx = bot._range_index(bot._prior_fraction(0, m))
        features = bot._equity_features(hero, board, idx, hp, prof)
        assert len(features) == 231, len(features)
        y = bot._posterior_eq(None, m, 0, hero, board, limit=224, rollouts=1536)
        rows.append(features)
        ys.append(y)
        cats.append(bot.eval7.evaluate(cc) >> 24)
        if (i + 1) % 5000 == 0:
            print("generated", i + 1, "seconds", round(time.monotonic() - start, 1), flush=True)
    return np.asarray(rows, dtype=np.float32), np.asarray(ys, dtype=np.float32).reshape(-1, 1), np.asarray(cats)


def metrics(y, pred, cats):
    err = (pred - y).ravel()
    return {"rmse": float(np.sqrt(np.mean(err ** 2))), "mae": float(np.mean(np.abs(err))),
            "p95_absolute_error": float(np.quantile(np.abs(err), .95)),
            "rmse_by_category": {str(c): float(np.sqrt(np.mean(err[cats == c] ** 2)))
                                 for c in sorted(set(cats))}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=240000)
    ap.add_argument("--epochs", type=int, default=70)
    ap.add_argument("--data", default="/tmp/openai_k_equity_training_v2.npz")
    args = ap.parse_args()
    if os.path.exists(args.data):
        with np.load(args.data) as d:
            x, y, cats = d["x"], d["y"], d["cats"]
    else:
        x, y, cats = generate(args.samples)
        np.savez_compressed(args.data, x=x, y=y, cats=cats)
    if x.shape[1] != 231:
        raise ValueError("Training cache has an obsolete feature schema; choose a new --data path")
    rng = np.random.default_rng(4831)
    perm = rng.permutation(len(x))
    x, y, cats = x[perm], y[perm], cats[perm]
    nval = len(x) // 8
    mean = x[nval:].mean(axis=0)
    scale = 1.0 / np.maximum(x[nval:].std(axis=0), .10)
    x = np.asarray((x - mean) * scale, order="C", dtype=np.float32)
    xv, yv, cv = x[:nval], y[:nval], cats[:nval]
    xt, yt = x[nval:], y[nval:]
    dims = [x.shape[1], 192, 96, 1]
    params = []
    for a, b in zip(dims, dims[1:]):
        params.extend([(rng.normal(size=(a, b)) * math.sqrt(1.5 / a)).astype(np.float32),
                       np.zeros(b, dtype=np.float32)])
    first = [np.zeros_like(p) for p in params]
    second = [np.zeros_like(p) for p in params]

    def predict(xx):
        a = np.maximum(xx @ params[0] + params[1], 0)
        b = np.maximum(a @ params[2] + params[3], 0)
        return 1 / (1 + np.exp(-np.clip(b @ params[4] + params[5], -20, 20)))

    best = float("inf")
    step = 0
    began = time.monotonic()
    for epoch in range(args.epochs):
        lr = 0.0014 * (0.25 + 0.75 * (1 - epoch / args.epochs))
        order = rng.permutation(len(xt))
        for start in range(0, len(xt), 1024):
            ids = order[start:start + 1024]
            xb, yb = xt[ids], yt[ids]
            a = np.maximum(xb @ params[0] + params[1], 0)
            b = np.maximum(a @ params[2] + params[3], 0)
            pred = 1 / (1 + np.exp(-np.clip(b @ params[4] + params[5], -20, 20)))
            dz = (pred - yb) * pred * (1 - pred) * (2.0 / len(xb))
            dw2, db2 = b.T @ dz, dz.sum(axis=0)
            dz1 = (dz @ params[4].T) * (b > 0)
            dw1, db1 = a.T @ dz1, dz1.sum(axis=0)
            dz0 = (dz1 @ params[2].T) * (a > 0)
            dw0, db0 = xb.T @ dz0, dz0.sum(axis=0)
            grads = [dw0, db0, dw1, db1, dw2, db2]
            step += 1
            for j, (p, g) in enumerate(zip(params, grads)):
                if j % 2 == 0:
                    g += 0.000006 * p
                first[j] *= .9
                first[j] += .1 * g
                second[j] *= .999
                second[j] += .001 * g * g
                p -= lr * (first[j] / (1 - .9 ** step)) / (np.sqrt(second[j] / (1 - .999 ** step)) + 1e-8)
        pred = predict(xv)
        report = metrics(yv, pred, cv)
        print("epoch", epoch + 1, "rmse", round(report["rmse"], 5), "mae", round(report["mae"], 5),
              "seconds", round(time.monotonic() - began, 1), flush=True)
        if report["rmse"] < best:
            best = report["rmse"]
            model = {"mean": mean, "scale": scale}
            for j in range(3):
                model["w" + str(j)] = params[j * 2]
                model["b" + str(j)] = params[j * 2 + 1]
            np.savez(os.path.join(ROOT, "equity_model.npz"), **model)
            report.update(samples=len(x), validation_samples=nval, epoch=epoch + 1,
                          layers=dims, seed=930571, generated_from="synthetic deals and the native range model")
            with open(os.path.join(ROOT, "training_report.json"), "w") as f:
                json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
