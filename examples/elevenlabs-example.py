from manim import *

from manim_voiceover import VoiceoverScene
from manim_voiceover.services.elevenlabs import ElevenLabsService
from elevenlabs import VoiceSettings


class ElevenLabsExample(VoiceoverScene):
    def construct(self):
        # Set speech service using defaults, without voice_name or voice_id
        # If none of voice_name or voice_id is passed, it defaults to the
        # first voice in the list returned by the ElevenLabs API
        #
        # self.set_speech_service(ElevenLabsService())
        #
        # Set speech service using voice_name
        #
        # self.set_speech_service(ElevenLabsService(voice_name="Adam"))
        #
        # Set speech service using voice_id
        #
        # self.set_speech_service(ElevenLabsService(voice_id="29vD33N1CtxCmqQRPOHJ"))

        # Comprehensive example with all available options
        self.set_speech_service(
            ElevenLabsService(
                voice_name="Joel", # change as needed. Example: "Glinda", "Sam", etc
                model="eleven_multilingual_v2",  # or "eleven_flash_v2_5", "eleven_turbo_v2_5"
                voice_settings=VoiceSettings(
                    stability=0.5, 
                    similarity_boost=0.25,
                    style=0.0,
                    use_speaker_boost=True
                ),
                output_format="mp3_44100_128",  # High quality format
                enable_logging=True,  # Enable for history features
            )
        )
        
        circle = Circle()
        square = Square().shift(2 * RIGHT)

        with self.voiceover(text="This circle is drawn as I speak.") as tracker:
            self.play(Create(circle), run_time=tracker.duration)

        with self.voiceover(text="Let's shift it to the left 2 units.") as tracker:
            self.play(circle.animate.shift(2 * LEFT), run_time=tracker.duration)

        # Example of per-request parameter override
        with self.voiceover(
            text="Now, let's transform it into a square.",
            # Override voice settings for this specific request
            voice_settings=VoiceSettings(
                stability=0.5,
                similarity_boost=0.8,
                style=0.2,
                use_speaker_boost=False
            ),
            optimize_streaming_latency=3,  # Max latency optimization for this request
        ) as tracker:
            self.play(Transform(circle, square), run_time=tracker.duration)

        with self.voiceover(text="Thank you for watching."):
            self.play(Uncreate(circle))

        self.wait()
