import numpy as np
import random
import os
import base64
import io
from PIL import Image as PilImage, ImageDraw

# ── Model ─────────────────────────────────────────────────────────────────────

class WolfSheepModel:

    def __init__(
        self,
        width=50,
        height=50,
        initial_sheep=100,
        initial_wolves=50,
        sheep_reproduce=4,
        wolf_reproduce=5,
        sheep_gain_from_food=4,
        wolf_gain_from_food=20,
        grass_regrowth_time=30
    ):
        self.width = width
        self.height = height
        self.sheep_reproduce = sheep_reproduce
        self.wolf_reproduce = wolf_reproduce
        self.sheep_gain_from_food = sheep_gain_from_food
        self.wolf_gain_from_food = wolf_gain_from_food
        self.grass_regrowth_time = grass_regrowth_time

        self.grid_grass = np.ones((height, width))
        self.countdown = np.zeros((height, width))

        self.sheep = []
        self.wolves = []

        for _ in range(initial_sheep):
            self.sheep.append({
                "x": random.randrange(width),
                "y": random.randrange(height),
                "energy": random.randrange(2 * sheep_gain_from_food)
            })

        for _ in range(initial_wolves):
            self.wolves.append({
                "x": random.randrange(width),
                "y": random.randrange(height),
                "energy": random.randrange(2 * wolf_gain_from_food)
            })

    def move(self, agent):
        dx = random.choice([-1, 0, 1])
        dy = random.choice([-1, 0, 1])
        agent["x"] = (agent["x"] + dx) % self.width
        agent["y"] = (agent["y"] + dy) % self.height

    def step(self):
        new_sheep = []
        new_wolves = []

        random.shuffle(self.sheep)
        for sheep in self.sheep:
            self.move(sheep)
            sheep["energy"] -= 1
            x, y = sheep["x"], sheep["y"]
            if self.grid_grass[y, x] == 1:
                self.grid_grass[y, x] = 0
                self.countdown[y, x] = self.grass_regrowth_time
                sheep["energy"] += self.sheep_gain_from_food
            # Fixed: reproduction only if alive
            if sheep["energy"] >= 0:
                new_sheep.append(sheep)
                if random.random() * 100 < self.sheep_reproduce:
                    sheep["energy"] /= 2
                    new_sheep.append({
                        "x": sheep["x"],
                        "y": sheep["y"],
                        "energy": sheep["energy"]
                    })
        self.sheep = new_sheep

        # Build spatial index for O(1) predation lookup
        sheep_by_pos = {}
        for s in self.sheep:
            sheep_by_pos.setdefault((s["x"], s["y"]), []).append(s)

        random.shuffle(self.wolves)
        for wolf in self.wolves:
            self.move(wolf)
            wolf["energy"] -= 1
            prey_list = sheep_by_pos.get((wolf["x"], wolf["y"]), [])
            if prey_list:
                prey = prey_list.pop()
                self.sheep.remove(prey)
                wolf["energy"] += self.wolf_gain_from_food
            # Fixed: reproduction only if alive
            if wolf["energy"] >= 0:
                new_wolves.append(wolf)
                if random.random() * 100 < self.wolf_reproduce:
                    wolf["energy"] /= 2
                    new_wolves.append({
                        "x": wolf["x"],
                        "y": wolf["y"],
                        "energy": wolf["energy"]
                    })
        self.wolves = new_wolves

        self.countdown[self.grid_grass == 0] -= 1
        regrow = self.countdown <= 0
        self.grid_grass[regrow] = 1
        self.countdown[regrow] = 0  # Fixed: reset stale countdown

    def sheep_count(self):
        return len(self.sheep)

    def wolf_count(self):
        return len(self.wolves)

# ── Rendering (pure Pillow, no matplotlib) ────────────────────────────────────

# Colours for each cell state
COLOUR_BARE  = (139, 90,  43)   # brown
COLOUR_GRASS = (34,  139, 34)   # green
COLOUR_SHEEP = (255, 255, 255)  # white
COLOUR_WOLF  = (20,  20,  20)   # near-black

CELL = 8  # pixel size of each grid cell


