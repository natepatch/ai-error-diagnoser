import hashlib

def generate_error_id(message: str) -> str:
    """Generate a stable, short hash to identify similar errors."""
    normalized = message.strip().lower()
    return hashlib.sha256(normalized.encode()).hexdigest()[:10]
