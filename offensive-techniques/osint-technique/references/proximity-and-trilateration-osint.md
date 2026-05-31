# Proximity and Trilateration OSINT

Location inference from apps and services that expose **distance** or **proximity** signals rather than coordinates. Targets the family of "near me" features (dating apps, social discovery, fitness/run-route apps, family/friend trackers, BLE-based social proximity, marketplace radius filters) where the platform deliberately hides exact coordinates but leaks enough geometry to reconstruct them.

## When this applies

Strong signal:
- Distance shown in km/mi with one-decimal precision (most dating apps).
- "Within X meters" badges (proximity beacons, fitness apps).
- Heatmaps with low anonymization (older fitness exports — Strava 2018 base bases incident).
- Search radius filters that you can shrink and re-query.
- Anything where you can change your own observer location and re-poll.

Weak / unusable:
- Server returns only "online nearby" with no distance.
- Distance jittered with cryptographic noise > app radius (rare in practice).
- One-shot distances with no re-poll (need ≥3 independent samples).

## Core geometry

Each observation = a circle centered on your observer point with radius = reported distance. The target lies on the intersection.

- **2 circles** → two candidate points (ambiguity).
- **3+ circles, well-spread** → unique solution under noise.
- **3+ circles, collinear observers** → degenerate; high GDOP, large error.

**Geometric Dilution of Precision (GDOP)** dominates result quality. Angular spread of observer points around the target matters more than raw count. Three observers at 120° around target ≫ ten observers in a line.

## Quantization noise floor

Most apps round distance to 1 decimal km → quantization step Δ = 100 m. Uniform-quantization standard deviation:

$$\sigma = \frac{\Delta}{\sqrt{12}} \approx 28.9\ \text{m}$$

This is the **theoretical lower bound** per measurement, independent of sample count. With well-spread observers, weighted LS converges to roughly $\sigma / \sqrt{N \cdot \text{GDOP-factor}}$ — typical practical floor ~10–30 m in a good configuration.

## Weighted least-squares fit

For observer points $(x_i, y_i)$ with measured distances $d_i$, minimize:

$$\sum_i w_i \left( \sqrt{(x - x_i)^2 + (y - y_i)^2} - d_i \right)^2$$

Weight $w_i = 1 / \sigma_i^2$. Use `scipy.optimize.least_squares` with Levenberg-Marquardt; seed initial guess as the centroid of observer points or the intersection of two best-conditioned circles.

Minimal Python:
```python
import numpy as np
from scipy.optimize import least_squares

def residuals(p, obs, dists, w):
    return w * (np.linalg.norm(obs - p, axis=1) - dists)

x0 = obs.mean(axis=0)
sol = least_squares(residuals, x0, args=(obs, dists, weights))
estimated_xy = sol.x
```

Work in a local projected CRS (UTM zone of target area) — never raw lat/lon — to keep distances Euclidean.

## Observer-placement strategy

To minimize GDOP without burning queries:

1. Drop first observer roughly where the target is suspected.
2. Pick second observer 1–3 km away in a direction that brackets the first circle.
3. Pick third observer ~120° from the line connecting the first two.
4. Validate: any three should give residuals near σ; if residuals ≫ σ, target moved or one observer is bad.

Avoid clustered observers — adding observers within the same neighborhood does not reduce uncertainty meaningfully.

## Re-poll discipline (live targets move)

A walking person moves ~80 m/min; a driving target moves >1 km/min. Treat measurement set as **simultaneous within target's coherence time**:

- Burst all observer queries in <60 s for pedestrians.
- For non-simultaneous samples, weight by recency or drop stale circles.
- A target oscillating between two locations creates two clusters in the solution space — use RANSAC, not LS averaging, to separate.

## RANSAC for behavioral clustering

Repeated observations over days/weeks rarely converge to one point because real people have routines (home, work, gym, partner). Naive averaging produces nonsense (somewhere between all the locations).

