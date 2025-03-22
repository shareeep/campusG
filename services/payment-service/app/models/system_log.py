from app import db
from datetime import datetime
import json

class SystemLog(db.Model):
    """Model for system logs stored in the database"""
    __tablename__ = 'system_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, nullable=False, index=True)
    level = db.Column(db.String(20), nullable=False, index=True)
    message = db.Column(db.Text, nullable=False)
    trace_id = db.Column(db.String(50), nullable=True, index=True)
    request_id = db.Column(db.String(50), nullable=True, index=True)
    data = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f"<SystemLog {self.id} - {self.level} - {self.timestamp}>"

    def to_dict(self):
        """Convert the model to a dictionary"""
        result = {
            'id': self.id,
            'timestamp': self.timestamp.isoformat(),
            'level': self.level,
            'message': self.message,
            'traceId': self.trace_id,
            'requestId': self.request_id,
            'createdAt': self.created_at.isoformat()
        }
        
        if self.data:
            if isinstance(self.data, str):
                try:
                    result['data'] = json.loads(self.data)
                except:
                    result['data'] = self.data
            else:
                result['data'] = self.data
                
        return result
