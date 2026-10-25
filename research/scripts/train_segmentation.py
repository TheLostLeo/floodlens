#!/usr/bin/env python3
"""Train research-only pixel water classifiers on frozen event splits."""
from __future__ import annotations

import argparse, csv, json, random, sys, time
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "src"))
from floodlens_research.segmentation import (add_counts, confusion, load_split,
    pixel_features, portable_path, read_chip, scores, select_threshold,
    validate_assignments)


def load_rows(size: int):
    with (ROOT / "data/research/derived/manifest.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assignments = load_split(ROOT / "data/research/derived/event_split.json")
    rows = [r for r in rows if str(r["event_id"]) in assignments]
    validate_assignments(rows, assignments)
    loaded = []
    for row in rows:
        image, label = read_chip(portable_path(row["s1_path"], ROOT), portable_path(row["label_path"], ROOT), size)
        loaded.append((row, assignments[str(row["event_id"])], image, label))
    return loaded


def normalizer(data):
    pixels = np.concatenate([image.reshape(2, -1).T for _, split, image, _ in data if split == "train"])
    mean = pixels.mean(axis=0).astype(np.float32)
    std = np.maximum(pixels.std(axis=0), 1e-5).astype(np.float32)
    return mean, std


def summarize(data, predictions, threshold):
    rows, groups = [], {}
    for (row, split, _, truth), probability in zip(data, predictions):
        counts = confusion(truth, probability >= threshold)
        metric = {**counts, **scores(counts)}
        rows.append({"sample_id": row["sample_id"], "event_id": row["event_id"], "event_name": row["event_name"], "split": split, **metric})
        groups.setdefault((split, row["event_name"]), []).append(counts)
    events = [{"split": k[0], "event_name": k[1], **(c := add_counts(v)), **scores(c)} for k, v in groups.items()]
    split_metrics = {}
    for split in ("train", "validation", "test"):
        c = add_counts(confusion(d[3], p >= threshold) for d, p in zip(data, predictions) if d[1] == split)
        split_metrics[split] = {**c, **scores(c)}
    return rows, events, split_metrics


def train_trees(data, seed, max_pixels):
    from sklearn.ensemble import ExtraTreesClassifier
    rng = np.random.default_rng(seed); xs=[]; ys=[]
    train = [d for d in data if d[1] == "train"]
    per_chip = max(100, max_pixels // len(train))
    for _, _, image, label in train:
        features = pixel_features(image).reshape(-1, 5); target=label.ravel(); valid=np.flatnonzero(target >= 0)
        chosen=rng.choice(valid, min(per_chip, len(valid)), replace=False)
        xs.append(features[chosen]); ys.append(target[chosen])
    model=ExtraTreesClassifier(n_estimators=60, max_depth=20, min_samples_leaf=3, n_jobs=-1, random_state=seed, class_weight="balanced")
    model.fit(np.concatenate(xs), np.concatenate(ys))
    return model, [model.predict_proba(pixel_features(d[2]).reshape(-1, 5))[:,1].reshape(d[3].shape).astype(np.float32) for d in data]


def train_unet(data, seed, epochs, mean, std):
    import torch
    from torch import nn
    torch.manual_seed(seed); random.seed(seed)
    class Block(nn.Module):
        def __init__(self, a,b): super().__init__(); self.net=nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.ReLU())
        def forward(self,x): return self.net(x)
    class UNet(nn.Module):
        def __init__(self):
            super().__init__(); self.a=Block(2,12); self.b=Block(12,24); self.pool=nn.MaxPool2d(2); self.up=nn.ConvTranspose2d(24,12,2,2); self.c=Block(24,12); self.out=nn.Conv2d(12,1,1)
        def forward(self,x): a=self.a(x); b=self.b(self.pool(a)); return self.out(self.c(torch.cat((a,self.up(b)),1)))
    model=UNet(); opt=torch.optim.Adam(model.parameters(),lr=1e-3); loss_fn=nn.BCEWithLogitsLoss(pos_weight=torch.tensor([2.0]))
    train=[d for d in data if d[1]=="train"]
    for _ in range(epochs):
        random.shuffle(train); model.train()
        for _,_,image,label in train:
            x=torch.from_numpy(((image-mean[:,None,None])/std[:,None,None])[None]); y=torch.from_numpy((label==1).astype(np.float32)[None,None]); mask=torch.from_numpy((label>=0).astype(np.float32)[None,None])
            opt.zero_grad(); raw=model(x); losses=torch.nn.functional.binary_cross_entropy_with_logits(raw,y,reduction="none",pos_weight=torch.tensor([2.0])); loss=(losses*mask).sum()/mask.sum().clamp_min(1); loss.backward(); opt.step()
    model.eval(); predictions=[]
    with torch.no_grad():
        for _,_,image, _ in data:
            x=torch.from_numpy(((image-mean[:,None,None])/std[:,None,None])[None]); predictions.append(torch.sigmoid(model(x))[0,0].numpy().astype(np.float32))
    return model, predictions


def main():
    parser=argparse.ArgumentParser(); parser.add_argument("--size",type=int,default=64); parser.add_argument("--epochs",type=int,default=12); parser.add_argument("--seed",type=int,default=42); parser.add_argument("--max-tree-pixels",type=int,default=120000); args=parser.parse_args()
    started=time.time(); data=load_rows(args.size); mean,std=normalizer(data)
    tree, tree_pred=train_trees(data,args.seed,args.max_tree_pixels)
    unet, unet_pred=train_unet(data,args.seed,args.epochs,mean,std)
    out=ROOT/"research/artifacts"/"segmentation-latest"; out.mkdir(parents=True,exist_ok=True)
    import joblib, torch
    joblib.dump(tree,out/"extra_trees.joblib"); torch.save(unet.state_dict(),out/"unet.pt")
    np.savez_compressed(out/"predictions.npz", **{f"tree__{d[0]['sample_id']}":p for d,p in zip(data,tree_pred)}, **{f"unet__{d[0]['sample_id']}":p for d,p in zip(data,unet_pred)})
    report={"status":"completed","task":"observed-water segmentation research; not forecasting","resolution":args.size,"epochs":args.epochs,"seed":args.seed,"normalization":{"mean":mean.tolist(),"std":std.tolist()},"models":{},"elapsed_seconds":round(time.time()-started,2)}
    for name,preds in (("extra_trees",tree_pred),("unet",unet_pred)):
        val=[(d[3],p) for d,p in zip(data,preds) if d[1]=="validation"]; threshold=select_threshold([x[0] for x in val],[x[1] for x in val]); chips,events,splits=summarize(data,preds,threshold); report["models"][name]={"threshold":threshold,"splits":splits,"events":events,"chips":chips}
    (out/"metrics.json").write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps({"artifact":str(out),"elapsed_seconds":report["elapsed_seconds"],"models":{k:v["splits"]["test"] for k,v in report["models"].items()}},indent=2))
if __name__=="__main__": main()
