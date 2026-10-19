#!/usr/bin/env python3
"""Download open building footprints for the user-confirmed Don Thaen polygon.
The generated dataset is a draft, not a household census.
"""
import json
import subprocess
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from shapely.geometry import shape, mapping

ROOT=Path(__file__).resolve().parents[1]
BOUNDARY=ROOT/"data/don-thaen-boundary.geojson"
OUTPUT=ROOT/"data/don-thaen-buildings.geojson"
boundary=json.loads(BOUNDARY.read_text(encoding="utf-8"))["features"][0]
area=shape(boundary["geometry"])
minlon,minlat,maxlon,maxlat=area.bounds

with tempfile.TemporaryDirectory() as temp:
    raw=Path(temp)/"buildings.geojson"
    args=["overturemaps","download","--type","building","--bbox",
          f"{minlon},{minlat},{maxlon},{maxlat}","-f","geojson","-o",str(raw)]
    subprocess.run(args,check=True,timeout=600)
    result=json.loads(raw.read_text(encoding="utf-8"))
    selected=[]
    seen=set()
    for i,feat in enumerate(result.get("features",[])):
        try:
            poly=shape(feat["geometry"])
            if poly.is_empty or not poly.is_valid or not poly.intersects(area):
                continue
            fid=feat.get("id") or feat.get("properties",{}).get("id") or f"feature-{i}"
            if fid in seen: continue
            seen.add(fid)
            # Do not clip to village boundary: preserve full building outline.
            selected.append({"type":"Feature","properties":{
                "id":str(fid),
                "building_source":"Overture Maps",
                "source_type":"building",
                "needs_field_verification":True
            },"geometry":mapping(poly)})
        except Exception:
            continue
    if not selected:
        raise RuntimeError("No buildings returned for this polygon: preserve any existing output")
    out={"type":"FeatureCollection","metadata":{
        "dataset":"Overture Maps buildings",
        "downloaded_at_utc":datetime.now(timezone.utc).isoformat(),
        "count":len(selected),
        "note":"Building footprints only; not verified homes or households."
    },"features":selected}
    OUTPUT.parent.mkdir(exist_ok=True,parents=True)
    OUTPUT.write_text(json.dumps(out,ensure_ascii=False,separators=(",",":")),encoding="utf-8")
    print(f"Wrote {len(selected)} building footprints to {OUTPUT}")
