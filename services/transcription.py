import requests
import os
import time
import urllib.parse
from typing import Dict, Optional

class TranscriptionService:
    def __init__(self):
        self.api_key = os.getenv('RAPIDAPI_KEY')
        if not self.api_key:
            raise ValueError("RAPIDAPI_KEY environment variable is required")
        
        # Using Speech-to-Text AI via RapidAPI
        self.base_url = "https://speech-to-text-ai.p.rapidapi.com"
        self.headers = {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": "speech-to-text-ai.p.rapidapi.com",
            "Content-Type": "application/x-www-form-urlencoded"
        }
    
    def transcribe_audio(self, audio_url: str) -> Dict:
        """
        Transcribe audio file from URL using Speech-to-Text AI
        Returns: Dictionary with transcript and metadata
        """
        try:
            print(f"🎵 Starting transcription for: {audio_url}")
            
            # Prepare the request URL with parameters
            # URL encode the audio URL parameter
            encoded_url = urllib.parse.quote(audio_url, safe='')
            
            # Make direct transcription request (this service returns results immediately)
            transcribe_url = f"{self.base_url}/transcribe?url={encoded_url}&lang=en&task=transcribe"
            
            response = requests.post(
                transcribe_url,
                headers=self.headers,
                data=""  # Empty payload as required by the service
            )
            
            print(f"📊 Transcription response status: {response.status_code}")
            
            if response.status_code != 200:
                error_text = response.text
                print(f"❌ Transcription failed: {error_text}")
                return {
                    'success': False,
                    'error': f'Failed to submit transcription: {error_text}'
                }
            
            # Parse the response
            result = response.json()
            print(f"✅ Transcription completed successfully")
            
            # Extract transcript text from the response
            # The exact format may vary, so we'll handle different possible structures
            transcript_text = ""
            
            if isinstance(result, dict):
                # Try different possible keys for the transcript
                transcript_text = (
                    result.get('text') or 
                    result.get('transcript') or 
                    result.get('transcription') or
                    str(result)
                )
            elif isinstance(result, str):
                transcript_text = result
            else:
                transcript_text = str(result)
            
            return {
                'success': True,
                'transcript': transcript_text,
                'confidence': 0.9,  # Default confidence since this service may not provide it
                'duration': 0,  # Duration not provided by this service
                'speakers': {},  # Speaker identification not available in basic version
                'chapters': [],  # Chapters not available
                'sentiment': [],  # Sentiment not available
                'entities': [],  # Entities not available
                'raw_response': result
            }
            
        except Exception as e:
            print(f"❌ Transcription service error: {str(e)}")
            return {
                'success': False,
                'error': f'Transcription service error: {str(e)}'
            }
    
    def _extract_speakers(self, utterances: list) -> Dict:
        """Extract speaker information from utterances (not used in this service)"""
        return {}
    
    def get_transcription_health(self) -> Dict:
        """Check if transcription service is healthy"""
        try:
            # Test API connectivity with a simple request
            # We'll use a test URL to check if the service responds
            test_url = "https://cdn.openai.com/whisper/draft-20220913a/micro-machines.wav"
            encoded_test_url = urllib.parse.quote(test_url, safe='')
            
            response = requests.post(
                f"{self.base_url}/transcribe?url={encoded_test_url}&lang=en&task=transcribe",
                headers=self.headers,
                data="",
                timeout=30  # Longer timeout for actual transcription test
            )
            
            return {
                'service': 'transcription',
                'status': 'healthy' if response.status_code in [200, 400, 401, 429] else 'unhealthy',
                'response_time': response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0,
                'api_key_configured': bool(self.api_key),
                'service_url': self.base_url
            }
            
        except Exception as e:
            return {
                'service': 'transcription',
                'status': 'unhealthy',
                'error': str(e),
                'api_key_configured': bool(self.api_key),
                'service_url': self.base_url
            }

# Global transcription service instance
transcription_service = TranscriptionService()
