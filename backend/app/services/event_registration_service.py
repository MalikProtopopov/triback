"""Обратная совместимость: реэкспорт ``EventRegistrationService`` из пакета."""

from app.services.event_registration import EventRegistrationService

__all__ = ["EventRegistrationService"]
