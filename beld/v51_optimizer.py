
import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Set, Tuple

try:
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    HAS_MPL = True
except Exception:
    HAS_MPL = False

CELL_SIZE_M = 0.6
GRID_COLS = 20
GRID_ROWS = 16
POP_SIZE = 60
GENERATIONS = 120
ELITE = 8
MUTATION_RATE = 0.28
SEED = 42

ROOM_SPECS = {
    "Living": {"target_m2": 24.0, "min_w": 4, "min_h": 4, "shape_options": ["RECT"]},
    "Kitchen": {"target_m2": 10.0, "min_w": 3, "min_h": 3, "shape_options": ["RECT", "L_SHAPE"]},
    "MasterBed": {"target_m2": 16.0, "min_w": 4, "min_h": 4, "shape_options": ["RECT"]},
    "Bed2": {"target_m2": 11.0, "min_w": 3, "min_h": 3, "shape_options": ["RECT"]},
    "Bath1": {"target_m2": 5.0, "min_w": 2, "min_h": 2, "shape_options": ["RECT", "L_SHAPE"]},
    "Bath2": {"target_m2": 4.0, "min_w": 2, "min_h": 2, "shape_options": ["RECT"]},
    "Parking": {"target_m2": 18.0, "min_w": 4, "min_h": 4, "shape_options": ["RECT"]},
}

REQUIRED_ADJ = [("Living", "Kitchen"), ("Living", "MasterBed"), ("MasterBed", "Bath1"), ("Bed2", "Bath2")]
CORRIDOR_ATTACH = ["Living", "Kitchen", "MasterBed", "Bed2", "Bath1", "Bath2"]
ROOM_SPECS_INV = {k: v for k, v in ROOM_SPECS.items()}


def clamp(v, lo, hi):
    return max(lo, min(v, hi))


def ensure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def rect_cells(anchor, extent):
    ax, ay = anchor
    w, h = extent
    return {(x, y) for x in range(ax, ax + w) for y in range(ay, ay + h)}


def lshape_cells(anchor, extent, l_params):
    ax, ay = anchor
    w, h = extent
    cut_w, cut_h = l_params
    cut_w = clamp(cut_w, 1, max(1, w - 1))
    cut_h = clamp(cut_h, 1, max(1, h - 1))
    full = rect_cells(anchor, extent)
    cut = {(x, y) for x in range(ax + w - cut_w, ax + w) for y in range(ay + h - cut_h, ay + h)}
    cells = full - cut
    return cells if cells else full


def neighbors4(c):
    x, y = c
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def connected_components(cells: Set[Tuple[int, int]]):
    cells = set(cells)
    comps = []
    while cells:
        start = next(iter(cells))
        stack = [start]
        comp = {start}
        cells.remove(start)
        while stack:
            cur = stack.pop()
            for n in neighbors4(cur):
                if n in cells:
                    cells.remove(n)
                    comp.add(n)
                    stack.append(n)
        comps.append(comp)
    return comps


def shared_edge_count(a: Set[Tuple[int, int]], b: Set[Tuple[int, int]]):
    cnt = 0
    for c in a:
        for n in neighbors4(c):
            if n in b:
                cnt += 1
    return cnt


def bbox(cells: Set[Tuple[int, int]]):
    xs = [c[0] for c in cells]
    ys = [c[1] for c in cells]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def bbox_fill_ratio(cells: Set[Tuple[int, int]]):
    if not cells:
        return 0.0
    x0, y0, x1, y1 = bbox(cells)
    return len(cells) / float((x1 - x0) * (y1 - y0))


def room_area_m2(cells: Set[Tuple[int, int]]):
    return len(cells) * CELL_SIZE_M * CELL_SIZE_M


def corridor_cells(spine):
    axis = spine["axis"]
    coord = spine["coordinate"]
    s0, s1 = spine["span"]
    cells = set()
    if axis == "Y":
        for y in range(s0, s1):
            if 0 <= coord < GRID_COLS and 0 <= y < GRID_ROWS:
                cells.add((coord, y))
    else:
        for x in range(s0, s1):
            if 0 <= x < GRID_COLS and 0 <= coord < GRID_ROWS:
                cells.add((x, coord))
    return cells


