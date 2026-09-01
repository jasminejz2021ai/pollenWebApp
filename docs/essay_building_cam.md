# Building CAM: How I Created and Gradually Improved a Campus Pollen-Mapping Web App

## Where it started

I have always been struck by how uneven allergy season feels. Walking from one
class to the next, I could go from barely noticing the air to eyes watering in
the span of a few dozen steps. The regional pollen "counts" on weather apps
never explained this — they report one number for a whole city, updated once a
day. That number cannot tell you that the corridor behind the gym is worse than
the quad, or that the oak-lined path you take every morning is the reason your
nose runs by first period. I wanted something that could resolve pollen at the
scale a student actually experiences it: meters, not miles.

That idea became **Campus AeroAllergen Mapping (CAM)** — a web app that models
how pollen disperses across a school campus and shows the result as a live map.
What follows is the story of how I built it and, more importantly, how I kept
improving it, one problem at a time.

## The first version: getting something real on the screen

The very first version was about proving the concept could exist at all. I set
up a Flask backend in Python to do the physics and a React frontend (with
Vite and Leaflet) to draw the map. The core science is a **Gaussian plume
model**: a well-established way to describe how a puff of material released
from a point source spreads downwind as the wind carries it (advection) and
turbulence widens it (diffusion). Each tree on campus became a point source of
pollen, and the app summed the plumes from every tree to produce a
concentration field over a grid.

To make the pollen realistic in time, I added a **phenology model** — each tree
species only releases pollen during its flowering window, modeled as a smooth
Gaussian "gate" over the year with a species-specific peak day and potency. An
oak in April behaves very differently from a pine in June.

Getting the first version running locally was its own small saga. My project
lived in a cloud-synced folder, and the dev server kept hanging because the
file watcher stalled on cloud placeholder files. Moving the project to a plain
local directory fixed it instantly. It was my first lesson that a lot of
"building software" is really about removing invisible friction.

## Putting it on the internet

A map that only runs on my laptop helps no one. So the next step was
deployment: the backend to Render, the frontend to Vercel. This is where I hit
my first genuinely confusing bug — roughly a quarter of requests to the live
backend came back as 404, seemingly at random. It took real detective work to
realize the server was running two worker processes, and one of them had only
partially finished loading its routes during startup. The fix was to have the
master process load the app once and then fork identical, fully-initialized
workers. After that, sixty out of sixty test requests succeeded. Debugging
something that fails only *sometimes* taught me to think about state and timing,
not just logic.

## Letting users ask "what if?"

Once it was live, I wanted the app to be more than a snapshot of right-now. I
added a **test mode** so anyone could override the live weather and ask
questions: What does the map look like on a windy April afternoon? On a calm,
stable morning? By exposing sliders for date, wind speed, wind direction, and
atmospheric stability class, the app turned from a dashboard into an
exploratory tool. My first attempt didn't actually let users type in those
inputs; I had to go back and wire the controls all the way through the
frontend, the API, and the physics engine. Features are only real once they
work end to end.

## Making the map look like the real campus

Early maps were blurry, which undercut the whole point of a *hyperlocal* tool.
I re-captured the satellite imagery at much higher resolution — 3000 pixels for
Gunn — and then took on something more ambitious: adding **Stanford** as a
second campus, covering the full core plus surrounding areas. Stanford is huge,
and stitching its imagery together revealed a subtle problem: the tiles didn't
line up, with roads visibly jumping across seams. The cause was a projection
mismatch, and the fix was to stitch the tiles in Web Mercator so they aligned
perfectly. I also switched Stanford to USGS NAIP imagery because its
true-color rendering shows the campus's characteristic red-tile roofs
accurately.

To make the app genuinely multi-campus, I refactored the hardcoded Gunn data
into a campus registry — each campus defined by its bounds, trees, buildings,
and boundary — so adding a new campus became a matter of data, not code
surgery.

## Teaching the app to see: from color to deep learning

I needed to know where the trees and buildings actually were. I began with
classical computer vision: detecting tree canopies by their green color and
splitting touching canopies with a watershed algorithm. Trees are relatively
easy because they're green. Rooftops are not — roofs, pavement, and dry ground
share overlapping colors. So for buildings I brought in the **Segment Anything
Model (SAM)**, a pretrained deep-learning segmentation network, and kept only
the masks that looked like rooftops by size, shape, and color. Because SAM
downsamples large images internally, I ran it on a grid of overlapping tiles so
small rooftops were resolved at higher effective resolution, then merged the
results. On Stanford this jumped detection from a couple hundred buildings to
thousands.

Crucially, I built a **human-in-the-loop** workflow. Automated detection is a
starting point, not the final answer. I added an interactive editor so I could
delete false positives, move trees, resize canopies, relabel species, and
reshape building footprints directly on the map. This semi-automated approach —
algorithm proposes, human corrects — turned out to be far more practical than
chasing a perfect fully-automatic detector.

