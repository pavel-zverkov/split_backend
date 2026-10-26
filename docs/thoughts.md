ok, api is upped at the localhost:8000, ui at the localhost:3000. 
lets discuss filters for competitions results and splits. we has filter for competition distance and competition classes. usually one athelete    
run one distance and one athelete belong to one class. so organizer link distance to classes. but sometimes we can has one athelete run more than one distance. you can find it for example                         
http://localhost:3000/events/7/competitions/15. so if competition has too much classes current filter ui is not freindly - very long list for scrolling. we can implement new behaviour, but i'm not finished       
create ux. what i think: 

we has two situation:
1. class many-to-one link distance
2. class many-to-many link distance
do we has this linkes in backend architecture?
if i turn concrete distance in distance filters, show the classes filters for this distance -> its good for сужения searching, but what we will do, if user want choose another class,  
that link to another distance and user dont know anything about this distance. classes ussualy separate by age and gender, but sometimes we has another classes (pro, begginers and others). so we can separate classes filters by this pattern and show separated filters for gender and age, if filters does'nt fit to screen wide. can you suggest any decision?

1. "So: many classes → one distance is the intended model. Many-to-many doesn't exist in the backend schema today."  - but ux and ui need for it. 
2. Sometimes users want compare their results inside the distance, how it would work for scenario 2?

I can't open the URL, but I know control-app.net well — it overlays a GPS track on an orienteering map and lets you manually align (translate + rotate + scale) the route until it matches the course.

  Here's how it fits your project:

  ---
  The core problem
  Your maps are JPEGs with no georeferencing. GPS data is WGS84 lat/lng. There's no automatic way to match them — you need a manual affine alignment (tx, ty, rotation, scale) stored per workout+map combination.

  ---
  What you already have
  - Workout → Result link (so you know which GPS track belongs to which athlete's run)
  - GPS/FIT/TCX files in MinIO
  - JPEG map in the viewer with pan/zoom
  - PostGIS (useful later for spatial queries)

  ---
  Proposed architecture

  Backend additions:
  1. New endpoint: GET /workouts/{id}/track → parses the FIT/GPX file, returns a flat projected [{x, y}] array (equirectangular from centroid — good enough for 5–20 km orienteering courses)
  2. New table route_alignments: (competition_id, workout_id, tx, ty, scale, rotation) — stores the affine transform once aligned. One alignment per workout+competition pair, reusable across sessions

  Frontend additions:
  1. SVG overlay layer on ImageMapViewer — renders GPS track as <polyline> transformed by the stored affine matrix
  2. Alignment mode UI — drag to translate, corner handle to rotate+scale simultaneously (same pattern as control-app), toggle "edit/lock"
  3. Multi-route display — from the analyze page, show selected athletes' routes simultaneously, color-coded

  ---
  Workflow
  1. Open splits page → select athlete → "Overlay route"
  2. Track appears on map (initially centered, unaligned)
  3. User drags/rotates/scales until it matches the course
  4. Click "Save alignment" → stored once for that competition's map
  5. Next athlete's track for the same competition uses the same spatial context (you shift their track by the saved matrix + their individual GPS offset)

  ---
  Main trade-off
  One alignment vs per-athlete alignment: ideally you calibrate once using one well-known route (e.g. winner's track), and all other tracks use the same map-space transformation. This works well if GPS quality is
  consistent. With forest/canopy interference, per-athlete fine-tuning might be needed.

  Want me to start implementing? I'd suggest starting with the backend track endpoint + the SVG overlay layer on the map, then the alignment UI.

✻ Baked for 46s

❯ maybe we need separate service for it. we starting create mapbox service, maybe we has artifacts at docs section?                                                                                                   

⏺ Good question — this is the right moment to think architecturally before building.

  ---
  Why a separate service makes sense here

  The route alignment / map georeferencing work is fundamentally different from the main app:
  - Heavy spatial computation (projections, affine transforms, raster warping)
  - Different dependency stack (GDAL, rasterio, turf.js, or Mapbox)
  - Could be stateless (compute-only, main backend owns storage)
  - Can be developed/deployed independently

  A thin geo-service (Python + FastAPI, or Node) that exposes:
  - POST /parse-track → FIT/GPX → GeoJSON LineString
  - POST /georeference → control point pairs → affine matrix
  - GET /tile/{z}/{x}/{y} → serves warped map JPEG as raster tiles (if you go Mapbox route)

  ---
  Mapbox approach changes everything

  If the JPEG map is georeferenced (even roughly, with 3–4 control points), you can add it as a raster source in Mapbox GL JS. Then GPS tracks are just GeoJSON — they align automatically. No manual drag/rotate UI
  needed.

  The georeferencing step: user picks 2–4 points on the JPEG → clicks the same spots on a Mapbox satellite/topo layer → system solves the affine transform → stored as artifact metadata.

  ---
  Artifacts fit naturally

  Your existing artifact system could store:
  - kind: MAP → JPEG (already done)
  - kind: COURSE → .kml / .geojson with control positions (already planned)
  - kind: MAP_GEOREF → the affine matrix JSON (4 GCP pairs + transform) attached to the map artifact, or as a companion artifact with distance_id

  So no new storage model needed — just new artifact kinds and a georef_data: JSON field on the artifact, or a separate companion artifact referencing the parent map by ID.

  ---
  My recommendation

  Start with the geo-service + Mapbox approach:
  1. Geo-service: parse GPS tracks, serve warped JPEG tiles
  2. Artifacts: add MAP_GEOREF kind, store control point pairs
  3. Frontend: replace the current ImageMapViewer with Mapbox GL JS in the splits/analyze pages — map JPEG as raster layer, GPS tracks as GeoJSON layers

  Want to start sketching the geo-service API or the artifact schema first?