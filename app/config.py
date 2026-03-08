from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "AI Assistant Platform Backend"
    app_env: str = "development"

    hf_space_url: str = "https://your-space-name.hf.space"
    hf_generate_path: str = "/generate_stream"
    hf_timeout_seconds: int = 120

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: str = ""
    allow_anon_chat: bool = False

    max_history_messages: int = 10
    max_user_memories: int = 5


settings = Settings()
