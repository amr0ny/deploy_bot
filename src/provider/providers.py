import asyncio
import os
import json
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
import logging

from src.provider.interfaces import AsyncProvider
from src.repository.proxy import ProxyRepository


class AsyncYtDlpProvider(AsyncProvider):
    """
    Асинхронный провайдер для работы с yt-dlp
    """

    def __init__(
            self,
            download_path: str = "downloads",
            quality: str = "best",
            proxy_repository: Optional[ProxyRepository] = None
    ):
        self.download_path = download_path
        self.quality = quality
        self.proxy_repository = proxy_repository
        self.logger = self._setup_logger()
        os.makedirs(download_path, exist_ok=True)

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger

    async def _get_proxy_config(self) -> Optional[str]:
        """Получает следующий прокси из репозитория"""
        if not self.proxy_repository:
            return None

        try:
            proxy = await self.proxy_repository.get_next_proxy()
            if proxy:
                # Форматируем прокси в нужном для yt-dlp формате
                if proxy.username and proxy.password:
                    proxy_url = f"http://{proxy.username}:{proxy.password}@{proxy.server}"
                else:
                    proxy_url = f"http://{proxy.server}"

                self.logger.info(f"Используется прокси: {proxy.server}")
                return proxy_url
        except Exception as e:
            self.logger.error(f"Ошибка при получении прокси: {e}")

        return None

    def _get_ydl_opts(self, output_template: Optional[str] = None, proxy_url: Optional[str] = None) -> Dict[str, Any]:
        if output_template is None:
            output_template = os.path.join(
                self.download_path,
                '%(title).100s.%(ext)s'
            )

        ydl_opts = {
            'format': self.quality,
            'outtmpl': output_template,
            'quiet': False,
            'no_warnings': False,
            'ignoreerrors': False,
            'logtostderr': False,
            'noplaylist': True,
            'extract_flat': False,
            'writethumbnail': False,
            'writeinfojson': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'consoletitle': False,
            'cookiefile': 'cookies.txt',
            'extractor_args': {
                'tiktok:format': 'download_addr'
            }
        }

        # Добавляем прокси если есть
        if proxy_url:
            ydl_opts['proxy'] = proxy_url

        return ydl_opts

    async def retrieve(self, url: str, download: bool = True, **kwargs) -> Any:
        """
        Основной метод для получения видео или информации о нем

        Args:
            url: Ссылка на видео
            download: Скачивать видео или только получать информацию
            **kwargs: Дополнительные параметры
                - custom_filename: Кастомное имя файла
                - audio_only: Скачивать только аудио
                - quality: Качество видео
                - max_retries: Максимальное количество попыток с разными прокси

        Returns:
            Путь к файлу или информация о видео
        """
        max_retries = kwargs.get('max_retries', 3 if self.proxy_repository else 1)

        for attempt in range(max_retries):
            try:
                # Получаем прокси для этой попытки
                proxy_url = await self._get_proxy_config()

                # Обновляем качество если передано в kwargs
                quality = kwargs.get('quality', self.quality)
                custom_filename = kwargs.get('custom_filename')
                audio_only = kwargs.get('audio_only', False)

                if audio_only:
                    result = await self.download_audio_only(url, custom_filename, proxy_url)
                elif download:
                    result = await self.download_video(url, custom_filename, quality, proxy_url)
                else:
                    result = await self.get_video_info(url, proxy_url)

                if result:
                    return result
                else:
                    self.logger.warning(f"Попытка {attempt + 1} не удалась, пробуем другой прокси...")

            except Exception as e:
                self.logger.warning(f"Попытка {attempt + 1} не удалась: {str(e)}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # Небольшая задержка перед следующей попыткой

        self.logger.error(f"Все {max_retries} попыток скачать {url} не удались")
        return None

    async def get_video_info(self, url: str, proxy_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            def extract_info():
                ydl_opts = {'quiet': True}
                if proxy_url:
                    ydl_opts['proxy'] = proxy_url

                with YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)

            self.logger.info(f"Получена информация о видео: {info.get('title', 'Unknown')}")
            return info

        except Exception as e:
            self.logger.error(f"Ошибка при получении информации: {str(e)}")
            return None

    async def download_video(
            self,
            url: str,
            custom_filename: Optional[str] = None,
            quality: Optional[str] = None,
            proxy_url: Optional[str] = None
    ) -> Optional[str]:
        try:
            output_template = None
            if custom_filename:
                output_template = os.path.join(
                    self.download_path,
                    f"{custom_filename}.%(ext)s"
                )

            ydl_opts = self._get_ydl_opts(output_template, proxy_url)
            if quality:
                ydl_opts['format'] = quality

            def download():
                with YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, download)

            if info and 'requested_downloads' in info and info['requested_downloads']:
                filepath = info['requested_downloads'][0]['filepath']
                self.logger.info(f"Видео успешно скачано: {filepath}")
                return filepath
            else:
                self.logger.error("Не удалось получить путь к скачанному файлу")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при скачивании: {str(e)}")
            return None

    async def download_audio_only(
            self,
            url: str,
            custom_filename: Optional[str] = None,
            proxy_url: Optional[str] = None
    ) -> Optional[str]:
        try:
            output_template = None
            if custom_filename:
                output_template = os.path.join(
                    self.download_path,
                    f"{custom_filename}.%(ext)s"
                )

            ydl_opts = self._get_ydl_opts(output_template, proxy_url)
            ydl_opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192',
                }],
            })

            def download():
                with YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=True)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, download)

            if info and 'requested_downloads' in info and info['requested_downloads']:
                filepath = info['requested_downloads'][0]['filepath']
                self.logger.info(f"Аудио успешно скачано: {filepath}")
                return filepath
            else:
                self.logger.error("Не удалось получить путь к скачанному аудио файлу")
                return None

        except Exception as e:
            self.logger.error(f"Ошибка при скачивании аудио: {str(e)}")
            return None