"""
Security audit and compliance system for PQC Secure Transfer.
Provides comprehensive audit logging, compliance reporting, and security event tracking.
"""

import json
import logging
import hashlib
import hmac
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
import asyncio
import os
from pathlib import Path

from monitoring.pqc_metrics_integration import record_security_event

logger = logging.getLogger(__name__)


class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication & Authorization
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    ACCESS_DENIED = "access_denied"
    PERMISSION_GRANTED = "permission_granted"
    
    # PQC Operations
    KEY_GENERATION = "key_generation"
    KEY_EXCHANGE = "key_exchange"
    KEY_ROTATION = "key_rotation"
    KEY_DELETION = "key_deletion"
    ENCRYPTION_OPERATION = "encryption_operation"
    DECRYPTION_OPERATION = "decryption_operation"
    
    # File Transfer Operations
    FILE_UPLOAD_START = "file_upload_start"
    FILE_UPLOAD_COMPLETE = "file_upload_complete"
    FILE_DOWNLOAD_START = "file_download_start"
    FILE_DOWNLOAD_COMPLETE = "file_download_complete"
    FILE_TRANSFER_FAILED = "file_transfer_failed"
    
    # Security Events
    SECURITY_VIOLATION = "security_violation"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    COMPLIANCE_VIOLATION = "compliance_violation"
    
    # System Events
    SERVICE_START = "service_start"
    SERVICE_STOP = "service_stop"
    CONFIGURATION_CHANGE = "configuration_change"
    SYSTEM_ERROR = "system_error"
    
    # Administrative Actions
    ADMIN_ACTION = "admin_action"
    POLICY_CHANGE = "policy_change"
    USER_MANAGEMENT = "user_management"


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Represents a single audit event."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None
    resource: Optional[str] = None
    action: Optional[str] = None
    result: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    correlation_id: Optional[str] = None
    environment: str = "production"
    service_name: str = "pqc-secure-transfer"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert audit event to dictionary."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['severity'] = self.severity.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    def to_json(self) -> str:
        """Convert audit event to JSON string."""
        return json.dumps(self.to_dict(), default=str)
    
    def calculate_integrity_hash(self, secret_key: bytes) -> str:
        """Calculate HMAC-SHA256 hash for integrity verification."""
        data = self.to_json().encode('utf-8')
        return hmac.new(secret_key, data, hashlib.sha256).hexdigest()


