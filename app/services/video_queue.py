from typing import List, Dict

# Очередь видео хранится в памяти (можно расширить на БД при необходимости)
_video_queue: List[Dict] = []
_video_mode_enabled: bool = False


def enable_video_mode() -> None:
    global _video_mode_enabled
    _video_mode_enabled = True


def disable_video_mode() -> None:
    global _video_mode_enabled
    _video_mode_enabled = False


def is_video_mode() -> bool:
    return _video_mode_enabled


def add_video(file_id: str, caption: str) -> None:
    _video_queue.append({
        'file_id': file_id,
        'caption': caption,
    })


def pop_next_video() -> Dict | None:
    if _video_queue:
        return _video_queue.pop(0)
    return None


def count_videos() -> int:
    return len(_video_queue)


def clear_video_queue() -> None:
    _video_queue.clear()

