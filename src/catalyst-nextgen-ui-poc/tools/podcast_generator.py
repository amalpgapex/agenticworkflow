
from typing import Dict, Any, Optional, Callable
from tools.base import AgenticTool
from openai import OpenAI
from pathlib import Path
from datetime import datetime

class PodcastGeneratorTool(AgenticTool):
    """Generate audio podcast from text using OpenAI TTS"""

    def __init__(self, api_key: str):
        super().__init__("podcast_generator", "Generate audio podcast from text")
        self.client = OpenAI(api_key=api_key)
        self.output_dir = Path("generated_audio")
        self.output_dir.mkdir(exist_ok=True)

    def execute(self, context: Dict[str, Any], streaming_callback: Optional[Callable] = None) -> str:
        """Generate podcast audio from text"""
        script = context.get('previous_output', context.get('document_content', ''))

        if not script or len(script.strip()) < 10:
            return "Error: No content available to convert to speech"

        if streaming_callback:
            streaming_callback("🎙️ Preparing podcast script for audio generation...")

        try:
            voice = context.get('parameters', {}).get('voice', 'alloy')
            if streaming_callback:
                streaming_callback(f"🎙️ Generating podcast audio with voice: {voice}...")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            audio_filename = f"podcast_{timestamp}.mp3"
            audio_path = self.output_dir / audio_filename

            response = self.client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=script[:4096]
            )
            response.stream_to_file(str(audio_path))

            if streaming_callback:
                streaming_callback(f"✅ Podcast audio generated successfully!\n\nAudio file: {audio_filename}\nVoice: {voice}\nDuration: ~{len(script) // 150} seconds (estimated)")

            return f"AUDIO_FILE:{audio_filename}"

        except Exception as e:
            error_msg = f"Error generating podcast audio: {str(e)}"
            if streaming_callback:
                streaming_callback(error_msg)
            return error_msg