class AuditLogger:
    """Handles audit event logging with integrity protection."""
    
    def __init__(self, log_directory: str = "audit_logs", 
                 integrity_key: Optional[bytes] = None):
        self.log_directory = Path(log_directory)
        self.log_directory.mkdir(exist_ok=True)
        
        # Generate or load integrity key
        self.integrity_key = integrity_key or self._get_or_create_integrity_key()
        
        # Current log file
        self.current_log_file = None
        self.log_file_handle = None
        
        # Event counter for integrity chain
        self.event_counter = 0
        self.last_event_hash = None
        
        logger.info(f"Audit logger initialized with log directory: {log_directory}")
    
    def _get_or_create_integrity_key(self) -> bytes:
        """Get or create integrity key for audit log protection."""
        key_file = self.log_directory / ".integrity_key"
        
        if key_file.exists():
            with open(key_file, 'rb') as f:
                return f.read()
        else:
            # Generate new key
            key = os.urandom(32)
            with open(key_file, 'wb') as f:
                f.write(key)
            # Secure the key file
            os.chmod(key_file, 0o600)
            return key
    
    def _get_current_log_file(self) -> Path:
        """Get current log file path (daily rotation)."""
        date_str = datetime.utcnow().strftime("%Y-%m-%d")
        return self.log_directory / f"audit_{date_str}.jsonl"
    
    def _ensure_log_file_open(self):
        """Ensure the current log file is open."""
        current_file = self._get_current_log_file()
        
        if self.current_log_file != current_file:
            # Close previous file if open
            if self.log_file_handle:
                self.log_file_handle.close()
            
            # Open new file
            self.current_log_file = current_file
            self.log_file_handle = open(current_file, 'a', encoding='utf-8')
            
            # Reset counter for new file
            if not current_file.exists() or current_file.stat().st_size == 0:
                self.event_counter = 0
                self.last_event_hash = None
    
    async def log_event(self, event: AuditEvent) -> bool:
        """Log an audit event with integrity protection."""
        try:
            self._ensure_log_file_open()
            
            # Add integrity information
            self.event_counter += 1
            event.details['_audit_sequence'] = self.event_counter
            
            # Calculate integrity hash
            integrity_hash = event.calculate_integrity_hash(self.integrity_key)
            event.details['_integrity_hash'] = integrity_hash
            
            # Chain with previous event
            if self.last_event_hash:
                event.details['_previous_hash'] = self.last_event_hash
            
            # Write to log file
            log_entry = event.to_json() + '\n'
            self.log_file_handle.write(log_entry)
            self.log_file_handle.flush()
            
            # Update last hash
            self.last_event_hash = integrity_hash
            
            # Record security event metric
            record_security_event(event.event_type.value, event.severity.value)
            
            logger.debug(f"Audit event logged: {event.event_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to log audit event {event.event_id}: {e}")
            return False
    
    def verify_log_integrity(self, log_file_path: Path) -> Dict[str, Any]:
        """Verify the integrity of an audit log file."""
        verification_result = {
            'file': str(log_file_path),
            'total_events': 0,
            'verified_events': 0,
            'integrity_violations': [],
            'chain_breaks': [],
            'is_valid': True
        }
        
        try:
            if not log_file_path.exists():
                verification_result['is_valid'] = False
                verification_result['error'] = 'Log file does not exist'
                return verification_result
            
            previous_hash = None
            sequence_counter = 0
            
            with open(log_file_path, 'r', encoding='utf-8') as f:
                for line_num, line in enumerate(f, 1):
                    if not line.strip():
                        continue
                    
                    try:
                        event_data = json.loads(line.strip())
                        verification_result['total_events'] += 1
                        
                        # Recreate event for hash verification
                        event = AuditEvent(
                            event_id=event_data['event_id'],
                            event_type=AuditEventType(event_data['event_type']),
                            severity=AuditSeverity(event_data['severity']),
                            timestamp=datetime.fromisoformat(event_data['timestamp']),
                            user_id=event_data.get('user_id'),
                            session_id=event_data.get('session_id'),
                            source_ip=event_data.get('source_ip'),
                            user_agent=event_data.get('user_agent'),
                            resource=event_data.get('resource'),
                            action=event_data.get('action'),
                            result=event_data.get('result'),
                            message=event_data.get('message', ''),
                            details={k: v for k, v in event_data.get('details', {}).items() 
                                   if not k.startswith('_')},
                            correlation_id=event_data.get('correlation_id'),
                            environment=event_data.get('environment', 'production'),
                            service_name=event_data.get('service_name', 'pqc-secure-transfer')
                        )
                        
                        # Verify integrity hash
                        stored_hash = event_data.get('details', {}).get('_integrity_hash')
                        calculated_hash = event.calculate_integrity_hash(self.integrity_key)
                        
                        if stored_hash != calculated_hash:
                            verification_result['integrity_violations'].append({
                                'line': line_num,
                                'event_id': event.event_id,
                                'stored_hash': stored_hash,
                                'calculated_hash': calculated_hash
                            })
                            verification_result['is_valid'] = False
                        else:
                            verification_result['verified_events'] += 1
                        
                        # Verify sequence chain
                        sequence_counter += 1
                        stored_sequence = event_data.get('details', {}).get('_audit_sequence')
                        stored_previous_hash = event_data.get('details', {}).get('_previous_hash')
                        
                        if stored_sequence != sequence_counter:
                            verification_result['chain_breaks'].append({
                                'line': line_num,
                                'expected_sequence': sequence_counter,
                                'stored_sequence': stored_sequence
                            })
                            verification_result['is_valid'] = False
                        
                        if previous_hash and stored_previous_hash != previous_hash:
                            verification_result['chain_breaks'].append({
                                'line': line_num,
                                'expected_previous_hash': previous_hash,
                                'stored_previous_hash': stored_previous_hash
                            })
                            verification_result['is_valid'] = False
                        
                        previous_hash = stored_hash
                        
                    except json.JSONDecodeError as e:
                        verification_result['integrity_violations'].append({
                            'line': line_num,
                            'error': f'JSON decode error: {e}'
                        })
                        verification_result['is_valid'] = False
                    except Exception as e:
                        verification_result['integrity_violations'].append({
                            'line': line_num,
                            'error': f'Verification error: {e}'
                        })
                        verification_result['is_valid'] = False
            
        except Exception as e:
            verification_result['is_valid'] = False
            verification_result['error'] = str(e)
        
        return verification_result
    
    def close(self):
        """Close the audit logger."""
        if self.log_file_handle:
            self.log_file_handle.close()
            self.log_file_handle = None


