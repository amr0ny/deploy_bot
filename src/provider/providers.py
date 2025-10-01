import asyncio
import os
import json
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL
import logging

from src.provider.interfaces import AsyncProvider


class AsyncYtDlpProvider(AsyncProvider):
    """
    Асинхронный провайдер для работы с yt-dlp
    """

    def __init__(self, download_path: str = "downloads", quality: str = "best"):
        self.download_path = download_path
        self.quality = quality
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

    def _get_ydl_opts(self, output_template: Optional[str] = None) -> Dict[str, Any]:
        if output_template is None:
            output_template = os.path.join(
                self.download_path,
                '%(title).100s.%(ext)s'
            )

        return {
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
            'extractor_args': {
                'tiktok:format': 'download_addr'
            }
        }

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

        Returns:
            Путь к файлу или информация о видео
        """
        try:
            # Обновляем качество если передано в kwargs
            quality = kwargs.get('quality', self.quality)
            custom_filename = kwargs.get('custom_filename')
            audio_only = kwargs.get('audio_only', False)

            if audio_only:
                return await self.download_audio_only(url, custom_filename)
            elif download:
                return await self.download_video(url, custom_filename, quality)
            else:
                return await self.get_video_info(url)

        except Exception as e:
            self.logger.error(f"Ошибка в retrieve: {str(e)}")
            return None

    async def get_video_info(self, url: str) -> Optional[Dict[str, Any]]:
        try:
            def extract_info():
                with YoutubeDL({'quiet': True}) as ydl:
                    return ydl.extract_info(url, download=False)

            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, extract_info)

            self.logger.info(f"Получена информация о видео: {info.get('title', 'Unknown')}")
            return info

        except Exception as e:
            self.logger.error(f"Ошибка при получении информации: {str(e)}")
            return None

    async def download_video(self, url: str, custom_filename: Optional[str] = None, quality: Optional[str] = None) -> \
    Optional[str]:
        try:
            output_template = None
            if custom_filename:
                output_template = os.path.join(
                    self.download_path,
                    f"{custom_filename}.%(ext)s"
                )

            ydl_opts = self._get_ydl_opts(output_template)
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

    async def download_audio_only(self, url: str, custom_filename: Optional[str] = None) -> Optional[str]:
        try:
            output_template = None
            if custom_filename:
                output_template = os.path.join(
                    self.download_path,
                    f"{custom_filename}.%(ext)s"
                )

            ydl_opts = self._get_ydl_opts(output_template)
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