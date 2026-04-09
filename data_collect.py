from pathlib import Path

import cv2

# Папка с видео
INPUT_DIR = Path("Avenue_Dataset")  # замени при необходимости
# Одна папка для всех кадров
OUTPUT_DIR = Path("sample_data")

INTERVAL_SECONDS = 3
VIDEO_EXTS = {".avi", ".mp4", ".mov", ".mkv", ".mpeg"}


def extract_frames(video_path: Path, output_dir: Path):
    cap = cv2.VideoCapture(str(video_path))

    if not cap.isOpened():
        print(f"[ERROR] Не удалось открыть: {video_path}")
        return

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 0:
        print(f"[ERROR] FPS не найден: {video_path}")
        cap.release()
        return

    frame_interval = max(1, int(round(fps * INTERVAL_SECONDS)))

    frame_idx = 0
    saved_idx = 0

    video_name = video_path.stem

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % frame_interval == 0:
            filename = f"{video_name}_frame_{saved_idx:05d}.jpg"
            output_path = output_dir / filename
            cv2.imwrite(str(output_path), frame)
            saved_idx += 1

        frame_idx += 1

    cap.release()
    print(f"[OK] {video_path.name}: сохранено {saved_idx} кадров")


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    video_files = [p for p in INPUT_DIR.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS]

    if not video_files:
        print(f"[INFO] Видео не найдены в {INPUT_DIR.resolve()}")
        return

    print(f"[INFO] Найдено видео: {len(video_files)}")

    for video_path in sorted(video_files):
        extract_frames(video_path, OUTPUT_DIR)

    print("[DONE] Все кадры сохранены в одну папку 🚀")


if __name__ == "__main__":
    main()
