from dataclasses import dataclass


@dataclass
class BrowserConfig:
    headless: bool = True
    disable_blink_features: bool = True
    no_sandbox: bool = True
    disable_web_security: bool = True
    disable_dev_shm: bool = True
    disable_gpu: bool = True
    enable_webgl: bool = True
    hide_scrollbars: bool = True
    mute_audio: bool = True
    window_width: int = 1366
    window_height: int = 768


@dataclass
class TimeoutConfig:
    page_load: int = 30000  # Таймаут загрузки страницы
    wait_for_continue_button: int = 3000
    continue_button: int = 5000  # Таймаут кнопки "Continue"
    form_selector: int = 10000  # Таймаут ожидания формы
    result_load: int = 30000