## Making the physics smarter: wind that bends around buildings

The original model assumed the wind blew uniformly across the whole campus.
But buildings redirect wind — they channel it between structures and divert it
around corners — and that changes where pollen goes. I replaced the uniform
wind with a **2D potential-flow field**: I solve Laplace's equation on the grid
with the buildings as obstacles, producing a wind field that flows *around*
each footprint. Then, instead of one campus-wide wind, each tree's plume is
driven by the local wind at its own location, so plumes bend and stretch
realistically.

I was careful to be honest about the model's limits. Potential flow is
inviscid — it captures diversion but not the turbulent, pollen-trapping wake
behind a building. I documented that plainly rather than overclaiming, because
a model you can trust is one whose boundaries you state. I also made sure pollen
concentration is zeroed inside building footprints, since you don't breathe
outdoor pollen while standing indoors.

Along the way I fought performance battles. With thousands of trees and
thousands of buildings, naively pairing every tree with every building made a
single map take nearly twenty seconds. Filtering each tree to only the
buildings within a couple hundred meters brought that back down to a few
seconds — fast enough to feel interactive.

## Sweating the interface details

A physics engine is useless if the interface fights the user. A lot of my later
work was UX polish that came directly from actually using the app:

- I moved the map controls out of the map itself into a clean toolbar, because
  too many buttons were floating over the imagery.
- I made the info panels collapsible so they stop blocking the view.
- I fixed popups that got clipped at the map's edges, and an infuriating bug
  where dragging a building corner near the top of the map made the whole view
  refresh and the shape vanish. The root cause was a subtle one: an array being
  recreated on every render was retriggering a "fit the map to bounds" effect.
- When editing building shapes, the app kept snapping my parallelograms and
  trapezoids back into rectangles. I changed it to preserve the exact dragged
  vertices, so real, non-rectangular rooftops survive.
- I added a "Move Trees" mode with draggable handles, and editable canopy radius
  and species — the radius even feeds back into the physics, since a bigger
  canopy emits proportionally more pollen.

The scariest bug in this phase turned a whole page blank white when I clicked a
building near the map edge — an uncaught error crashing the entire app. I fixed
the immediate cause (a popup fighting the map's hard boundary) and, just as
importantly, wrapped the map in an **error boundary** so a single component
hiccup can never again take down the whole page. Defense in depth matters.

## Grounding the model in reality

The more the app matured, the more I cared about whether its inputs reflected
the *actual* campuses. I went looking for real data. For Gunn, I found the 2009
PAUSD arborist inventory — 455 numbered trees with species — and used it to set
the campus's real species proportions (oaks about 42%, redwood about 20%),
rather than guessing. I discovered Cedar was a meaningful presence that I wasn't
modeling, and added it — which gave the app a realistic *fall* pollen peak it
never had before, since cedar pollinates in autumn.

For Stanford, I found the university's tree inventory: over 43,000 trees,
dominated by coast live oak (~40% of the population), with palms, eucalyptus,
redwood, and olive rounding out the most common species. I labeled the campus
by those top species and left the long tail as a generic "Other" class. I also
noticed the tree detector had placed many canopies on top of rooftops, so I
wrote a geometric filter that removes any tree whose canopy mostly overlaps a
building — pruning about 43% of Stanford's raw detections as rooftop false
positives.

Being honest about uncertainty became a design principle. Rather than pretend I
could identify every tree from satellite color, I model a confident subset by
species and assign the rest a conservative generic profile — so the map is
faithful about what it does and doesn't know.

## What I learned

CAM didn't arrive fully formed; it grew through dozens of small, deliberate
improvements. Each one started with a concrete complaint — this is blurry, this
crashes, this snaps back, this doesn't match the real campus — and ended with a
fix that made the whole thing a little more trustworthy. I learned that:

- **Shipping early beats perfecting in private.** Deploying exposed the real
  bugs (like the intermittent 404s) that I'd never have found on my laptop.
- **Debugging is a skill of its own,** especially for problems that only appear
  sometimes or only in production.
- **Physical models should state their limits.** The potential-flow wind is a
  cheap, useful approximation, and saying so is more scientific than hiding it.
- **Automation plus human judgment beats either alone.** The detector gets me
  90% of the way; my corrections get the rest.
- **Grounding a model in real data** — a 2009 tree survey, a university
  inventory — is what separates a plausible demo from a credible tool.

The app I have now maps thousands of individual trees and buildings across two
campuses, computes a physically-motivated pollen field in seconds, and lets
anyone explore how season and weather change the risk along their own walk to
class. It is not finished — the honest next step is validating its predictions
against real pollen measurements — but it is a real, working answer to the
question I started with: *why does the air feel so different a hundred steps
from here?*
