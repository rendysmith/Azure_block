from typing import Optional, Dict, Any, Union
import json

from prefect.blocks.core import Block

from pydantic import Field, SecretStr

from azure.ai.contentunderstanding import ContentUnderstandingClient
from azure.ai.contentunderstanding.models import AnalysisInput
from azure.core.credentials import AzureKeyCredential
from azure.core.exceptions import AzureError
from azure.identity import DefaultAzureCredential

from prefect.events import emit_event
import os
from dotenv import load_dotenv

load_dotenv()


class ContentUnderstandingCredentials(Block):
    """Блок с подключением к Azure Content Understanding"""

    _block_type_name = "Content Understanding Credentials"
    _description = "Connecting to the Azure Content Understanding service"

    endpoint: str = Field(
        default=os.getenv("CONTENT_UNDERSTANDING_ENDPOINT", "https://dev-inwa.services.ai.azure.com/")
    )
    key: SecretStr = Field(
        default=SecretStr(os.getenv("CONTENT_UNDERSTANDING_KEY", ""))
    )
    api_version: str = Field(default="2025-11-01")

    def get_client(self) -> ContentUnderstandingClient:
        if self.key.get_secret_value():
            credential = AzureKeyCredential(self.key.get_secret_value())
        else:
            credential = DefaultAzureCredential()

        return ContentUnderstandingClient(
            endpoint=self.endpoint,
            credential=credential,
            api_version=self.api_version,
        )


class ContentUnderstandingAnalyzer(Block):
    """Блок для анализа файлов через Content Understanding"""

    _block_type_name = "Content Understanding Analyzer"
    _description = "Analyzes a document based on its URL or data"

    credentials: ContentUnderstandingCredentials
    analyzer_id: str = Field(..., description="ID analisator (example: auftrag)")

    def run(
        self,
        file_url: Optional[str] = None,
        file_data: Optional[Union[bytes, dict]] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Запускает анализ и возвращает результат в виде dict или None
        """
        if not file_url and not file_data:
            raise ValueError("Needed to post file_url or file_data")

        client = self.credentials.get_client()

        try:
            if file_url:
                inputs = [AnalysisInput(url=file_url)]
            else:
                # Пока упрощённо поддерживаем только file_url
                # file_data можно доработать позже
                raise NotImplementedError("file_data don't support. Use file_url.")

            print(f"🔍 Start analisys with '{self.analyzer_id}'...")

            poller = client.begin_analyze(
                analyzer_id=self.analyzer_id,
                inputs=inputs,
            )

            result = poller.result()
            result_dict = result.as_dict() if hasattr(result, "as_dict") else dict(result)

            # Отправляем событие в Prefect
            emit_event(
                event="contentunderstanding.analysis.completed",
                resource={"prefect.resource.id": f"analyzer.{self.analyzer_id}"},
                payload={
                    "analyzer_id": self.analyzer_id,
                    "file_url": file_url,
                    "status": "success"
                }
            )

            print("✅ The analysis has been successfully completed")
            return result_dict

        except AzureError as e:
            print(f"❌ Azure Error: {e.message}")
            emit_event(
                event="contentunderstanding.analysis.failed",
                resource={"prefect.resource.id": f"analyzer.{self.analyzer_id}"},
                payload={"error": str(e)}
            )
            return None

        except Exception as e:
            print(f"❌ Error: {e}")
            return None