import json
from typing import Optional, Dict, Any, Union
import os

from prefect.blocks.core import Block
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

from prefect.events import emit_event


class ContentUnderstandingSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="CONTENT_UNDERSTANDING_",
    )

    endpoint: str = "https://dev-inwa.services.ai.azure.com/"
    key: str = ""
    api_version: str = "2025-11-01"


settings = ContentUnderstandingSettings()


class ContentUnderstandingCredentials(Block):
    """
    Block describing connection to Azure Content Understanding service.
    """

    _block_type_name = "Content Understanding Credentials"
    _description = "Stores endpoint, API key and API version for Azure Content Understanding service"

    endpoint: str = Field(default=settings.endpoint)
    key: SecretStr = Field(default=SecretStr(settings.key))
    api_version: str = Field(default=settings.api_version)

    def get_client(self) -> ContentUnderstandingClient:
        """Return authenticated client."""
        key_value = self.key.get_secret_value().strip()

        credential = (
            AzureKeyCredential(key_value) if key_value else DefaultAzureCredential()
        )

        return ContentUnderstandingClient(
            endpoint=self.endpoint.rstrip("/"),
            credential=credential,
            api_version=self.api_version,
        )


class ContentUnderstandingAnalyzer(Block):
    """
    Block that calls Azure Content Understanding service.
    """

    _block_type_name = "Content Understanding Analyzer"
    _description = "Analyzes file by URL or binary data and returns JSON result or None"

    credentials: ContentUnderstandingCredentials
    analyzer_id: str = Field(..., description="ID of the analyzer (e.g. 'auftrag')")

    def run(
        self,
        file_url: Optional[str] = None,
        file_data: Optional[Union[bytes, dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Perform analysis using Azure Content Understanding.
        Returns dict or None.
        """
        if not file_url and not file_data:
            raise ValueError("Either 'file_url' or 'file_data' must be provided.")

        client = self.credentials.get_client()

        try:
            print(f"Starting analysis with analyzer '{self.analyzer_id}'")

            if file_url:
                print(f"Using file URL: {file_url}")
                poller = client.begin_analyze(
                    analyzer_id=self.analyzer_id,
                    inputs=[AnalysisInput(url=file_url)],
                )
            else:
                # file_data support
                if isinstance(file_data, dict):
                    content = file_data.get("content") or json.dumps(file_data).encode("utf-8")
                else:
                    content = file_data

                print(f"Using binary data (size: {len(content)} bytes)")
                poller = client.begin_analyze_binary(
                    analyzer_id=self.analyzer_id,
                    binary_input=content,
                )

            result = poller.result()
            result_dict = result.as_dict() if hasattr(result, "as_dict") else dict(result)

            emit_event(
                event="contentunderstanding.analysis.completed",
                resource={"prefect.resource.id": f"analyzer.{self.analyzer_id}"},
                payload={
                    "analyzer_id": self.analyzer_id,
                    "file_url": file_url,
                    "status": "success",
                },
            )

            print("Analysis completed successfully.")
            return result_dict

        except AzureError as e:
            error_msg = getattr(e, "message", str(e))
            print(f"Azure Error: {error_msg}")
            emit_event(
                event="contentunderstanding.analysis.failed",
                resource={"prefect.resource.id": f"analyzer.{self.analyzer_id}"},
                payload={"error": error_msg},
            )
            return None

        except Exception as e:
            print(f"Unexpected error during analysis: {e}")
            return None