def render_grid(model):
    """Render the environment grid as a Pillow Image."""
    img = PilImage.new("RGB", (model.width * CELL, model.height * CELL))
    draw = ImageDraw.Draw(img)

    for y in range(model.height):
        for x in range(model.width):
            colour = COLOUR_GRASS if model.grid_grass[y, x] == 1 else COLOUR_BARE
            draw.rectangle(
                [x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1],
                fill=colour
            )

    for sheep in model.sheep:
        cx = sheep["x"] * CELL + CELL // 2
        cy = sheep["y"] * CELL + CELL // 2
        r = CELL // 2 - 1
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COLOUR_SHEEP)

    for wolf in model.wolves:
        cx = wolf["x"] * CELL + CELL // 2
        cy = wolf["y"] * CELL + CELL // 2
        r = CELL // 2 - 1
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=COLOUR_WOLF)

    return img


def render_plot(sheep_vals, wolf_vals, steps, max_pop, plot_w=400, plot_h=400):
    """Render the population chart as a Pillow Image."""
    pad = 50
    img = PilImage.new("RGB", (plot_w, plot_h), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Axes
    draw.line([pad, pad, pad, plot_h - pad], fill=(180, 180, 180), width=1)
    draw.line([pad, plot_h - pad, plot_w - pad, plot_h - pad], fill=(180, 180, 180), width=1)

    # Title and labels
    draw.text((plot_w // 2 - 55, 8), "Population Dynamics", fill=(50, 50, 50))
    draw.text((pad + 4, pad - 14), "●  Sheep", fill=(30, 100, 220))
    draw.text((pad + 80, pad - 14), "●  Wolves", fill=(200, 40, 40))

    def to_px(step, val):
        sx = steps if steps > 0 else 1
        mx = max_pop if max_pop > 0 else 1
        x = pad + int((step / sx) * (plot_w - 2 * pad))
        y = (plot_h - pad) - int((val / mx) * (plot_h - 2 * pad))
        return x, y

    # Y-axis ticks
    for i in range(5):
        val = int(max_pop * i / 4)
        _, py = to_px(0, val)
        draw.line([pad - 4, py, pad, py], fill=(180, 180, 180))
        draw.text((2, py - 6), str(val), fill=(120, 120, 120))

    # Plot lines
    n = len(sheep_vals)
    if n > 1:
        for i in range(1, n):
            draw.line([to_px(i - 1, sheep_vals[i - 1]), to_px(i, sheep_vals[i])],
                      fill=(30, 100, 220), width=2)
            draw.line([to_px(i - 1, wolf_vals[i - 1]), to_px(i, wolf_vals[i])],
                      fill=(200, 40, 40), width=2)

    return img


def combine_frames(grid_img, plot_img):
    """Stitch grid and plot side by side."""
    gh, gw = grid_img.height, grid_img.width
    ph, pw = plot_img.height, plot_img.width
    h = max(gh, ph)
    combined = PilImage.new("RGB", (gw + pw + 10, h), (240, 240, 240))
    combined.paste(grid_img, (0, (h - gh) // 2))
    combined.paste(plot_img, (gw + 10, (h - ph) // 2))
    return combined


def frame_to_b64(img):
    """Convert a Pillow image to a base64 PNG string."""
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ── HTML output ───────────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Wolf–Sheep Predator–Prey Model</title>
<style>
  body {{ font-family: 'Segoe UI', sans-serif; background: #1e1e2e; color: #cdd6f4;
          display: flex; flex-direction: column; align-items: center; padding: 24px; margin: 0; }}
  h1 {{ font-size: 1.3rem; margin-bottom: 4px; }}
  .subtitle {{ font-size: 0.8rem; color: #888; margin-bottom: 16px; }}
  #display {{ border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }}
  .controls {{ display: flex; gap: 12px; align-items: center; margin-top: 14px; flex-wrap: wrap; justify-content: center; }}
  button {{
    padding: 7px 18px; border-radius: 6px; border: none; cursor: pointer;
    font-size: 0.85rem; font-weight: 600; background: #313244; color: #cdd6f4;
    transition: background 0.2s;
  }}
  button:hover {{ background: #45475a; }}
  button#playBtn {{ background: #89b4fa; color: #1e1e2e; }}
  button#playBtn:hover {{ background: #74c7ec; }}
  .info {{ font-size: 0.78rem; color: #6c7086; margin-top: 10px; }}
  input[type=range] {{ accent-color: #89b4fa; width: 140px; }}
  label {{ font-size: 0.8rem; color: #a6adc8; }}
</style>
</head>
<body>
<h1>🐺 Wolf–Sheep Predator–Prey Model</h1>
<p class="subtitle">Agent-based model · {steps} steps · {width}×{height} grid</p>
<img id="display" src="" alt="simulation frame">
<div class="controls">
  <button id="playBtn" onclick="togglePlay()">⏸ Pause</button>
  <button onclick="stepBack()">◀ Step</button>
  <button onclick="stepFwd()">Step ▶</button>
  <button onclick="restart()">↺ Restart</button>
  <label>Speed <input type="range" id="speed" min="20" max="500" value="80" oninput="updateSpeed()"></label>
</div>
<div class="info" id="info">Step 0 / {steps}</div>

<script>
const frames = {frames_json};
let idx = 0, playing = true, timer = null;
const FPS_DEFAULT = 80;
let interval = FPS_DEFAULT;

function show(i) {{
  document.getElementById("display").src = "data:image/png;base64," + frames[i];
  document.getElementById("info").textContent = "Step " + i + " / {steps}";
}}

function next() {{
  if (idx < frames.length - 1) {{ idx++; show(idx); }}
  else {{ clearInterval(timer); playing = false; document.getElementById("playBtn").textContent = "▶ Play"; }}
}}

function togglePlay() {{
  playing = !playing;
  document.getElementById("playBtn").textContent = playing ? "⏸ Pause" : "▶ Play";
  if (playing) timer = setInterval(next, interval);
  else clearInterval(timer);
}}

function stepFwd() {{ if (idx < frames.length - 1) {{ idx++; show(idx); }} }}
function stepBack() {{ if (idx > 0) {{ idx--; show(idx); }} }}
function restart() {{ clearInterval(timer); idx = 0; show(0); playing = true;
  document.getElementById("playBtn").textContent = "⏸ Pause";
  timer = setInterval(next, interval); }}
function updateSpeed() {{
  interval = 520 - parseInt(document.getElementById("speed").value);
  if (playing) {{ clearInterval(timer); timer = setInterval(next, interval); }}
}}

show(0);
timer = setInterval(next, interval);
</script>
</body>
</html>
"""


# ── Main entry point ──────────────────────────────────────────────────────────

def run_predator_prey_model(
    steps=200,
    width=50,
    height=50,
    initial_sheep=100,
    initial_wolves=50,
    sheep_reproduce=4,
    wolf_reproduce=5,
    sheep_gain_from_food=4,
    wolf_gain_from_food=20,
    grass_regrowth_time=30
):
    model = WolfSheepModel(
        width=width, height=height,
        initial_sheep=initial_sheep, initial_wolves=initial_wolves,
        sheep_reproduce=sheep_reproduce, wolf_reproduce=wolf_reproduce,
        sheep_gain_from_food=sheep_gain_from_food,
        wolf_gain_from_food=wolf_gain_from_food,
        grass_regrowth_time=grass_regrowth_time,
    )

    max_pop = max(initial_sheep, initial_wolves) * 3
    sheep_vals, wolf_vals = [], []
    frame_b64s = []

    print(f"Running {steps} steps...")

    for frame in range(steps):
        model.step()
        sheep_vals.append(model.sheep_count())
        wolf_vals.append(model.wolf_count())

        grid_img = render_grid(model)
        plot_img = render_plot(sheep_vals, wolf_vals, steps, max_pop)
        combined = combine_frames(grid_img, plot_img)
        frame_b64s.append(frame_to_b64(combined))

        if frame % 50 == 0:
            print(f"  Step {frame}: sheep={model.sheep_count()}, wolves={model.wolf_count()}")

    print("Rendering complete. Writing HTML...")

    import json
    frames_json = json.dumps(frame_b64s)

    html = HTML_TEMPLATE.format(
        steps=steps,
        width=width,
        height=height,
        frames_json=frames_json,
    )

    save_path = os.path.join(os.getcwd(), "wolf_sheep.html")
    with open(save_path, "w") as f:
        f.write(html)

    print(f"Saved → {save_path}")
    return save_path


if __name__ == "__main__":
    run_predator_prey_model(
        steps=200,
        initial_sheep=100,
        initial_wolves=50,
        sheep_reproduce=4,
        wolf_reproduce=5,
        sheep_gain_from_food=4,
        wolf_gain_from_food=30,
        grass_regrowth_time=30
    )