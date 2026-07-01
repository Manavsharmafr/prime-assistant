from sqlalchemy import Column, String
from app.core.database import Base


class SystemSettings(Base):
    __tablename__ = "system_settings"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
class UserPreferences(Base):
    __tablename__ = "user_preferences"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)