@dataclass
class Candidate:
    genome: Dict
    score: float = -1e18
    details: Dict = field(default_factory=dict)


class V51Engine:
    def __init__(self, seed=SEED):
        self.rng = random.Random(seed)

    def init_room(self, name):
        spec = ROOM_SPECS[name]
        target_cells = max(4, round(spec["target_m2"] / (CELL_SIZE_M * CELL_SIZE_M)))
        w = max(spec["min_w"], int(math.sqrt(target_cells)))
        h = max(spec["min_h"], math.ceil(target_cells / w))
        w = clamp(w, spec["min_w"], GRID_COLS - 1)
        h = clamp(h, spec["min_h"], GRID_ROWS - 1)
        ax = self.rng.randint(0, max(0, GRID_COLS - w))
        ay = self.rng.randint(0, max(0, GRID_ROWS - h))
        shape = self.rng.choice(spec["shape_options"])
        room = {"anchor": (ax, ay), "extent": (w, h), "shape": shape}
        if shape == "L_SHAPE":
            room["l_params"] = (max(1, w // 3), max(1, h // 3))
        return room

    def random_spine(self):
        axis = self.rng.choice(["Y", "X"])
        if axis == "Y":
            return {"axis": "Y", "coordinate": self.rng.randint(3, GRID_COLS - 4), "span": (0, GRID_ROWS)}
        return {"axis": "X", "coordinate": self.rng.randint(3, GRID_ROWS - 4), "span": (0, GRID_COLS)}

    def make_candidate(self):
        return Candidate(genome={"rooms": {name: self.init_room(name) for name in ROOM_SPECS}, "corridor_spine": self.random_spine()})

    def decode_room(self, room):
        cells = rect_cells(room["anchor"], room["extent"])
        if room.get("shape") == "L_SHAPE":
            cells = lshape_cells(room["anchor"], room["extent"], room.get("l_params", (1, 1)))
        return {(x, y) for x, y in cells if 0 <= x < GRID_COLS and 0 <= y < GRID_ROWS}

    def mutate_room(self, room):
        room = {k: (tuple(v) if isinstance(v, tuple) else v) for k, v in room.items()}
        op = self.rng.choice(["nudge", "stretch", "shape"])
        ax, ay = room["anchor"]
        w, h = room["extent"]
        if op == "nudge":
            dx, dy = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            room["anchor"] = (clamp(ax + dx, 0, GRID_COLS - w), clamp(ay + dy, 0, GRID_ROWS - h))
        elif op == "stretch":
            dw, dh = self.rng.choice([(1, 0), (-1, 0), (0, 1), (0, -1)])
            min_w = ROOM_SPECS_INV[room["name"]]["min_w"]
            min_h = ROOM_SPECS_INV[room["name"]]["min_h"]
            new_w = clamp(w + dw, min_w, GRID_COLS - ax)
            new_h = clamp(h + dh, min_h, GRID_ROWS - ay)
            if 0.35 < (new_w / max(new_h, 1)) < 3.5:
                room["extent"] = (new_w, new_h)
        else:
            opts = ROOM_SPECS_INV[room["name"]]["shape_options"]
            room["shape"] = self.rng.choice(opts)
            if room["shape"] == "L_SHAPE":
                room["l_params"] = (
                    clamp(self.rng.randint(1, max(1, w - 1)), 1, max(1, w - 1)),
                    clamp(self.rng.randint(1, max(1, h - 1)), 1, max(1, h - 1)),
                )
            else:
                room.pop("l_params", None)
        return room

    def mutate_spine(self, spine):
        spine = dict(spine)
        if self.rng.random() < 0.75:
            d = self.rng.choice([-1, 1])
            if spine["axis"] == "Y":
                spine["coordinate"] = clamp(spine["coordinate"] + d, 0, GRID_COLS - 1)
            else:
                spine["coordinate"] = clamp(spine["coordinate"] + d, 0, GRID_ROWS - 1)
        else:
            spine["axis"] = "X" if spine["axis"] == "Y" else "Y"
            max_coord = GRID_ROWS - 1 if spine["axis"] == "X" else GRID_COLS - 1
            spine["coordinate"] = clamp(spine["coordinate"], 0, max_coord)
            spine["span"] = (0, GRID_COLS if spine["axis"] == "X" else GRID_ROWS)
        return spine

    def mutate(self, cand):
        g = {"rooms": {}, "corridor_spine": dict(cand.genome["corridor_spine"])}
        for name, room in cand.genome["rooms"].items():
            rr = dict(room)
            rr["name"] = name
            if self.rng.random() < MUTATION_RATE:
                rr = self.mutate_room(rr)
            rr.pop("name", None)
            g["rooms"][name] = rr
        if self.rng.random() < MUTATION_RATE:
            g["corridor_spine"] = self.mutate_spine(g["corridor_spine"])
        return Candidate(g)

    def crossover(self, a, b):
        rooms = {name: dict(self.rng.choice([a.genome["rooms"][name], b.genome["rooms"][name]])) for name in ROOM_SPECS}
        spine = dict(self.rng.choice([a.genome["corridor_spine"], b.genome["corridor_spine"]]))
        return Candidate({"rooms": rooms, "corridor_spine": spine})

    def evaluate(self, cand):
        room_cells = {name: self.decode_room(room) for name, room in cand.genome["rooms"].items()}
        spine = corridor_cells(cand.genome["corridor_spine"])
        penalty, reward, overlap_cells = 0.0, 0.0, 0
        names = list(room_cells)

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                ov = room_cells[names[i]] & room_cells[names[j]]
                overlap_cells += len(ov)
        penalty += overlap_cells * 120.0

        for name, cells in room_cells.items():
            area = room_area_m2(cells)
            target = ROOM_SPECS[name]["target_m2"]
            penalty += abs(area - target) * 18.0
            comps = connected_components(cells) if cells else []
            if len(comps) > 1:
                penalty += (len(comps) - 1) * 400.0
            fill = bbox_fill_ratio(cells)
            if cand.genome["rooms"][name].get("shape") == "RECT":
                penalty += max(0.0, 0.98 - fill) * 500.0
            else:
                penalty += max(0.0, 0.72 - fill) * 260.0
            if not cells:
                penalty += 1000.0

        for a, b in REQUIRED_ADJ:
            shared = shared_edge_count(room_cells[a], room_cells[b])
            if shared == 0:
                penalty += 180.0
            else:
                reward += min(shared, 6) * 20.0

        for name in CORRIDOR_ATTACH:
            shared = shared_edge_count(room_cells[name], spine)
            if shared == 0:
                penalty += 140.0
            else:
                reward += min(shared, 4) * 15.0

        if len(spine) < min(GRID_COLS, GRID_ROWS) // 2:
            penalty += 120.0
        reward += len(spine) * 2.0

        ext_align = 0
        for cells in room_cells.values():
            if cells:
                x0, y0, x1, y1 = bbox(cells)
                if x0 == 0 or y0 == 0 or x1 == GRID_COLS or y1 == GRID_ROWS:
                    ext_align += 1
        reward += ext_align * 20.0

        cand.score = reward - penalty
        cand.details = {
            "overlap_cells": overlap_cells,
            "reward": reward,
            "penalty": penalty,
            "room_cells": room_cells,
            "spine": spine,
        }
        return cand.score

    def tournament(self, pop, k=4):
        return max(self.rng.sample(pop, k), key=lambda c: c.score)

    def evolve(self):
        pop = [self.make_candidate() for _ in range(POP_SIZE)]
        for c in pop:
            self.evaluate(c)
        best = max(pop, key=lambda c: c.score)
        history = []
        for gen in range(1, GENERATIONS + 1):
            pop.sort(key=lambda c: c.score, reverse=True)
            if pop[0].score > best.score:
                best = pop[0]
            history.append(best.score)
            if gen % 10 == 0 or gen == 1:
                print(
                    f"Gen {gen:03d} best={best.score:9.2f} "
                    f"penalty={best.details['penalty']:8.2f} overlap={best.details['overlap_cells']:3d}"
                )
            next_pop = pop[:ELITE]
            while len(next_pop) < POP_SIZE:
                if self.rng.random() < 0.55:
                    child = self.crossover(self.tournament(pop), self.tournament(pop))
                else:
                    p = self.tournament(pop)
                    child = Candidate(
                        {
                            "rooms": {k: dict(v) for k, v in p.genome["rooms"].items()},
                            "corridor_spine": dict(p.genome["corridor_spine"]),
                        }
                    )
                child = self.mutate(child)
                self.evaluate(child)
                next_pop.append(child)
            pop = next_pop
        return best, history


def plot_solution(best, out_png="output/v51_layout.png"):
    ensure_parent_dir(out_png)
    if not HAS_MPL:
        print("matplotlib not available; skipping PNG")
        return
    colors = {
        "Living": "#9ecae1",
        "Kitchen": "#fdd0a2",
        "MasterBed": "#c7e9c0",
        "Bed2": "#fdae6b",
        "Bath1": "#dadaeb",
        "Bath2": "#f2f0f7",
        "Parking": "#bdbdbd",
    }
    fig, ax = plt.subplots(figsize=(12, 9))
    ax.set_xlim(0, GRID_COLS)
    ax.set_ylim(0, GRID_ROWS)
    ax.set_aspect("equal")
    ax.invert_yaxis()
    for x in range(GRID_COLS + 1):
        ax.plot([x, x], [0, GRID_ROWS], color="#eeeeee", linewidth=0.6)
    for y in range(GRID_ROWS + 1):
        ax.plot([0, GRID_COLS], [y, y], color="#eeeeee", linewidth=0.6)
    for name, cells in best.details["room_cells"].items():
        for x, y in cells:
            ax.add_patch(Rectangle((x, y), 1, 1, facecolor=colors.get(name, "#cccccc"), edgecolor="black", linewidth=1.0))
        if cells:
            x0, y0, x1, y1 = bbox(cells)
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, name, ha="center", va="center", fontsize=10, weight="bold")
    for x, y in best.details["spine"]:
        ax.add_patch(Rectangle((x, y), 1, 1, facecolor="#fff59d", edgecolor="#bc8f00", linewidth=1.2, hatch="//"))
    ax.add_patch(Rectangle((0, 0), GRID_COLS, GRID_ROWS, fill=False, edgecolor="red", linewidth=2.2, linestyle="--"))
    ax.set_title(f"V5.1 Anchor-Extent-Spine Layout | score={best.score:.2f}")
    plt.tight_layout()
    plt.savefig(out_png, dpi=180)
    plt.close(fig)


def write_summary(best, history, path="output/v51_summary.txt"):
    ensure_parent_dir(path)
    with open(path, "w", encoding="utf-8") as f:
        f.write("V5.1 Anchor-Extent-Spine Layout Optimization Summary\n")
        f.write("=" * 58 + "\n")
        f.write(f"Grid: {GRID_COLS} x {GRID_ROWS} | Cell size: {CELL_SIZE_M} m\n")
        f.write(f"Best score: {best.score:.2f}\n")
        f.write(f"Penalty: {best.details['penalty']:.2f} | Reward: {best.details['reward']:.2f}\n")
        f.write(f"Overlap cells: {best.details['overlap_cells']}\n\n")
        for name, room in best.genome["rooms"].items():
            cells = best.details["room_cells"][name]
            f.write(
                f"{name}: anchor={room['anchor']} extent={room['extent']} shape={room['shape']} "
                f"area_m2={room_area_m2(cells):.2f} fill_ratio={bbox_fill_ratio(cells):.2f}\n"
            )
        f.write("\nCorridor spine\n")
        f.write(str(best.genome["corridor_spine"]) + "\n")
        f.write("\nFitness tail\n")
        f.write(", ".join(f"{x:.1f}" for x in history[-20:]))


def run_v51(out_dir="output"):
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    engine = V51Engine(seed=SEED)
    best, history = engine.evolve()
    plot_solution(best, out_png=str(out_dir / "v51_layout.png"))
    write_summary(best, history, path=str(out_dir / "v51_summary.txt"))
    return best, history


if __name__ == "__main__":
    print("Launching V5.1 anchor-extent-spine optimization...")
    best, history = run_v51()
    print(f"Done. Best score={best.score:.2f}")
    print("Saved: output/v51_layout.png")
    print("Saved: output/v51_summary.txt")
