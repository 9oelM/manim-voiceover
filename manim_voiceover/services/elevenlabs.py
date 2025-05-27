import os
import sys
from pathlib import Path
from typing import List, Optional, Union

from dotenv import find_dotenv, load_dotenv
from manim import logger

from manim_voiceover.helper import create_dotenv_file, remove_bookmarks
from manim_voiceover.services.base import SpeechService

try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import save
except ImportError:
    logger.error(
        'Missing packages. Run `pip install "manim-voiceover[elevenlabs]"` '
        "to use ElevenLabs API."
    )


load_dotenv(find_dotenv(usecwd=True))


def create_dotenv_elevenlabs():
    logger.info(
        "Check out https://voiceover.manim.community/en/stable/services.html#elevenlabs"
        " to learn how to create an account and get your subscription key."
    )
    try:
        os.environ["ELEVEN_API_KEY"]
    except KeyError:
        if not create_dotenv_file(["ELEVEN_API_KEY"]):
            raise Exception(
                "The environment variables ELEVEN_API_KEY are not set. "
                "Please set them or create a .env file with the variables."
            )
        logger.info("The .env file has been created. Please run Manim again.")
        sys.exit()


create_dotenv_elevenlabs()


class ElevenLabsService(SpeechService):
    """Speech service for ElevenLabs API."""

    def __init__(
        self,
        voice_name: Optional[str] = None,
        voice_id: Optional[str] = None,
        model: str = "eleven_multilingual_v2",
        voice_settings: Optional[dict] = None,
        output_format: str = "mp3_44100_128",
        transcription_model: str = "base",
        **kwargs,
    ):
        """
        Args:
            voice_name (str, optional): The name of the voice to use.
                See the
                `API page <https://elevenlabs.io/docs/api-reference/text-to-speech>`
                for reference. Defaults to `None`.
                If none of `voice_name` or `voice_id` is be provided,
                it uses default available voice.
            voice_id (str, Optional): The id of the voice to use.
                See the
                `API page <https://elevenlabs.io/docs/api-reference/text-to-speech>`
                for reference. Defaults to `None`. If none of `voice_name`
                or `voice_id` must be provided, it uses default available voice.
            model (str, optional): The name of the model to use. See the `API
                page: <https://elevenlabs.io/docs/api-reference/text-to-speech>`
                for reference. Defaults to `eleven_multilingual_v2`
            voice_settings (dict, optional): The voice settings to use.
                See the
                `Docs: <https://elevenlabs.io/docs/speech-synthesis/voice-settings>`
                for reference.
                It is a dictionary, with keys: `stability` (Required, number),
                `similarity_boost` (Required, number),
                `style` (Optional, number, default 0), `use_speaker_boost`
                (Optional, boolean, True).
            output_format (str, optional): The voice output format to use. 
                Options are available depending on the Elevenlabs subscription. 
                See the `API page:
                <https://elevenlabs.io/docs/api-reference/text-to-speech>`
                for reference. Defaults to `mp3_44100_128`.
        """
        # Initialize the ElevenLabs client
        api_key = os.getenv("ELEVEN_API_KEY")
        self.client = ElevenLabs(api_key=api_key)
        
        if not voice_name and not voice_id:
            logger.warn(
                "None of `voice_name` or `voice_id` provided. "
                "Will be using default voice."
            )

        # Get available voices using the new API
        try:
            voices_response = self.client.voices.get_all()
            available_voices = voices_response.voices
        except Exception as e:
            logger.error(f"Failed to get voices: {e}")
            raise Exception("Failed to get voices from ElevenLabs API.")

        selected_voice = None
        if voice_name:
            selected_voice = next((v for v in available_voices if v.name == voice_name), None)
        elif voice_id:
            selected_voice = next((v for v in available_voices if v.voice_id == voice_id), None)

        if selected_voice:
            self.voice_id = selected_voice.voice_id
            self.voice_name = selected_voice.name
        else:
            if available_voices:
                logger.warn(
                    "Given `voice_name` or `voice_id` not found (or not provided). "
                    f"Defaulting to {available_voices[0].name}"
                )
                self.voice_id = available_voices[0].voice_id
                self.voice_name = available_voices[0].name
            else:
                raise Exception("No voices available from ElevenLabs API.")

        self.model = model
        self.voice_settings = voice_settings or {}
        self.output_format = output_format

        SpeechService.__init__(self, transcription_model=transcription_model, **kwargs)

    def generate_from_text(
        self,
        text: str,
        cache_dir: Optional[str] = None,
        path: Optional[str] = None,
        **kwargs,
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir  # type: ignore

        input_text = remove_bookmarks(text)
        input_data = {
            "input_text": input_text,
            "service": "elevenlabs",
            "config": {
                "model": self.model,
                "voice_id": self.voice_id,
                "voice_name": self.voice_name,
                "voice_settings": self.voice_settings,
                "output_format": self.output_format,
            },
        }

        # Check cache
        cached_result = self.get_cached_result(input_data, cache_dir)
        if cached_result is not None:
            return cached_result

        if path is None:
            audio_path = self.get_audio_basename(input_data) + ".mp3"
        else:
            audio_path = path

        try:
            # Use the new client API for text-to-speech
            voice_settings_obj = None
            if self.voice_settings:
                voice_settings_obj = {
                    "stability": self.voice_settings.get("stability", 0.5),
                    "similarity_boost": self.voice_settings.get("similarity_boost", 0.5),
                    "style": self.voice_settings.get("style", 0),
                    "use_speaker_boost": self.voice_settings.get("use_speaker_boost", True),
                }

            audio = self.client.text_to_speech.convert(
                text=input_text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format=self.output_format,
                voice_settings=voice_settings_obj,
            )
            
            # Save the audio to file
            save(audio, str(Path(cache_dir) / audio_path))
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            raise Exception(f"Failed to generate speech: {e}")

        json_dict = {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }

        return json_dict
