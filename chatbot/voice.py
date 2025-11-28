"""
Voice AI Service using Groq Whisper and ElevenLabs
===================================================
Handles voice-to-text and text-to-voice operations
"""

import os
import io
import base64
from typing import Optional
from groq import Groq
import logging

logger = logging.getLogger(__name__)

# ElevenLabs will be imported conditionally
try:
    from elevenlabs.client import ElevenLabs
    from elevenlabs import Voice, VoiceSettings
    ELEVENLABS_AVAILABLE = True
except ImportError:
    try:
        # Fallback for older versions
        from elevenlabs import generate, set_api_key, Voice, VoiceSettings
        ELEVENLABS_AVAILABLE = True
    except ImportError:
        ELEVENLABS_AVAILABLE = False
        logger.warning("ElevenLabs not installed. Text-to-speech will be disabled.")


class VoiceAIService:
    """Service for voice AI operations"""
    
    def __init__(self):
        """Initialize Groq client for transcription and ElevenLabs for TTS"""
        # Initialize service state
        self.groq_client = None
        self.transcription_enabled = False
        self.tts_enabled = False
        self.elevenlabs_client = None
        self.initialization_errors = []
        
        # Groq for transcription
        groq_api_key = os.getenv('GROQ_API_KEY_TWO') or os.getenv('GROQ_API_KEY')
        if groq_api_key:
            try:
                self.groq_client = Groq(api_key=groq_api_key)
                self.transcription_model = os.getenv('VOICE_TRANSCRIPTION_MODEL', 'whisper-large-v3')
                self.max_audio_size = int(os.getenv('VOICE_MAX_AUDIO_SIZE', '25')) * 1024 * 1024  # Convert MB to bytes
                self.transcription_enabled = True
                logger.info("Groq Whisper transcription enabled")
            except Exception as e:
                error_msg = f"Failed to initialize Groq client: {e}"
                self.initialization_errors.append(error_msg)
                logger.error(error_msg)
        else:
            error_msg = "GROQ_API_KEY_TWO or GROQ_API_KEY environment variable not found. Transcription disabled."
            self.initialization_errors.append(error_msg)
            logger.warning(error_msg)
        
        # ElevenLabs for TTS
        if ELEVENLABS_AVAILABLE:
            elevenlabs_api_key = os.getenv('ELEVENLABS_API_KEY')
            if elevenlabs_api_key:
                try:
                    # Try new client-based approach
                    self.elevenlabs_client = ElevenLabs(api_key=elevenlabs_api_key)
                    self.tts_enabled = True
                    logger.info("ElevenLabs TTS enabled (new client)")
                except Exception as e:
                    # Fallback to old approach
                    try:
                        set_api_key(elevenlabs_api_key)
                        self.tts_enabled = True
                        logger.info("ElevenLabs TTS enabled (legacy client)")
                    except Exception as e2:
                        error_msg = f"Failed to initialize ElevenLabs client: {e}, {e2}"
                        self.initialization_errors.append(error_msg)
                        logger.warning(error_msg)
                
                if self.tts_enabled:
                    self.voice_id = os.getenv('ELEVENLABS_VOICE_ID', 'EXAVITQu4vr4xnSDxMaL')  # Default: Bella
            else:
                logger.info("ELEVENLABS_API_KEY not set. TTS disabled (this is optional).")
        else:
            logger.info("ElevenLabs library not available. TTS disabled (this is optional).")
        
        # Log final status
        if self.transcription_enabled or self.tts_enabled:
            logger.info(f"Voice AI Service initialized - Transcription: {'✓' if self.transcription_enabled else '✗'}, TTS: {'✓' if self.tts_enabled else '✗'}")
        else:
            logger.warning("Voice AI Service initialized with limited functionality. Check API keys.")
    
    def transcribe_audio(
        self, 
        audio_file: bytes, 
        filename: str = "audio.mp3",
        language: str = "en"
    ) -> str:
        """
        Transcribe audio to text using Groq Whisper
        
        Args:
            audio_file: Audio file bytes
            filename: Original filename (for format detection)
            language: Language code (default: en)
            
        Returns:
            Transcribed text
        """
        if not self.transcription_enabled:
            raise ValueError("Voice transcription is not available. Please check your Groq API key configuration.")
        
        try:
            # Validate file size
            if len(audio_file) > self.max_audio_size:
                raise ValueError(f"Audio file too large. Maximum size is {self.max_audio_size / (1024*1024):.0f}MB")
            
            # Basic file validation
            if len(audio_file) == 0:
                raise ValueError("Audio file is empty")
            
            # Create file-like object
            audio_io = io.BytesIO(audio_file)
            audio_io.name = filename
            
            # Transcribe using Groq Whisper
            transcription = self.groq_client.audio.transcriptions.create(
                file=(filename, audio_io),
                model=self.transcription_model,
                language=language,
                response_format="text"
            )
            
            # Validate transcription result
            if not transcription or not transcription.strip():
                logger.warning("Transcription returned empty result")
                return "I couldn't understand the audio. Please try speaking more clearly."
            
            logger.info(f"Audio transcribed successfully: {len(transcription)} characters")
            return transcription.strip()
            
        except ValueError as e:
            # Re-raise validation errors as-is
            logger.error(f"Validation error in transcription: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise ValueError(f"Failed to transcribe audio: {str(e)}")
    
    def synthesize_speech(
        self, 
        text: str, 
        voice_id: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Convert text to speech using ElevenLabs
        
        Args:
            text: Text to convert to speech
            voice_id: Optional voice ID override
            
        Returns:
            Audio bytes or None if TTS is disabled
        """
        if not self.tts_enabled:
            logger.info("TTS is disabled. Returning None (this is optional).")
            return None
        
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return None
        
        # Limit text length to prevent API issues
        max_length = 5000
        if len(text) > max_length:
            text = text[:max_length] + "..."
            logger.warning(f"Text truncated to {max_length} characters for TTS")
        
        try:
            if self.elevenlabs_client:
                # Use new client-based approach
                audio = self.elevenlabs_client.generate(
                    text=text,
                    voice=Voice(
                        voice_id=voice_id or self.voice_id,
                        settings=VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75,
                            style=0.0,
                            use_speaker_boost=True
                        )
                    ),
                    model="eleven_multilingual_v2"
                )
            else:
                # Use old approach
                audio = generate(
                    text=text,
                    voice=Voice(
                        voice_id=voice_id or self.voice_id,
                        settings=VoiceSettings(
                            stability=0.5,
                            similarity_boost=0.75,
                            style=0.0,
                            use_speaker_boost=True
                        )
                    ),
                    model="eleven_multilingual_v2"
                )
            
            # Convert generator to bytes
            if hasattr(audio, '__iter__'):
                audio_bytes = b''.join(audio)
            else:
                audio_bytes = audio
            
            if len(audio_bytes) == 0:
                logger.warning("TTS returned empty audio")
                return None
            
            logger.info(f"Speech synthesized successfully: {len(audio_bytes)} bytes")
            return audio_bytes
            
        except Exception as e:
            logger.error(f"Error synthesizing speech: {e}")
            return None
    
    def get_service_status(self) -> dict:
        """
        Get current service status and capabilities
        
        Returns:
            Dict with service status information
        """
        return {
            "transcription_enabled": self.transcription_enabled,
            "tts_enabled": self.tts_enabled,
            "initialization_errors": self.initialization_errors,
            "max_audio_size_mb": self.max_audio_size / (1024 * 1024) if hasattr(self, 'max_audio_size') else 0
        }
    
    def process_voice_message(
        self,
        audio_file: bytes,
        filename: str,
        chatbot_service,
        user_id: str,
        session_id: Optional[str] = None,
        include_audio_response: bool = False
    ) -> dict:
        """
        Process voice input end-to-end: transcribe -> chatbot -> optional TTS
        
        Args:
            audio_file: Audio file bytes
            filename: Original filename
            chatbot_service: ChatbotService instance
            user_id: User ID
            session_id: Optional session ID
            include_audio_response: Whether to include audio response
            
        Returns:
            Dict with transcription, response, session_id, and optional audio
        """
        try:
            # Step 1: Transcribe audio
            transcription = self.transcribe_audio(audio_file, filename)
            
            # Step 2: Process through chatbot
            chatbot_response = chatbot_service.process_message(
                message=transcription,
                session_id=session_id,
                stream=False
            )
            
            result = {
                "transcription": transcription,
                "response": chatbot_response["response"],
                "session_id": chatbot_response["session_id"],
                "sources": chatbot_response.get("sources", [])
            }
            
            # Step 3: Optional TTS
            if include_audio_response:
                if self.tts_enabled:
                    audio_response = self.synthesize_speech(chatbot_response["response"])
                    if audio_response:
                        result["audio_response"] = base64.b64encode(audio_response).decode('utf-8')
                    else:
                        result["tts_error"] = "Failed to generate audio response"
                else:
                    result["tts_error"] = "Text-to-speech is not available"
            
            return result
            
        except ValueError as e:
            # User-friendly validation errors
            logger.error(f"Validation error in voice processing: {e}")
            raise e
        except Exception as e:
            logger.error(f"Error processing voice message: {e}")
            raise ValueError(f"Failed to process voice message: {str(e)}")


# Global instance
_voice_service = None


def get_voice_service() -> VoiceAIService:
    """Get or create global Voice AI service instance"""
    global _voice_service
    if _voice_service is None:
        _voice_service = VoiceAIService()
    return _voice_service
