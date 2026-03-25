import sys
import os
from typing import Optional
from prefect import flow
from pydantic import SecretStr

from blocks import ContentUnderstandingCredentials, ContentUnderstandingAnalyzer
import json

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


@flow(name="Test - Content Understanding Analysis")
def test_content_understanding_analysis(
        file_url: Optional[str] = None,
        file_data: Optional[bytes] = None,
        analyzer_id: str = "auftrag",
        credentials_block_name: str = "cu-credentials",
):
    print("=== Content Understanding Test Flow Started ===\n")

    from blocks import settings

    print(f"Updating credentials block '{credentials_block_name}' with settings...")
    credentials = ContentUnderstandingCredentials(
        endpoint=settings.endpoint,
        key=SecretStr(settings.key),
        api_version=settings.api_version
    )

    # ПРИНУДИТЕЛЬНО перезаписываем старый плохой блок в базе Prefect
    credentials.save(credentials_block_name, overwrite=True)
    print(f"✅ Credentials block updated and saved.")

    analyzer = ContentUnderstandingAnalyzer(
        credentials=credentials,
        analyzer_id=analyzer_id,
    )

    if not file_url and not file_data:
        file_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"
        print(f"⚠️ Using default test PDF: {file_url}")

    result = analyzer.run(file_url=file_url, file_data=file_data)

    if result:
        print("\n=== ANALYSIS RESULT ===")
        result_str = json.dumps(result, indent=2, ensure_ascii=False)
        print(result_str[:3000])
        if len(result_str) > 3000:
            print("... (truncated)")
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Analysis failed.")

    return result


if __name__ == "__main__":
    test_content_understanding_analysis()