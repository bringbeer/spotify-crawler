import os
import re
from PIL import Image
import numpy as np
from math import sqrt

def parse_index_file(index_file="index.txt"):
    """Parse the index file and extract album names with their song counts."""
    albums = {}
    artists = {}
    
    try:
        # Try reading the index file with common encodings to avoid mojibake
        # (UTF-8 is preferred; fall back to Windows-1252 / Latin-1 if needed).
        content = None
        for enc in ("utf-8", "cp1252", "latin-1"):
            try:
                with open(index_file, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
        if content is None:
            # Last resort: read with replacement for undecodable bytes
            with open(index_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
        
        # Extract album section
        album_match = re.search(r"Album Index:\n(.*?)\n(?:Artist Index:|Total songs:)", content, re.DOTALL)
        if album_match:
            album_lines = album_match.group(1).strip().split("\n")
            for line in album_lines:
                match = re.match(r"\s*(.+?):\s*(\d+)\s*songs", line)
                if match:
                    albums[match.group(1)] = int(match.group(2))
        
        # Extract artist section
        artist_match = re.search(r"Artist Index:\n(.*?)\n(?:Total songs:|$)", content, re.DOTALL)
        if artist_match:
            artist_lines = artist_match.group(1).strip().split("\n")
            for line in artist_lines:
                match = re.match(r"\s*(.+?):\s*(\d+)\s*songs", line)
                if match:
                    artists[match.group(1)] = int(match.group(2))
        
        return albums, artists
    except FileNotFoundError:
        print(f"Error: {index_file} not found")
        return {}, {}

def get_cover_path(album_name, covers_dir="covers"):
    """Find the cover image for an album."""
    sanitized_name = "".join(c if c.isalnum() else "_" for c in album_name)
    cover_path = os.path.join(covers_dir, f"{sanitized_name}.jpg")
    
    if os.path.exists(cover_path):
        return cover_path
    return None

def scale_dimension(count, min_count, max_count, min_size=50, max_size=300):
    """Scale dimension based on song count."""
    if max_count == min_count:
        return (min_size + max_size) // 2
    
    normalized = (count - min_count) / (max_count - min_count)
    return int(min_size + normalized * (max_size - min_size))

def build_cluster(albums, covers_dir="covers", output_file="cluster.png"):
    """Build a cluster image from album covers scaled by song count, largest in center."""
    if not albums:
        print("No albums found")
        return
    
    # Get song count range
    min_count = min(albums.values())
    max_count = max(albums.values())
    
    # Calculate scaled sizes and grid layout
    scaled_covers = []
    for album_name, count in albums.items():
        cover_path = get_cover_path(album_name, covers_dir)
        if cover_path:
            size = scale_dimension(count, min_count, max_count)
            scaled_covers.append({
                'name': album_name,
                'path': cover_path,
                'size': size,
                'count': count
            })
        else:
            print(f"Warning: Cover not found for {album_name}")
    
    if not scaled_covers:
        print("No album covers found")
        return
    
    # Sort by size descending (largest first for center placement)
    scaled_covers.sort(key=lambda x: x['size'], reverse=True)
    
    # Load images
    images = []
    for cover_info in scaled_covers:
        try:
            img = Image.open(cover_info['path']).convert('RGB')
            # Resize to square based on calculated size
            img = img.resize((cover_info['size'], cover_info['size']), Image.Resampling.LANCZOS)
            images.append(img)
        except Exception as e:
            print(f"Error loading {cover_info['name']}: {e}")
    
    if not images:
        print("No images could be loaded")
        return
    
    # Spiral-adjacent packing algorithm
    # We'll keep a list of placed rectangles and for each new image
    # generate candidate positions that place the new rect adjacent to
    # existing ones (touching on a side). Candidates are scored by
    # distance to center so placement stays compact. This minimizes
    # gaps while preventing overlap.
    placements = []  # List of dicts: {'img': Image, 'x': int, 'y': int, 'w': int, 'h': int}

    def rects_overlap(a, b):
        """Return True if rect a overlaps rect b. Rect is (x,y,w,h)."""
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return not (ax + aw <= bx or bx + bw <= ax or ay + ah <= by or by + bh <= ay)

    def center_distance(x, y, w, h):
        cx = x + w / 2.0
        cy = y + h / 2.0
        return sqrt(cx * cx + cy * cy)

    # place the largest image centered at origin (top-left coords)
    first_img = images[0]
    placements.append({'img': first_img, 'x': 0, 'y': 0, 'w': first_img.size[0], 'h': first_img.size[1]})

    # helper to build candidates adjacent to a placed rect
    def candidates_around(px, py, pw, ph, iw, ih):
        c = []
        # right (touch left side of candidate to right side of placed)
        c.append((px + pw, py))
        # right aligned bottom
        c.append((px + pw, py + ph - ih))
        # right centered
        c.append((px + pw, py + (ph - ih) // 2))
        # left
        c.append((px - iw, py))
        c.append((px - iw, py + ph - ih))
        c.append((px - iw, py + (ph - ih) // 2))
        # bottom
        c.append((px, py + ph))
        c.append((px + (pw - iw) // 2, py + ph))
        # top
        c.append((px, py - ih))
        c.append((px + (pw - iw) // 2, py - ih))
        return c

    # Place the rest of images
    for idx in range(1, len(images)):
        img = images[idx]
        iw, ih = img.size

        # generate candidate positions from all placed rects
        cand_set = []
        for p in placements:
            cand_set.extend(candidates_around(p['x'], p['y'], p['w'], p['h'], iw, ih))

        # also add positions around bounding box edges (small spiral expansion)
        min_x = min(p['x'] for p in placements)
        min_y = min(p['y'] for p in placements)
        max_x = max(p['x'] + p['w'] for p in placements)
        max_y = max(p['y'] + p['h'] for p in placements)
        # positions around bbox
        for t in range(-2, 3):
            cand_set.append((min_x - iw + t * 1, min_y + t))
            cand_set.append((max_x + t, min_y + t))
            cand_set.append((min_x + t, max_y + t))
            cand_set.append((max_x + t, max_y - ih + t))

        # de-duplicate candidates
        seen = set()
        candidates = []
        for (cx, cy) in cand_set:
            key = (int(cx), int(cy))
            if key in seen:
                continue
            seen.add(key)
            candidates.append((int(cx), int(cy)))

        # score candidates: prefer ones that do not overlap and touch at least one rect
        scored = []
        for (cx, cy) in candidates:
            rect = (cx, cy, iw, ih)
            overlap = False
            touching = False
            for p in placements:
                placed_rect = (p['x'], p['y'], p['w'], p['h'])
                if rects_overlap(rect, placed_rect):
                    overlap = True
                    break
                # touching check: edges equal
                if (cx + iw == p['x'] or cx == p['x'] + p['w'] or cy + ih == p['y'] or cy == p['y'] + p['h']):
                    # also check 1D overlap on the other axis
                    if not (cx + iw <= p['x'] or p['x'] + p['w'] <= cx) or not (cy + ih <= p['y'] or p['y'] + p['h'] <= cy):
                        touching = True
            if not overlap:
                dist = center_distance(cx, cy, iw, ih)
                scored.append((not touching, dist, cx, cy, touching))

        # If we have valid non-overlapping candidates, pick the one with lowest (not_touching, dist)
        if scored:
            scored.sort()
            _, _, chosen_x, chosen_y, _ = scored[0]
            placements.append({'img': img, 'x': chosen_x, 'y': chosen_y, 'w': iw, 'h': ih})
            continue

        # If no candidate from adjacency worked, perform a spiral search outward from center
        center_x = (min_x + max_x) / 2
        center_y = (min_y + max_y) / 2
        placed = False
        max_radius = max(max_x - min_x, max_y - min_y) + max(iw, ih) * 10
        step = max(10, int(min(iw, ih) / 2))
        r = step
        while r < max_radius and not placed:
            # try multiple angles for each radius
            for angle_deg in range(0, 360, 10):
                ang = angle_deg * (3.14159265 / 180.0)
                cx = int(center_x + r * np.cos(ang))
                cy = int(center_y + r * np.sin(ang))
                rect = (cx, cy, iw, ih)
                if any(rects_overlap(rect, (p['x'], p['y'], p['w'], p['h'])) for p in placements):
                    continue
                placements.append({'img': img, 'x': cx, 'y': cy, 'w': iw, 'h': ih})
                placed = True
                break
            r += step
        if not placed:
            # last resort: place to the right of bounding box
            placements.append({'img': img, 'x': max_x + 1, 'y': min_y, 'w': iw, 'h': ih})

    # Tighten placements: iteratively pull outer images toward cluster center
    def tighten_placements(placements, max_passes=100):
        def can_place_at(idx, x, y):
            pw = placements[idx]['w']
            ph = placements[idx]['h']
            rect = (x, y, pw, ph)
            for j, other in enumerate(placements):
                if j == idx:
                    continue
                if rects_overlap(rect, (other['x'], other['y'], other['w'], other['h'])):
                    return False
            return True

        for pass_num in range(max_passes):
            moved_any = False
            # compute current center (average of centers)
            centers_x = [p['x'] + p['w'] / 2.0 for p in placements]
            centers_y = [p['y'] + p['h'] / 2.0 for p in placements]
            center_x = sum(centers_x) / len(centers_x)
            center_y = sum(centers_y) / len(centers_y)

            # process outer items first (farther from center)
            dists = []
            for i, p in enumerate(placements):
                cx = p['x'] + p['w'] / 2.0
                cy = p['y'] + p['h'] / 2.0
                d = (cx - center_x) ** 2 + (cy - center_y) ** 2
                dists.append((d, i))
            dists.sort(reverse=True)

            for _, i in dists:
                p = placements[i]
                px = p['x']
                py = p['y']
                pw = p['w']
                ph = p['h']

                # try to move towards center (max 3 steps per pass to avoid infinite loops)
                for step_num in range(3):
                    cx = px + pw / 2.0
                    cy = py + ph / 2.0
                    vx = center_x - cx
                    vy = center_y - cy
                    step_x = int(np.sign(vx))
                    step_y = int(np.sign(vy))

                    moved = False
                    # try x move
                    if step_x != 0 and can_place_at(i, px + step_x, py):
                        px += step_x
                        moved = True
                        moved_any = True
                        placements[i]['x'] = px

                    # try y move
                    if step_y != 0 and can_place_at(i, px, py + step_y):
                        py += step_y
                        moved = True
                        moved_any = True
                        placements[i]['y'] = py

                    if not moved:
                        break

            if not moved_any:
                break

    tighten_placements(placements)

    # Calculate bounding box of final placements
    min_x = min(p['x'] for p in placements)
    min_y = min(p['y'] for p in placements)
    max_x = max(p['x'] + p['w'] for p in placements)
    max_y = max(p['y'] + p['h'] for p in placements)

    canvas_width = int(max_x - min_x)
    canvas_height = int(max_y - min_y)

    # Normalize coordinates
    placements = [(p['img'], int(p['x'] - min_x), int(p['y'] - min_y)) for p in placements]
    
    # Create canvas
    canvas = Image.new('RGB', (canvas_width, canvas_height), color=(20, 20, 20))
    
    # Place images on canvas
    for img, x, y in placements:
        canvas.paste(img, (x, y))
    
    # Save cluster
    canvas.save(output_file)
    print(f"Cluster image saved to {output_file}")
    print(f"Total albums: {len(placements)}")
    print(f"Canvas size: {canvas_width}x{canvas_height}")

if __name__ == "__main__":
    albums, artists = parse_index_file("index.txt")
    
    if albums:
        print(f"Found {len(albums)} albums")
        build_cluster(albums)
    else:
        print("No albums found in index file")
