import random
import time


class StealthBrowser:
    """Класс для управления stealth-браузером с улучшенной маскировкой"""

    @staticmethod
    def get_random_fingerprint():
        """Генерирует случайный fingerprint браузера"""
        return {
            "user_agent": random.choice(
                [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
                ]
            ),
            "viewport": {
                "width": random.randint(1200, 1400),
                "height": random.randint(800, 1000),
            },
            "device_scale_factor": random.choice([1, 1.5, 2]),
            "geolocation": {
                "longitude": random.uniform(30, 40),
                "latitude": random.uniform(50, 60),
                "accuracy": random.uniform(10, 100),
            },
        }

    @staticmethod
    def human_like_mouse_movement(page):
        """Имитирует человеческое движение мыши"""
        for _ in range(random.randint(2, 5)):
            x = random.randint(0, page.viewport_size["width"])
            y = random.randint(0, page.viewport_size["height"])
            page.mouse.move(x, y)
            time.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    def random_scroll(page):
        """Случайная прокрутка страницы"""
        scroll_height = page.evaluate("document.body.scrollHeight")
        for _ in range(random.randint(1, 3)):
            scroll_to = random.randint(0, scroll_height)
            page.evaluate(f"window.scrollTo(0, {scroll_to})")
            time.sleep(random.uniform(0.5, 2))

    @staticmethod
    def random_actions(page):
        """Случайные действия на странице"""
        actions = [
            lambda: page.keyboard.press("PageDown"),
            lambda: page.keyboard.press("PageUp"),
            lambda: page.keyboard.type(" ", delay=random.uniform(50, 150)),
            lambda: StealthBrowser.human_like_mouse_movement(page),
            lambda: StealthBrowser.random_scroll(page),
        ]
        random.shuffle(actions)
        for action in actions[: random.randint(1, 3)]:
            action()
            time.sleep(random.uniform(0.5, 1.5))
