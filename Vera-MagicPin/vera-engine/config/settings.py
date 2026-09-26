from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", protected_namespaces=())

    team_name: str = "Team Raunak"
    team_members: list[str] = ["Raunak Kheshwani"]
    model_name: str = "llama3-8b-8192"
    approach: str = (
        "Context-to-decision composer: deterministic opportunity ranking and "
        "attention/fatigue suppression choose the action, an evidence-grounded "
        "LLM composer only handles wording."
    )
    contact_email: str = "raunak@example.com"
    version: str = "0.1.0"

    llm_provider: str = "gemini"
    gemini_api_key: str | None = None
    groq_api_key: str | None = None
    database_url: str | None = None


settings = Settings()