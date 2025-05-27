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
    from elevenlabs import VoiceSettings, save
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
        voice_settings: Optional[VoiceSettings] = None,
        output_format: str = "mp3_44100_128",
        enable_logging: Optional[bool] = None,
        optimize_streaming_latency: Optional[int] = None,
        language_code: Optional[str] = None,
        apply_text_normalization: Optional[str] = None,
        apply_language_text_normalization: Optional[bool] = None,
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
            voice_settings (VoiceSettings, optional): The voice settings to use.
                Should be a VoiceSettings instance from elevenlabs.
                See the
                `Docs: <https://elevenlabs.io/docs/speech-synthesis/voice-settings>`
                for reference.
            output_format (str, optional): The voice output format to use. 
                Options are available depending on the Elevenlabs subscription. 
                See the `API page:
                <https://elevenlabs.io/docs/api-reference/text-to-speech>`
                for reference. Defaults to `mp3_44100_128`.
            enable_logging (bool, optional): When enable_logging is set to false 
                zero retention mode will be used for the request. Defaults to None.
            optimize_streaming_latency (int, optional): You can turn on latency 
                optimizations at some cost of quality. Values: 0-4. Defaults to None.
            language_code (str, optional): Language code (ISO 639-1) used to enforce 
                a language for the model. Currently only Turbo v2.5 and Flash v2.5 
                support language enforcement. Defaults to None.
            apply_text_normalization (str, optional): Controls text normalization 
                with three modes: 'auto', 'on', and 'off'. Defaults to None.
            apply_language_text_normalization (bool, optional): Controls language 
                text normalization. Can heavily increase latency. Currently only 
                supported for Japanese. Defaults to None.
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
            
        # validate language_code
        if language_code:
            if model not in ["eleven_turbo_v2_5", "eleven_flash_v2_5"]:
                raise Exception(f"Language code {language_code} is not supported for model {model}. Needs model to be one of ['eleven_turbo_v2_5', 'eleven_flash_v2_5']")

        self.model = model
        
        # Store voice_settings directly
        self.voice_settings = voice_settings
            
        self.output_format = output_format
        self.enable_logging = enable_logging
        self.optimize_streaming_latency = optimize_streaming_latency
        self.language_code = language_code
        self.apply_text_normalization = apply_text_normalization
        self.apply_language_text_normalization = apply_language_text_normalization

        SpeechService.__init__(self, transcription_model=transcription_model, **kwargs)

    def generate_from_text(
        self,
        text: str,
        cache_dir: Optional[str] = None,
        path: Optional[str] = None,
        # Per-request overrides
        voice_settings: Optional[VoiceSettings] = None,
        enable_logging: Optional[bool] = None,
        optimize_streaming_latency: Optional[int] = None,
        language_code: Optional[str] = None,
        seed: Optional[int] = None,
        previous_text: Optional[str] = None,
        next_text: Optional[str] = None,
        previous_request_ids: Optional[List[str]] = None,
        next_request_ids: Optional[List[str]] = None,
        apply_text_normalization: Optional[str] = None,
        apply_language_text_normalization: Optional[bool] = None,
        **kwargs,
    ) -> dict:
        if cache_dir is None:
            cache_dir = self.cache_dir  # type: ignore

        input_text = remove_bookmarks(text)
        # Determine final parameters (per-request overrides or instance defaults)
        final_voice_settings = voice_settings or self.voice_settings
        final_enable_logging = enable_logging if enable_logging is not None else self.enable_logging
        final_optimize_streaming_latency = optimize_streaming_latency if optimize_streaming_latency is not None else self.optimize_streaming_latency
        final_language_code = language_code or self.language_code
        final_apply_text_normalization = apply_text_normalization or self.apply_text_normalization
        final_apply_language_text_normalization = apply_language_text_normalization if apply_language_text_normalization is not None else self.apply_language_text_normalization

        input_data = {
            "input_text": input_text,
            "service": "elevenlabs",
            "config": {
                "model": self.model,
                "voice_id": self.voice_id,
                "voice_name": self.voice_name,
                "voice_settings": final_voice_settings.model_dump() if final_voice_settings else None,
                "output_format": self.output_format,
                "enable_logging": final_enable_logging,
                "optimize_streaming_latency": final_optimize_streaming_latency,
                "language_code": final_language_code,
                "seed": seed,
                "previous_text": previous_text,
                "next_text": next_text,
                "previous_request_ids": previous_request_ids,
                "next_request_ids": next_request_ids,
                "apply_text_normalization": final_apply_text_normalization,
                "apply_language_text_normalization": final_apply_language_text_normalization,
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
            # Use the new client API for text-to-speech with all available parameters
            # Use per-request overrides if provided, otherwise use instance defaults
            audio = self.client.text_to_speech.convert(
                text=input_text,
                voice_id=self.voice_id,
                model_id=self.model,
                output_format=self.output_format,
                voice_settings=final_voice_settings,
                enable_logging=final_enable_logging,
                optimize_streaming_latency=final_optimize_streaming_latency,
                language_code=final_language_code,
                seed=seed,
                previous_text=previous_text,
                next_text=next_text,
                previous_request_ids=previous_request_ids,
                next_request_ids=next_request_ids,
                apply_text_normalization=final_apply_text_normalization,
                apply_language_text_normalization=final_apply_language_text_normalization,
            )
            
            # Save the audio to file using the correct path
            if cache_dir is None:
                raise ValueError("cache_dir cannot be None")
            full_audio_path = Path(cache_dir) / audio_path
            save(audio, str(full_audio_path))
            
        except Exception as e:
            logger.error(f"ElevenLabs TTS failed: {e}")
            raise Exception(f"Failed to generate speech: {e}")

        json_dict = {
            "input_text": text,
            "input_data": input_data,
            "original_audio": audio_path,
        }

        return json_dict
