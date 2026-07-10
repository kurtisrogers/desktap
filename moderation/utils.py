from moderation.models import AuditLog


def log_action(actor, action: str, target_type: str, target_id: int, metadata=None):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        metadata=metadata or {},
    )