class ComplianceReporter:
    """Generates compliance reports from audit logs."""
    
    def __init__(self, audit_logger: AuditLogger):
        self.audit_logger = audit_logger
    
    async def generate_pqc_compliance_report(self, start_date: datetime, 
                                           end_date: datetime) -> Dict[str, Any]:
        """Generate PQC-specific compliance report."""
        report = {
            'report_type': 'pqc_compliance',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'generated_at': datetime.utcnow().isoformat(),
            'summary': {},
            'key_operations': {},
            'security_events': {},
            'compliance_status': 'COMPLIANT'
        }
        
        try:
            # Analyze audit logs for the period
            pqc_events = await self._extract_pqc_events(start_date, end_date)
            
            # Key operation statistics
            key_ops = {
                'key_generations': len([e for e in pqc_events if e['event_type'] == 'key_generation']),
                'key_exchanges': len([e for e in pqc_events if e['event_type'] == 'key_exchange']),
                'key_rotations': len([e for e in pqc_events if e['event_type'] == 'key_rotation']),
                'encryption_operations': len([e for e in pqc_events if e['event_type'] == 'encryption_operation']),
                'decryption_operations': len([e for e in pqc_events if e['event_type'] == 'decryption_operation'])
            }
            report['key_operations'] = key_ops
            
            # Security event analysis
            security_events = [e for e in pqc_events if e['severity'] in ['error', 'critical']]
            report['security_events'] = {
                'total_security_events': len(security_events),
                'critical_events': len([e for e in security_events if e['severity'] == 'critical']),
                'error_events': len([e for e in security_events if e['severity'] == 'error']),
                'events_by_type': self._group_events_by_type(security_events)
            }
            
            # Compliance checks
            compliance_issues = []
            
            # Check key rotation frequency
            if key_ops['key_rotations'] == 0 and (end_date - start_date).days > 30:
                compliance_issues.append("No key rotations performed in reporting period")
            
            # Check for critical security events
            if report['security_events']['critical_events'] > 0:
                compliance_issues.append(f"{report['security_events']['critical_events']} critical security events")
            
            if compliance_issues:
                report['compliance_status'] = 'NON_COMPLIANT'
                report['compliance_issues'] = compliance_issues
            
            report['summary'] = {
                'total_pqc_events': len(pqc_events),
                'compliance_status': report['compliance_status'],
                'key_operations_total': sum(key_ops.values()),
                'security_events_total': len(security_events)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate PQC compliance report: {e}")
            report['error'] = str(e)
            report['compliance_status'] = 'ERROR'
        
        return report
    
    async def generate_access_report(self, start_date: datetime, 
                                   end_date: datetime) -> Dict[str, Any]:
        """Generate access and authentication report."""
        report = {
            'report_type': 'access_report',
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'generated_at': datetime.utcnow().isoformat(),
            'authentication_events': {},
            'access_patterns': {},
            'security_violations': {}
        }
        
        try:
            # Extract access-related events
            access_events = await self._extract_access_events(start_date, end_date)
            
            # Authentication statistics
            auth_events = {
                'successful_logins': len([e for e in access_events if e['event_type'] == 'user_login' and e['result'] == 'success']),
                'failed_logins': len([e for e in access_events if e['event_type'] == 'user_login' and e['result'] == 'failure']),
                'logouts': len([e for e in access_events if e['event_type'] == 'user_logout']),
                'access_denied': len([e for e in access_events if e['event_type'] == 'access_denied'])
            }
            report['authentication_events'] = auth_events
            
            # Access pattern analysis
            user_access = {}
            for event in access_events:
                user_id = event.get('user_id', 'anonymous')
                if user_id not in user_access:
                    user_access[user_id] = {'events': 0, 'unique_ips': set(), 'last_access': None}
                
                user_access[user_id]['events'] += 1
                if event.get('source_ip'):
                    user_access[user_id]['unique_ips'].add(event['source_ip'])
                
                event_time = datetime.fromisoformat(event['timestamp'])
                if not user_access[user_id]['last_access'] or event_time > user_access[user_id]['last_access']:
                    user_access[user_id]['last_access'] = event_time
            
            # Convert sets to counts for JSON serialization
            for user_data in user_access.values():
                user_data['unique_ip_count'] = len(user_data['unique_ips'])
                user_data['unique_ips'] = list(user_data['unique_ips'])
                if user_data['last_access']:
                    user_data['last_access'] = user_data['last_access'].isoformat()
            
            report['access_patterns'] = {
                'unique_users': len(user_access),
                'user_details': user_access
            }
            
            # Security violations
            violations = [e for e in access_events if e['event_type'] in ['security_violation', 'intrusion_attempt']]
            report['security_violations'] = {
                'total_violations': len(violations),
                'violations_by_type': self._group_events_by_type(violations),
                'violations_by_ip': self._group_events_by_ip(violations)
            }
            
        except Exception as e:
            logger.error(f"Failed to generate access report: {e}")
            report['error'] = str(e)
        
        return report
    
    async def _extract_pqc_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Extract PQC-related events from audit logs."""
        pqc_event_types = [
            'key_generation', 'key_exchange', 'key_rotation', 'key_deletion',
            'encryption_operation', 'decryption_operation'
        ]
        
        return await self._extract_events_by_type(pqc_event_types, start_date, end_date)
    
    async def _extract_access_events(self, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Extract access-related events from audit logs."""
        access_event_types = [
            'user_login', 'user_logout', 'access_denied', 'permission_granted',
            'security_violation', 'intrusion_attempt'
        ]
        
        return await self._extract_events_by_type(access_event_types, start_date, end_date)
    
    async def _extract_events_by_type(self, event_types: List[str], 
                                    start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Extract events of specific types from audit logs."""
        events = []
        
        # Iterate through log files in the date range
        current_date = start_date.date()
        end_date_only = end_date.date()
        
        while current_date <= end_date_only:
            log_file = self.audit_logger.log_directory / f"audit_{current_date.strftime('%Y-%m-%d')}.jsonl"
            
            if log_file.exists():
                try:
                    with open(log_file, 'r', encoding='utf-8') as f:
                        for line in f:
                            if not line.strip():
                                continue
                            
                            try:
                                event_data = json.loads(line.strip())
                                event_time = datetime.fromisoformat(event_data['timestamp'])
                                
                                # Check if event is in date range and of correct type
                                if (start_date <= event_time <= end_date and 
                                    event_data['event_type'] in event_types):
                                    events.append(event_data)
                                    
                            except (json.JSONDecodeError, KeyError, ValueError):
                                continue
                                
                except Exception as e:
                    logger.error(f"Error reading log file {log_file}: {e}")
            
            current_date += timedelta(days=1)
        
        return events
    
    def _group_events_by_type(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group events by type and count them."""
        type_counts = {}
        for event in events:
            event_type = event.get('event_type', 'unknown')
            type_counts[event_type] = type_counts.get(event_type, 0) + 1
        return type_counts
    
    def _group_events_by_ip(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Group events by source IP and count them."""
        ip_counts = {}
        for event in events:
            source_ip = event.get('source_ip', 'unknown')
            ip_counts[source_ip] = ip_counts.get(source_ip, 0) + 1
        return ip_counts


class SecurityAuditManager:
    """Main manager for security audit and compliance operations."""
    
    def __init__(self, log_directory: str = "audit_logs"):
        self.audit_logger = AuditLogger(log_directory)
        self.compliance_reporter = ComplianceReporter(self.audit_logger)
        
        logger.info("Security audit manager initialized")
    
    async def log_pqc_operation(self, operation: str, user_id: Optional[str] = None,
                               algorithm: str = "Kyber768", result: str = "success",
                               details: Optional[Dict[str, Any]] = None) -> str:
        """Log a PQC operation."""
        event_id = f"pqc_{operation}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        event = AuditEvent(
            event_id=event_id,
            event_type=AuditEventType(f"{operation.lower()}_operation"),
            severity=AuditSeverity.INFO if result == "success" else AuditSeverity.ERROR,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=operation,
            result=result,
            message=f"PQC {operation} operation {result}",
            details={
                'algorithm': algorithm,
                **(details or {})
            }
        )
        
        await self.audit_logger.log_event(event)
        return event_id
    
    async def log_file_transfer(self, operation: str, filename: str, 
                               file_size: int, user_id: Optional[str] = None,
                               result: str = "success", 
                               details: Optional[Dict[str, Any]] = None) -> str:
        """Log a file transfer operation."""
        event_id = f"transfer_{operation}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        event_type_map = {
            'upload_start': AuditEventType.FILE_UPLOAD_START,
            'upload_complete': AuditEventType.FILE_UPLOAD_COMPLETE,
            'download_start': AuditEventType.FILE_DOWNLOAD_START,
            'download_complete': AuditEventType.FILE_DOWNLOAD_COMPLETE,
            'transfer_failed': AuditEventType.FILE_TRANSFER_FAILED
        }
        
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type_map.get(operation, AuditEventType.FILE_TRANSFER_FAILED),
            severity=AuditSeverity.INFO if result == "success" else AuditSeverity.ERROR,
            timestamp=datetime.utcnow(),
            user_id=user_id,
            resource=filename,
            action=operation,
            result=result,
            message=f"File {operation} {result}: {filename}",
            details={
                'file_size': file_size,
                'filename': filename,
                **(details or {})
            }
        )
        
        await self.audit_logger.log_event(event)
        return event_id
    
    async def log_security_event(self, event_type: str, severity: str = "warning",
                                message: str = "", user_id: Optional[str] = None,
                                source_ip: Optional[str] = None,
                                details: Optional[Dict[str, Any]] = None) -> str:
        """Log a security event."""
        event_id = f"security_{event_type}_{int(datetime.utcnow().timestamp() * 1000)}"
        
        event = AuditEvent(
            event_id=event_id,
            event_type=AuditEventType.SECURITY_VIOLATION,
            severity=AuditSeverity(severity),
            timestamp=datetime.utcnow(),
            user_id=user_id,
            source_ip=source_ip,
            action=event_type,
            message=message or f"Security event: {event_type}",
            details=details or {}
        )
        
        await self.audit_logger.log_event(event)
        return event_id
    
    async def generate_compliance_report(self, report_type: str = "pqc_compliance",
                                       days_back: int = 30) -> Dict[str, Any]:
        """Generate a compliance report."""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days_back)
        
        if report_type == "pqc_compliance":
            return await self.compliance_reporter.generate_pqc_compliance_report(start_date, end_date)
        elif report_type == "access_report":
            return await self.compliance_reporter.generate_access_report(start_date, end_date)
        else:
            raise ValueError(f"Unknown report type: {report_type}")
    
    def verify_audit_integrity(self, days_back: int = 7) -> Dict[str, Any]:
        """Verify audit log integrity for recent days."""
        verification_results = {}
        
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days_back)
        
        current_date = start_date
        while current_date <= end_date:
            log_file = self.audit_logger.log_directory / f"audit_{current_date.strftime('%Y-%m-%d')}.jsonl"
            
            if log_file.exists():
                result = self.audit_logger.verify_log_integrity(log_file)
                verification_results[current_date.strftime('%Y-%m-%d')] = result
            
            current_date += timedelta(days=1)
        
        return verification_results
    
    def close(self):
        """Close the audit manager."""
        self.audit_logger.close()


# Global audit manager instance
_audit_manager: Optional[SecurityAuditManager] = None


def initialize_audit_system(log_directory: str = "audit_logs") -> SecurityAuditManager:
    """Initialize the global audit system."""
    global _audit_manager
    _audit_manager = SecurityAuditManager(log_directory)
    logger.info("Security audit system initialized")
    return _audit_manager


def get_audit_manager() -> Optional[SecurityAuditManager]:
    """Get the global audit manager."""
    return _audit_manager


# Convenience functions for common audit operations
async def log_pqc_operation(operation: str, user_id: Optional[str] = None,
                           algorithm: str = "Kyber768", result: str = "success",
                           details: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Log a PQC operation using the global audit manager."""
    if _audit_manager:
        return await _audit_manager.log_pqc_operation(operation, user_id, algorithm, result, details)
    return None


async def log_file_transfer(operation: str, filename: str, file_size: int,
                           user_id: Optional[str] = None, result: str = "success",
                           details: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Log a file transfer operation using the global audit manager."""
    if _audit_manager:
        return await _audit_manager.log_file_transfer(operation, filename, file_size, user_id, result, details)
    return None


async def log_security_event(event_type: str, severity: str = "warning",
                            message: str = "", user_id: Optional[str] = None,
                            source_ip: Optional[str] = None,
                            details: Optional[Dict[str, Any]] = None) -> Optional[str]:
    """Log a security event using the global audit manager."""
    if _audit_manager:
        return await _audit_manager.log_security_event(event_type, severity, message, user_id, source_ip, details)
    return None