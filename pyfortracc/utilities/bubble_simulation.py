import numpy as np
import matplotlib.pyplot as plt
import os
import warnings
warnings.filterwarnings("ignore")

def draw_bubble(frame, center_x, center_y, radius_x, radius_y, alpha=1.0):
    """
    pyfortracc bubble simulation
    """
    h, w = frame.shape
    # Calculate bounds for optimization
    x_min = max(0, int(center_x - radius_x - 1))
    x_max = min(w, int(center_x + radius_x + 2))
    y_min = max(0, int(center_y - radius_y - 1))
    y_max = min(h, int(center_y + radius_y + 2))
    
    # Criar grid apenas na região necessária
    y, x = np.ogrid[y_min:y_max, x_min:x_max]
    
    # Equação da elipse
    mask = ((x - center_x) / radius_x) ** 2 + ((y - center_y) / radius_y) ** 2 <= 1
    frame[y_min:y_max, x_min:x_max][mask] = alpha

def bubble_simulation(n_frames=25, size=50, seed=42, dir="bubble_simulation"):
    """
    Generates a sequence of bubbles moving, growing, shrinking,
    splitting and merging, in a 50x50 matrix.
    Now the bubble starts at the bottom-right corner and moves to the top-left corner.
    """
    os.makedirs(dir, exist_ok=True)
    rng = np.random.default_rng(seed)

    # Initialize the main bubble at the bottom-right corner (with left shift)
    left_shift = 8
    start_r = 6
    start_x = max(start_r, size - 1 - start_r - left_shift)
    start_y = size - 1 - start_r
    
    objects = [
        {"x": start_x, "y": start_y, "r": start_r, "dr": 0.3, "vx": -0.8, "vy": -0.8, "a": 1.0}
    ]

    # Event points
    n_frames = 30
    eject_frame = 5
    fuse_frame = 20
    freeze_frame = max(eject_frame + 1, fuse_frame - 2)
    steer_frame = eject_frame + max(1, (fuse_frame - eject_frame) // 2)
    fade_start = 26
    fade_duration = max(1, n_frames - fade_start)
    alpha = 1.0
    fused = False
    fused_r_initial = None

    for t in range(n_frames):
        frame = np.zeros((size, size), dtype=np.float32)

        # Split: a partir do frame 5, a bolha se divide em duas
        if t == eject_frame and len(objects) == 1:
            o = objects[0]
            # main keeps moving; eject is smaller and initially slower to lag behind
            main_r = o["r"] * 0.95
            eject_r = o["r"] * 0.6

            main_vx = o["vx"] * 1.0
            main_vy = o["vy"] * 1.0
            # reduced speed so it stays behind, plus a slight lateral push
            perp_x = -o["vy"]
            perp_y = o["vx"]
            norm = np.hypot(perp_x, perp_y)
            if norm == 0:
                nx, ny = 0.0, 0.0
            else:
                nx, ny = perp_x / norm, perp_y / norm

            eject_vx = o["vx"] * 0.4 + nx * 0.4
            eject_vy = o["vy"] * 0.4 + ny * 0.4

            objects = [
                {"x": o["x"], "y": o["y"], "r": main_r, "dr": o["dr"], "vx": main_vx, "vy": main_vy, "a": 1.0},
                {"x": o["x"] + 6, "y": o["y"] + 6, "r": eject_r, "dr": -0.1, "vx": eject_vx, "vy": eject_vy, "a": 1.0}
            ]

        # Merge: no frame 20, as duas bolhas se fundem novamente
        if t == fuse_frame and len(objects) == 2:
            o1, o2 = objects[0], objects[1]
            # Calcula as propriedades da bolha fundida
            x_new = (o1["x"] * o1["r"] + o2["x"] * o2["r"]) / (o1["r"] + o2["r"])
            y_new = (o1["y"] * o1["r"] + o2["y"] * o2["r"]) / (o1["r"] + o2["r"])
            r_new = min(12, o1["r"] + o2["r"])
            vx_new = (o1["vx"] + o2["vx"]) / 2
            vy_new = (o1["vy"] + o2["vy"]) / 2

            objects = [{"x": x_new, "y": y_new, "r": r_new, "dr": 0.3, "vx": vx_new, "vy": vy_new, "a": 1.0}]
            fused = True
            fused_r_initial = r_new

        # after fusion, inicia fade apenas a partir de fade_start
        if fused and t >= fade_start:
            # progress from 1..fade_duration across frames fade_start..n_frames-1
            progress = float(t - fade_start + 1) / float(fade_duration)
            progress = min(1.0, max(0.0, progress))
            alpha = float(max(0.0, 1.0 - progress))
            # reduzir raio da bolha fundida proporcionalmente
            if len(objects) == 1:
                objects[0]["r"] = fused_r_initial * max(0.0, 1.0 - progress)

        # freeze main a partir de freeze_frame para "esperar" a ejetada
        if t == freeze_frame and len(objects) >= 1:
            # assume objects[0] is main
            objects[0]["vx"] = 0.0
            objects[0]["vy"] = 0.0

        # steering: no steer_frame ajustar velocidade da ejetada para voltar à main e sincronizar chegada
        if t == steer_frame and len(objects) == 2:
            main = objects[0]
            eject = objects[1]
            remaining = fuse_frame - t
            if remaining > 0:
                dx = main["x"] - eject["x"]
                dy = main["y"] - eject["y"]
                # define velocidade necessária para chegar em fuse_frame
                eject_vx = dx / remaining
                eject_vy = dy / remaining
                eject["vx"] = eject_vx
                eject["vy"] = eject_vy

        # At frame 15, give an upward push to the ejected bubble to move it more upwards
        if t == 15 and len(objects) == 2:
            eject = objects[1]
            eject['vy'] += 0.6
            # eject['vx'] += -0.1
        # Update position, size and shape of each bubble
        for obj in objects:
            # Atualiza a posição
            obj["x"] += obj["vx"]
            obj["y"] += obj["vy"]

            # Ensure bubbles stay within image bounds
            obj["x"] = np.clip(obj["x"], obj["r"], size - 1 - obj["r"])
            obj["y"] = np.clip(obj["y"], obj["r"], size - 1 - obj["r"])

            # Growth / decay
            obj["r"] += obj["dr"]
            if obj["r"] > 8 or obj["r"] < 3:
                obj["dr"] *= -1

            # Shape oscillation
            obj["a"] = 1.0 + 0.3*np.sin(t*0.5 + rng.random())

            # Draw the bubble using a custom function
            draw_bubble(frame, obj["x"], obj["y"], int(obj["r"]*obj["a"]), obj["r"], alpha)

        # Save the frame as PNG
        plt.imsave(f"{dir}/frame_{t:02d}.png", frame, cmap="Blues")

    print(f"\nDataset with {n_frames} frames successfully generated in '{dir}'")