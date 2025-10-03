# AI Meeting Assistant - Backend API Documentation

## 🚀 Base URL
```
Development: http://localhost:5000
Production: https://your-domain.com
```

## 📋 Complete API Endpoints Reference

### 🔐 Authentication Endpoints

#### Verify User
```http
POST /api/auth/verify
Content-Type: application/json

{
  "firebase_uid": "string",
  "email": "string", 
  "name": "string"
}
```

#### Get User
```http
GET /api/auth/user/{firebase_uid}
```

#### Update User
```http
PUT /api/auth/user/{firebase_uid}
Content-Type: application/json

{
  "name": "string",
  "email": "string"
}
```

---

### 📁 File Upload & Processing

#### Upload Audio File
```http
POST /api/upload/audio
Content-Type: multipart/form-data

Form Data:
- audio: File (mp3, wav, m4a, mp4, webm)
- user_id: string
- title: string (optional)
```

**Response:**
```json
{
  "success": true,
  "meeting_id": "uuid",
  "audio_url": "string",
  "file_size": 1024000,
  "status": "processing",
  "message": "File uploaded successfully. Processing started."
}
```

#### Get Processing Status
```http
GET /api/upload/status/{meeting_id}
```

**Response:**
```json
{
  "meeting_id": "uuid",
  "meeting_status": "processing|completed|failed",
  "title": "string",
  "created_at": "2024-01-01T12:00:00Z",
  "processing_steps": [
    {
      "step": "transcription",
      "status": "completed",
      "progress": 100,
      "error_message": null,
      "started_at": "2024-01-01T12:00:00Z",
      "completed_at": "2024-01-01T12:05:00Z"
    }
  ]
}
```

---

### 🎤 Meeting Management

#### Get All Meetings
```http
GET /api/meetings?user_id={user_id}&page=1&limit=10
```

**Response:**
```json
{
  "meetings": [
    {
      "id": "uuid",
      "title": "Team Meeting",
      "status": "completed",
      "duration": 1800,
      "file_size": 1024000,
      "task_count": 5,
      "timeline_count": 12,
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:30:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 10,
    "total": 25,
    "pages": 3
  }
}
```

#### Get Meeting Details
```http
GET /api/meetings/{meeting_id}
```

#### Get Meeting Timeline
```http
GET /api/meetings/{meeting_id}/timeline
```

**Response:**
```json
{
  "meeting_id": "uuid",
  "timeline": [
    {
      "id": "uuid",
      "timestamp": "05:30",
      "timestamp_minutes": 5.5,
      "event_type": "decision",
      "title": "Budget Approval",
      "content": "Team approved Q4 budget allocation",
      "participants": ["John", "Sarah"],
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total_entries": 12
}
```

#### Get Meeting Summary
```http
GET /api/meetings/{meeting_id}/summary
```

#### Delete Meeting
```http
DELETE /api/meetings/{meeting_id}
```

#### Reprocess Meeting
```http
POST /api/meetings/{meeting_id}/reprocess
```

#### Get Meeting Statistics
```http
GET /api/meetings/stats?user_id={user_id}
```

---

### ✅ Task Management

#### Get All Tasks
```http
GET /api/tasks?user_id={user_id}&status=pending&priority=high&meeting_id={meeting_id}
```

**Response:**
```json
{
  "tasks": [
    {
      "id": "uuid",
      "meeting_id": "uuid",
      "meeting_title": "Team Meeting",
      "title": "Prepare market analysis",
      "description": "Detailed market research for Q4",
      "assigned_to": "John Smith",
      "deadline": "2024-01-25T00:00:00Z",
      "priority": "high",
      "status": "pending",
      "calendar_event_id": "cal_123",
      "created_at": "2024-01-01T12:00:00Z",
      "updated_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 5,
  "filters": {
    "status": "pending",
    "priority": "high",
    "meeting_id": null
  }
}
```

#### Get Task Details
```http
GET /api/tasks/{task_id}
```

#### Update Task Status
```http
PUT /api/tasks/{task_id}/status
Content-Type: application/json

{
  "status": "pending|in_progress|completed"
}
```

