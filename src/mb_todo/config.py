"""Centralized application configuration."""

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, computed_field


class Config(BaseModel):
    """Application-wide configuration."""

    model_config = ConfigDict(frozen=True)

    data_dir: Path = Field(description="Base directory for all application data")

    @computed_field(description="SQLite database file")
    @property
    def db_path(self) -> Path:
        """SQLite database file."""
        return self.data_dir / "todo.db"

    @computed_field(description="Rotating log file")
    @property
    def log_path(self) -> Path:
        """Rotating log file."""
        return self.data_dir / "todo.log"

    @staticmethod
    def build(data_dir: Path | None = None) -> Config:
        """Build a Config instance from defaults."""
        resolved_dir = data_dir if data_dir is not None else Path.home() / ".local" / "mb-todo"
        return Config(data_dir=resolved_dir)