Workflow:
1. Collect $N$ trilateration solutions across multiple sessions, each tagged with weekday + time-of-day.
2. Run DBSCAN or RANSAC (`sklearn.cluster.DBSCAN`, `eps ≈ 150 m`, `min_samples ≈ 3`).
3. Label clusters by temporal profile:
   - 22:00–07:00 weekdays + weekends → **home** candidate.
   - 09:00–18:00 weekdays only → **work** candidate.
   - Recurring 18:00–20:00 weekday → **gym / regular activity**.
   - Sporadic clusters → social spots, partner home, family.
4. Confidence = (#samples in cluster) × (1 / σ_cluster) × temporal-consistency-score.

## Mosaic closure (photo → building → window)

Trilateration narrows to a zone (~50–500 m radius). The final mile is **content-based** OSINT against profile media:

| Signal | Tool / source | Closes to |
|--------|---------------|-----------|
| Skyline / known landmarks visible from window | Google Earth Pro, PeakVisor | Specific building face |
| Sunset/sunrise direction & angle in photo | SunCalc, PhotoPills, suncalc.org | Window orientation (N/S/E/W) + approximate floor |
| Shadow length + timestamp | SunCalc + EXIF time | Date confirmation, latitude check |
| Interior furniture in window reflection | Reverse image (IKEA, Wayfair) | Apartment type / class |
| Tile, parquet, mouldings | Country / decade fingerprint | Building era |
| View of unique structure (crane, hoarding, signage) | Street View time machine, Mapillary | Exact street segment + side |
| Visible street name, bus stop ID, license plate fragment | OSM, transit operator GTFS | Specific point |

Sun orientation deserves emphasis: a photo at known local time + visible sun position fixes window bearing within ~10°, often enough to eliminate all but one face of a candidate building.

## Defensive countermeasures and why they fail

| Defense | Bypass |
|---------|--------|
| Round distance to 1 km | More observers, longer campaign; floor moves to ~290 m |
| Add fixed Gaussian noise σ | Average over N samples → σ/√N; rejoin trilateration once σ small enough |
| Snap to grid | Grid cell becomes the precision floor; combine with photo-based closure |
| Hide distance entirely | Behavioral OSINT only (posting times, photo backgrounds, mutual contacts) |
| App randomizes observer's reported location | Use multiple accounts from different devices to verify |

Most platforms ship one defense layer; the technique stack defeats each in isolation.

## Operational and ethical scope

This methodology is **only legitimate** for:
- Authorized red team / social engineering with written scope and consent for the target organization's personnel.
- Defensive research disclosing a platform vulnerability with vendor coordination.
- Investigative journalism with editorial and legal review.
- Self-test on accounts you own.

Targeting an individual without consent is stalking and is criminalized in most jurisdictions regardless of whether the technique used "public" data. Document scope before collection. Evidence retention follows operational-security-and-evidence.md.

## Evidence to log

- Observer coordinates and times (UTC) for every query.
- Raw reported distances + app version (rounding behavior changes between releases).
- LS residuals and σ per session.
- Cluster IDs, member counts, temporal labels.
- Photo provenance: profile, timestamp, source media SHA-256.
- Sun-position calculator inputs (date, time, lat/lon hypothesis) and resulting bearing.

## Tool ecosystem

- **scipy / scikit-learn** — least squares + DBSCAN.
- **pyproj** — projected CRS transforms (lat/lon ↔ UTM).
- **SunCalc.org / PhotoPills / Suncalc-py** — sun/moon position by time and location.
- **Google Earth Pro** — historical imagery, line-of-sight, 3D building view.
- **Mapillary / KartaView / Street View Time Machine** — street-level photo history.
- **OpenStreetMap Overpass API** — POI queries for landmark cross-checks.
- **EXIFtool** — residual metadata extraction.

## References

- "Geometric Dilution of Precision" — standard GNSS literature; same math applies to terrestrial trilateration.
- Pinperepette / Signal Pirate, "Il tramonto ha un indirizzo" — applied trilateration + RANSAC + sun-orientation closure write-up.
- Strava heatmap incident (2018) — early demonstration of behavioral clustering exposing sensitive locations.
- Bellingcat geolocation guides — mosaic-closure tradecraft.