#### Update Task Details
```http
PUT /api/tasks/{task_id}
Content-Type: application/json

{
  "title": "string",
  "description": "string",
  "assigned_to": "string",
  "deadline": "2024-01-25T00:00:00Z",
  "priority": "high|medium|low",
  "status": "pending|in_progress|completed"
}
```

#### Delete Task
```http
DELETE /api/tasks/{task_id}
```

#### Get Upcoming Tasks
```http
GET /api/tasks/upcoming?user_id={user_id}&days=30
```

**Response:**
```json
{
  "upcoming_tasks": [
    {
      "id": "uuid",
      "meeting_title": "Team Meeting",
      "title": "Prepare report",
      "deadline": "2024-01-25T00:00:00Z",
      "days_until_deadline": 5,
      "priority": "high",
      "status": "pending",
      "is_overdue": false
    }
  ],
  "total": 3,
  "days_ahead": 30
}
```

#### Get Task Statistics
```http
GET /api/tasks/stats?user_id={user_id}
```

---

### 🏥 Health Check Endpoints

#### Overall Health
```http
GET /api/health
```

**Response:**
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "overall_status": "healthy",
  "services": {
    "database": {
      "service": "database",
      "status": "healthy",
      "connection": "active"
    },
    "storage": {
      "service": "storage", 
      "status": "healthy",
      "provider": "supabase"
    },
    "transcription": {
      "service": "transcription",
      "status": "healthy",
      "api_key_configured": true
    },
    "ai_processor": {
      "service": "ai_processor",
      "status": "healthy",
      "model": "gemini-pro"
    },
    "calendar": {
      "service": "calendar_sync",
      "status": "healthy",
      "events_count": 25
    }
  }
}
```

#### Individual Service Health
```http
GET /api/health/database
GET /api/health/storage  
GET /api/health/transcription
GET /api/health/ai
GET /api/health/calendar
```

#### Detailed Health with Metrics
```http
GET /api/health/detailed
```

#### Routes Status
```http
GET /api/health/routes
```

---

## 🔧 Frontend Integration Examples

### React/TypeScript Integration

#### 1. API Client Setup
```typescript
// src/services/api.ts
const API_BASE_URL = 'http://localhost:5000';

class ApiClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  private async request<T>(
    endpoint: string, 
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;
    
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw new Error(`API Error: ${response.statusText}`);
    }

    return response.json();
  }

  // Auth methods
  async verifyUser(userData: {
    firebase_uid: string;
    email: string;
    name: string;
  }) {
    return this.request('/api/auth/verify', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  // Upload methods
  async uploadAudio(file: File, userId: string, title?: string) {
    const formData = new FormData();
    formData.append('audio', file);
    formData.append('user_id', userId);
    if (title) formData.append('title', title);

    return fetch(`${this.baseURL}/api/upload/audio`, {
      method: 'POST',
      body: formData,
    }).then(res => res.json());
  }

  async getProcessingStatus(meetingId: string) {
    return this.request(`/api/upload/status/${meetingId}`);
  }

  // Meeting methods
  async getMeetings(userId: string, page = 1, limit = 10) {
    return this.request(`/api/meetings?user_id=${userId}&page=${page}&limit=${limit}`);
  }

  async getMeeting(meetingId: string) {
    return this.request(`/api/meetings/${meetingId}`);
  }

  async getMeetingTimeline(meetingId: string) {
    return this.request(`/api/meetings/${meetingId}/timeline`);
  }

  // Task methods
  async getTasks(userId: string, filters: {
    status?: string;
    priority?: string;
    meeting_id?: string;
  } = {}) {
    const params = new URLSearchParams({ user_id: userId, ...filters });
    return this.request(`/api/tasks?${params}`);
  }

  async updateTaskStatus(taskId: string, status: string) {
    return this.request(`/api/tasks/${taskId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  }

  // Health check
  async getHealth() {
    return this.request('/api/health');
  }
}

export const apiClient = new ApiClient();
```

#### 2. React Hook for File Upload
```typescript
// src/hooks/useFileUpload.ts
import { useState } from 'react';
import { apiClient } from '../services/api';

export const useFileUpload = () => {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const uploadFile = async (file: File, userId: string, title?: string) => {
    setUploading(true);
    setError(null);
    setProgress(0);

    try {
      const result = await apiClient.uploadAudio(file, userId, title);
      
      if (result.success) {
        // Poll for status updates
        const meetingId = result.meeting_id;
        const pollStatus = async () => {
          const status = await apiClient.getProcessingStatus(meetingId);
          
          // Calculate overall progress
          const steps = status.processing_steps;
          const completedSteps = steps.filter(s => s.status === 'completed').length;
          const totalSteps = steps.length;
          const overallProgress = (completedSteps / totalSteps) * 100;
          
          setProgress(overallProgress);
          
          if (status.meeting_status === 'completed') {
            setUploading(false);
            return result;
          } else if (status.meeting_status === 'failed') {
            throw new Error('Processing failed');
          } else {
            // Continue polling
            setTimeout(pollStatus, 2000);
          }
        };
        
        pollStatus();
        return result;
      } else {
        throw new Error(result.error || 'Upload failed');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
      setUploading(false);
      throw err;
    }
  };

  return { uploadFile, uploading, progress, error };
};
```

#### 3. Meeting Dashboard Component
```typescript
// src/components/MeetingDashboard.tsx
import React, { useEffect, useState } from 'react';
import { apiClient } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

interface Meeting {
  id: string;
  title: string;
  status: string;
  task_count: number;
  created_at: string;
}

export const MeetingDashboard: React.FC = () => {
  const [meetings, setMeetings] = useState<Meeting[]>([]);
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  useEffect(() => {
    const fetchMeetings = async () => {
      if (user?.id) {
        try {
          const response = await apiClient.getMeetings(user.id);
          setMeetings(response.meetings);
        } catch (error) {
          console.error('Failed to fetch meetings:', error);
        } finally {
          setLoading(false);
        }
      }
    };

    fetchMeetings();
  }, [user]);

  if (loading) return <div>Loading meetings...</div>;

  return (
    <div className="meeting-dashboard">
      <h2>Your Meetings</h2>
      {meetings.map(meeting => (
        <div key={meeting.id} className="meeting-card">
          <h3>{meeting.title}</h3>
          <p>Status: {meeting.status}</p>
          <p>Tasks: {meeting.task_count}</p>
          <p>Created: {new Date(meeting.created_at).toLocaleDateString()}</p>
        </div>
      ))}
    </div>
  );
};
```

---

## 🚨 Error Handling

All endpoints return consistent error responses:

```json
{
  "error": "Error message description",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

Common HTTP status codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `404` - Not Found
- `413` - File Too Large
- `500` - Internal Server Error
- `503` - Service Unavailable

---

## 🔐 Authentication

The backend expects Firebase authentication. Include the user's Firebase UID in requests:

```typescript
// Get Firebase user
const user = auth.currentUser;
if (user) {
  const userData = {
    firebase_uid: user.uid,
    email: user.email,
    name: user.displayName
  };
  
  // Verify with backend
  await apiClient.verifyUser(userData);
}
```

---

## 📊 Rate Limits & Constraints

- **File Upload**: Max 100MB per file
- **Supported Formats**: MP3, WAV, M4A, MP4, WebM
- **Processing Time**: 2-10 minutes depending on file size
- **Concurrent Uploads**: 5 per user
- **API Rate Limit**: 1000 requests/hour per user

---

## 🔄 Real-time Updates

For real-time processing updates, poll the status endpoint:

```typescript
const pollProcessingStatus = async (meetingId: string) => {
  const poll = async () => {
    const status = await apiClient.getProcessingStatus(meetingId);
    
    if (status.meeting_status === 'processing') {
      setTimeout(poll, 2000); // Poll every 2 seconds
    }
    
    return status;
  };
  
  return poll();
};
```

---

This documentation provides everything needed to integrate the backend with your React frontend! 🚀
