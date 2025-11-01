"""
Core data models for CTF challenges and system state
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum
import uuid

class ChallengeType(Enum):
    """Types of web CTF challenges"""
    SQL_INJECTION = "sql_injection"
    XSS = "xss" 
    CSRF = "csrf"
    AUTHENTICATION_BYPASS = "auth_bypass"
    AUTHORIZATION = "authorization"
    FILE_UPLOAD = "file_upload"
    COMMAND_INJECTION = "command_injection"
    XXE = "xxe"
    SSRF = "ssrf"
    DESERIALIZATION = "deserialization"
    OTHER = "other"

class ExploitStatus(Enum):
    """Status of exploitation attempts"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"

@dataclass
class Challenge:
    """Represents a CTF challenge submission"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    url: str = ""
    title: str = ""
    description: str = ""
    source_code: Optional[str] = None
    flag_format: str = ""
    hint: Optional[str] = None
    challenge_type: Optional[ChallengeType] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert challenge to dictionary for serialization"""
        return {
            "id": self.id,
            "url": self.url,
            "title": self.title,
            "description": self.description,
            "source_code": self.source_code,
            "flag_format": self.flag_format,
            "hint": self.hint,
            "challenge_type": self.challenge_type.value if self.challenge_type else None,
            "created_at": self.created_at.isoformat()
        }

@dataclass 
class ExploitAttempt:
    """Represents a single exploitation attempt"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    challenge_id: str = ""
    agent_name: str = ""
    attack_vector: str = ""
    payload: str = ""
    request_data: Dict[str, Any] = field(default_factory=dict)
    response_data: Dict[str, Any] = field(default_factory=dict)
    status: ExploitStatus = ExploitStatus.PENDING
    flag_found: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exploit attempt to dictionary"""
        return {
            "id": self.id,
            "challenge_id": self.challenge_id,
            "agent_name": self.agent_name,
            "attack_vector": self.attack_vector,
            "payload": self.payload,
            "request_data": self.request_data,
            "response_data": self.response_data,
            "status": self.status.value,
            "flag_found": self.flag_found,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
            "execution_time": self.execution_time
        }

@dataclass
class CTFSubmission:
    """Complete CTF submission with results"""
    challenge: Challenge
    exploit_attempts: List[ExploitAttempt] = field(default_factory=list)
    final_flag: Optional[str] = None
    success: bool = False
    total_time: Optional[float] = None
    agent_logs: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_exploit_attempt(self, attempt: ExploitAttempt):
        """Add an exploitation attempt to the submission"""
        self.exploit_attempts.append(attempt)
        if attempt.flag_found and attempt.status == ExploitStatus.SUCCESS:
            self.final_flag = attempt.flag_found
            self.success = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert submission to dictionary"""
        return {
            "challenge": self.challenge.to_dict(),
            "exploit_attempts": [attempt.to_dict() for attempt in self.exploit_attempts],
            "final_flag": self.final_flag,
            "success": self.success,
            "total_time": self.total_time,
            "agent_logs": self.agent_logs
        }