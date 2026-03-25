import json

from prefect import flow
from blocks import ContentUnderstandingCredentials, ContentUnderstandingAnalyzer


@flow(name="Just Docs analyst")
def analyze_file_flow(file_url: str, analyzer_id: str = "auftrag"):
    # Загружаем или создаём credentials
    try:
        credentials = ContentUnderstandingCredentials.load("cu-credentials")
    except Exception:
        credentials = ContentUnderstandingCredentials()
        credentials.save("cu-credentials", overwrite=True)
        print("Создан новый блок credentials")

    # Создаём анализатор
    analyzer = ContentUnderstandingAnalyzer(
        credentials=credentials,
        analyzer_id=analyzer_id
    )

    # Запускаем анализ
    result = analyzer.run(file_url=file_url)

    if result:
        print("\n=== Analysis Result ===")
        print(json.dumps(result, indent=2, ensure_ascii=False)[:2000] + "\n...")
    else:
        print("Analysis Didn't work.")

    return result


# ========================
if __name__ == "__main__":
    # Пример использования
    test_url = "https://www.w3.org/WAI/ER/tests/xhtml/testfiles/resources/pdf/dummy.pdf"

    analyze_file_flow(test_url, analyzer_id="auftrag")