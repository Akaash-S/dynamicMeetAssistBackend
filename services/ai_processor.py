import google.generativeai as genai
import os
import json
import re
from typing import Dict, List, Optional

class AIProcessor:
    def __init__(self):
        self.api_key = os.getenv('GEMINI_API_KEY')
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is required")
        
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
    
    def extract_timeline(self, transcript: str, duration: int = 0) -> Dict:
        """
        Extract minute-by-minute timeline from transcript
        """
        try:
            prompt = f"""
            Analyze this meeting transcript and create a detailed minute-by-minute timeline.
            
            TRANSCRIPT:
            {transcript}
            
            INSTRUCTIONS:
            1. Create timeline entries for significant events, discussions, decisions, and action items
            2. Estimate timestamps based on content flow and natural conversation pace
            3. Each entry should have: timestamp (in minutes:seconds format), event_type, title, and detailed content
            4. Event types: "discussion", "decision", "task_assignment", "question", "action_item", "presentation"
            5. Make timestamps realistic and well-distributed throughout the meeting
            
            RETURN FORMAT (JSON):
            {{
                "timeline": [
                    {{
                        "timestamp": "00:30",
                        "timestamp_minutes": 0.5,
                        "event_type": "discussion",
                        "title": "Meeting Introduction",
                        "content": "Team members introduced themselves and outlined the agenda",
                        "participants": ["Speaker A", "Speaker B"]
                    }}
                ],
                "summary": "Brief overall meeting summary",
                "key_decisions": ["Decision 1", "Decision 2"],
                "action_items": ["Action 1", "Action 2"]
            }}
            
            Ensure the JSON is valid and properly formatted.
            """
            
            print("🤖 Generating timeline with Gemini AI...")
            response = self.model.generate_content(prompt)
            
            # Parse the response
            timeline_data = self._parse_json_response(response.text)
            
            if timeline_data:
                print(f"✅ Generated {len(timeline_data.get('timeline', []))} timeline entries")
                return {
                    'success': True,
                    'data': timeline_data
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to parse timeline response'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Timeline generation error: {str(e)}'
            }
    
    def extract_tasks(self, transcript: str, timeline_data: Optional[Dict] = None) -> Dict:
        """
        Extract actionable tasks from transcript and timeline
        """
        try:
            context = ""
            if timeline_data and timeline_data.get('timeline'):
                context = f"\nTIMELINE CONTEXT:\n{json.dumps(timeline_data['timeline'], indent=2)}"
            
            prompt = f"""
            Analyze this meeting transcript and extract all actionable tasks and to-do items.
            
            TRANSCRIPT:
            {transcript}
            {context}
            
            INSTRUCTIONS:
            1. Identify all tasks, action items, assignments, and follow-ups mentioned
            2. For each task, determine: description, assigned person, deadline, priority, and dependencies
            3. If no specific person is assigned, mark as "Unassigned"
            4. If no deadline is mentioned, suggest a reasonable one based on task urgency
            5. Priority levels: "high", "medium", "low"
            6. Include both explicit tasks and implied action items
            
            RETURN FORMAT (JSON):
            {{
                "tasks": [
                    {{
                        "title": "Prepare market analysis report",
                        "description": "Detailed description of what needs to be done",
                        "assigned_to": "John Smith",
                        "deadline": "2024-01-25",
                        "priority": "high",
                        "status": "pending",
                        "dependencies": ["Budget approval", "Data collection"],
                        "estimated_hours": 8,
                        "category": "research"
                    }}
                ],
                "task_summary": {{
                    "total_tasks": 5,
                    "high_priority": 2,
                    "medium_priority": 2,
                    "low_priority": 1,
                    "assigned_tasks": 4,
                    "unassigned_tasks": 1
                }}
            }}
            
            Ensure the JSON is valid and properly formatted.
            """
            
            print("🎯 Extracting tasks with Gemini AI...")
            response = self.model.generate_content(prompt)
            
            # Parse the response
            tasks_data = self._parse_json_response(response.text)
            
            if tasks_data:
                print(f"✅ Extracted {len(tasks_data.get('tasks', []))} tasks")
                return {
                    'success': True,
                    'data': tasks_data
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to parse tasks response'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Task extraction error: {str(e)}'
            }
    
    def generate_meeting_summary(self, transcript: str, timeline_data: Optional[Dict] = None, tasks_data: Optional[Dict] = None) -> Dict:
        """
        Generate comprehensive meeting summary
        """
        try:
            context = ""
            if timeline_data:
                context += f"\nTIMELINE:\n{json.dumps(timeline_data.get('timeline', []), indent=2)}"
            if tasks_data:
                context += f"\nTASKS:\n{json.dumps(tasks_data.get('tasks', []), indent=2)}"
            
            prompt = f"""
            Create a comprehensive meeting summary based on the transcript and extracted data.
            
            TRANSCRIPT:
            {transcript}
            {context}
            
            INSTRUCTIONS:
            1. Provide an executive summary of the meeting
            2. List key decisions made
            3. Highlight important discussions and their outcomes
            4. Identify any unresolved issues or questions
            5. Note participant contributions and engagement
            6. Assess meeting effectiveness and outcomes
            
            RETURN FORMAT (JSON):
            {{
                "executive_summary": "Brief overview of the meeting purpose and outcomes",
                "key_decisions": [
                    {{
                        "decision": "Budget approved for Q4",
                        "rationale": "Strong market projections",
                        "impact": "Enables expansion plans"
                    }}
                ],
                "important_discussions": [
                    {{
                        "topic": "Market expansion strategy",
                        "outcome": "Agreed to focus on European markets first",
                        "participants": ["CEO", "Marketing Director"]
                    }}
                ],
                "unresolved_issues": [
                    "Legal review timeline unclear",
                    "Resource allocation pending"
                ],
                "participant_insights": {{
                    "most_active": "John Smith",
                    "key_contributors": ["Jane Doe", "Mike Johnson"],
                    "total_participants": 5
                }},
                "meeting_effectiveness": {{
                    "score": 8.5,
                    "strengths": ["Clear agenda", "Good participation"],
                    "improvements": ["Better time management", "More concrete deadlines"]
                }},
                "next_steps": [
                    "Schedule follow-up meeting",
                    "Distribute action items",
                    "Begin market research"
                ]
            }}
            
            Ensure the JSON is valid and properly formatted.
            """
            
            print("📋 Generating meeting summary with Gemini AI...")
            response = self.model.generate_content(prompt)
            
            # Parse the response
            summary_data = self._parse_json_response(response.text)
            
            if summary_data:
                print("✅ Generated comprehensive meeting summary")
                return {
                    'success': True,
                    'data': summary_data
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to parse summary response'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': f'Summary generation error: {str(e)}'
            }
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Parse JSON from AI response, handling common formatting issues
        """
        try:
            # Remove markdown code blocks if present
            cleaned_text = re.sub(r'```json\s*|\s*```', '', response_text.strip())
            
            # Try to find JSON content between braces
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            
            # If no braces found, try parsing the whole cleaned text
            return json.loads(cleaned_text)
            
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Response text: {response_text[:500]}...")
            return None
        except Exception as e:
            print(f"❌ Unexpected parsing error: {e}")
            return None
    
    def get_ai_health(self) -> Dict:
        """Check if AI service is healthy"""
        try:
            # Test API connectivity with a simple prompt
            test_response = self.model.generate_content("Hello, respond with 'OK' if you're working.")
            
            return {
                'service': 'ai_processor',
                'status': 'healthy' if test_response.text else 'unhealthy',
                'api_key_configured': bool(self.api_key),
                'model': 'gemini-2.0-flash-exp'
            }
            
        except Exception as e:
            return {
                'service': 'ai_processor',
                'status': 'unhealthy',
                'error': str(e),
                'api_key_configured': bool(self.api_key)
            }

# Global AI processor instance
ai_processor = AIProcessor()
