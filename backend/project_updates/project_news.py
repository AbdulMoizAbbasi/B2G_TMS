import os
import re
from datetime import datetime
from pathlib import Path

import openpyxl
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq
from tavily import TavilyClient


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

ENV_FILE = Path(__file__).resolve().parent / ".env"
load_dotenv(ENV_FILE)

EXCEL_FILE = (
    BASE_DIR
    / "data"
    / "ICT_Projects_2026-27.xlsx"
)

PROJECT_SHEET = "Projects Details"
NEWS_SHEET = "Project News"

# Only fetch the latest 3 results
MAX_RESULTS = 3

SEARCH_DEPTH = "advanced"

TAVILY_API_KEY = os.getenv("api_key")
GROQ_API_KEY = os.getenv("groq_api_key")

if not TAVILY_API_KEY:
    raise RuntimeError(
        "Tavily API key not found. "
        "Expected 'api_key' in project_updates/.env"
    )

if not GROQ_API_KEY:
    raise RuntimeError(
        "Groq API key not found. "
        "Expected 'groq_api_key' in project_updates/.env"
    )


tavily_client = TavilyClient(
    api_key=TAVILY_API_KEY
)

groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# EXCEL HELPERS
# ============================================================

def get_workbook():
    return openpyxl.load_workbook(
        EXCEL_FILE
    )


def ensure_news_sheet(workbook):

    if NEWS_SHEET not in workbook.sheetnames:

        sheet = workbook.create_sheet(
            NEWS_SHEET
        )

        sheet.append([
            "Project ID",
            "Project Name",
            "News Date",
            "News Title",
            "Keypoints",
            "Source",
            "URL",
            "Last Updated",
        ])

        return sheet

    return workbook[NEWS_SHEET]


# ============================================================
# PROJECT LOOKUP
# ============================================================

def get_project_by_id(project_id):

    workbook = get_workbook()

    if PROJECT_SHEET not in workbook.sheetnames:
        return None

    sheet = workbook[
        PROJECT_SHEET
    ]

    headers = [
        cell.value
        for cell in sheet[1]
    ]

    for row in sheet.iter_rows(
        min_row=2,
        values_only=True,
    ):

        record = dict(
            zip(headers, row)
        )

        if str(
            record.get("Project ID")
        ) == str(project_id):

            return record

    return None


# ============================================================
# WEB PAGE CONTENT FALLBACK
# ============================================================

def fetch_page_content(url):

    if not url:
        return ""

    try:

        response = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 "
                    "(KHTML, like Gecko) "
                    "Chrome/140.0 Safari/537.36"
                )
            },
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        for element in soup([
            "script",
            "style",
            "noscript",
            "svg",
            "nav",
            "footer",
            "header",
            "form",
            "aside",
        ]):

            element.decompose()

        container = (
            soup.find("article")
            or soup.find("main")
            or soup.body
        )

        if not container:
            return ""

        text = container.get_text(
            separator="\n",
            strip=True,
        )

        lines = []

        for line in text.splitlines():

            line = re.sub(
                r"\s+",
                " ",
                line,
            ).strip()

            if line:
                lines.append(line)

        text = "\n".join(lines)

        return text[:12000]

    except Exception as e:

        print(
            f"[PAGE FETCH ERROR] "
            f"{url}: {e}"
        )

        return ""


# ============================================================
# TAVILY SEARCH
# ============================================================

def search_project_news(project_name):

    query = (
        f"{project_name} latest updates"
    )

    print("\n" + "=" * 70)
    print("TAVILY SEARCH DEBUG")
    print("=" * 70)
    print(f"Query: {query}")
    print("=" * 70)

    search_results = tavily_client.search(
        query=query,
        search_depth=SEARCH_DEPTH,
        max_results=MAX_RESULTS,
        include_answer=False,
        include_raw_content=True,
    )

    results = search_results.get(
        "results",
        []
    )

    print(
        f"\nTavily returned "
        f"{len(results)} results:"
    )

    processed_results = []

    for index, result in enumerate(
        results,
        start=1,
    ):

        title = result.get(
            "title"
        )

        url = result.get(
            "url"
        )

        published_date = (
            result.get(
                "published_date"
            )
            or result.get(
                "published"
            )
            or result.get(
                "date"
            )
            or result.get(
                "publishedDate"
            )
        )

        source = result.get(
            "source"
        )

        score = result.get(
            "score"
        )

        raw_content = (
            result.get(
                "raw_content"
            )
            or ""
        )

        content = (
            result.get(
                "content"
            )
            or ""
        )

        print("\n" + "-" * 70)
        print(f"RESULT #{index}")
        print(f"Title: {title}")
        print(f"URL: {url}")
        print(
            f"Published Date: "
            f"{published_date}"
        )
        print(
            f"Source: "
            f"{source}"
        )
        print(
            f"Score: "
            f"{score}"
        )
        print(
            f"Raw content length: "
            f"{len(raw_content)}"
        )
        print(
            f"Tavily content length: "
            f"{len(content)}"
        )

        # Prefer Tavily raw content
        if raw_content.strip():

            final_content = raw_content

        elif content.strip():

            final_content = content

        else:

            print(
                "[CONTENT FALLBACK] "
                "Fetching source page..."
            )

            final_content = (
                fetch_page_content(url)
            )

        # Keep the prompt within a reasonable size
        final_content = final_content[:12000]

        print(
            f"Final content length: "
            f"{len(final_content)}"
        )

        processed_results.append({
            "title": title,
            "url": url,
            "published_date": published_date,
            "source": source,
            "score": score,
            "content": final_content,
        })

    print("=" * 70)
    print("END TAVILY DEBUG")
    print("=" * 70 + "\n")

    return processed_results


# ============================================================
# GROQ RESPONSE EXTRACTION
# ============================================================

def extract_groq_text(response):

    try:

        message = (
            response.choices[0]
            .message
        )

        content = getattr(
            message,
            "content",
            None
        )

        if content:
            return str(
                content
            ).strip()

    except Exception:
        pass

    try:

        output_text = getattr(
            response,
            "output_text",
            None
        )

        if output_text:
            return str(
                output_text
            ).strip()

    except Exception:
        pass

    return ""


# ============================================================
# GROQ ANALYSIS
# ============================================================

def generate_news_summary(
    project_name,
    title,
    content,
):

    if not content:
        content = title or ""

    content = content[:12000]

    prompt = f"""
You analyze a source article about a government project.

PROJECT:
{project_name}

SOURCE TITLE:
{title}

SOURCE CONTENT:
{content}

Your task is to extract the actual substantive project update.

Focus on:
- development
- construction/progress
- funding/allocation
- approvals
- implementation
- timelines
- objectives
- infrastructure
- ICT/technology
- delays
- risks/issues
- project scope

Ignore:
- likes
- reactions
- comments
- views
- followers
- hashtags
- social media engagement
- promotional language

Do not invent information.
Do not infer facts from the project name.
Do not claim an announcement unless the source explicitly says it.
Historical information must remain historical.

Return EXACTLY this format:

TITLE: short factual title
KEYPOINT 1: short factual point
KEYPOINT 2: short factual point

Each keypoint must be 15 words or fewer.
"""


    try:

        response = groq_client.chat.completions.create(
            model="openai/gpt-oss-20b",

            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],

            temperature=0.1,

            # ------------------------------------------------
            # IMPORTANT FIX
            # ------------------------------------------------
            # Previously 300 tokens were almost entirely
            # consumed by reasoning.
            #
            # Give the model enough room to finish its
            # reasoning AND generate the final answer.
            # ------------------------------------------------

            max_tokens=1000,

            # Reduce reasoning so the model reaches
            # the requested final output.
            reasoning_effort="low",
        )

        print("\n[GROQ RAW RESPONSE]")
        print(response)
        print("[END GROQ RAW RESPONSE]\n")

        output = extract_groq_text(
            response
        )

        print("\n[GROQ OUTPUT]")
        print(output)
        print("[END GROQ OUTPUT]\n")

        if not output:

            print(
                "[GROQ WARNING] "
                "Model returned empty content."
            )

            return {
                "title": title,
                "keypoints": "",
            }

        return parse_groq_output(
            output,
            fallback_title=title,
        )

    except Exception as e:

        print(
            f"[GROQ ERROR] {e}"
        )

        return {
            "title": title,
            "keypoints": "",
        }


# ============================================================
# PARSE GROQ OUTPUT
# ============================================================

def parse_groq_output(
    output,
    fallback_title,
):

    title = fallback_title
    keypoints = []

    if not output:

        return {
            "title": title,
            "keypoints": "",
        }

    output = output.strip()

    # --------------------------------------------------------
    # TITLE
    # --------------------------------------------------------

    title_match = re.search(
        r"TITLE\s*:\s*(.+?)(?=\n|$)",
        output,
        re.IGNORECASE,
    )

    if title_match:

        title = (
            title_match
            .group(1)
            .strip()
        )

    # --------------------------------------------------------
    # KEYPOINT 1 / KEYPOINT 2
    # --------------------------------------------------------

    numbered_matches = re.findall(
        r"KEYPOINT\s*(?:1|2)\s*:\s*(.+?)(?=\n|$)",
        output,
        re.IGNORECASE,
    )

    for point in numbered_matches:

        point = point.strip()

        point = re.sub(
            r"^[•\-*]\s*",
            "",
            point,
        )

        if point:
            keypoints.append(
                point
            )

    # --------------------------------------------------------
    # GENERIC KEYPOINT
    # --------------------------------------------------------

    if not keypoints:

        generic_matches = re.findall(
            r"KEYPOINT\s*:\s*(.+?)(?=\n|$)",
            output,
            re.IGNORECASE,
        )

        for point in generic_matches:

            point = point.strip()

            point = re.sub(
                r"^[•\-*]\s*",
                "",
                point,
            )

            if point:
                keypoints.append(
                    point
                )

    # --------------------------------------------------------
    # BULLET FALLBACK
    # --------------------------------------------------------

    if not keypoints:

        for line in output.splitlines():

            line = line.strip()

            if not line:
                continue

            if re.match(
                r"^TITLE\s*:",
                line,
                re.IGNORECASE,
            ):
                continue

            if re.match(
                r"^KEYPOINT\s*(?:1|2)?\s*:?",
                line,
                re.IGNORECASE,
            ):
                continue

            if re.match(
                r"^[•\-*]",
                line,
            ):

                line = re.sub(
                    r"^[•\-*]\s*",
                    "",
                    line,
                )

                if line:
                    keypoints.append(
                        line
                    )

            if len(keypoints) >= 2:
                break

    # --------------------------------------------------------
    # CLEANUP
    # --------------------------------------------------------

    cleaned_keypoints = []

    for point in keypoints:

        point = point.strip()

        point = re.sub(
            r"^[•\-*]\s*",
            "",
            point,
        )

        if point:
            cleaned_keypoints.append(
                point
            )

    cleaned_keypoints = (
        cleaned_keypoints[:2]
    )

    return {
        "title": title,
        "keypoints": "\n".join(
            f"• {point}"
            for point in cleaned_keypoints
        ),
    }


# ============================================================
# GET NEWS FOR PROJECT
# ============================================================

def get_news_for_project(
    project_id,
):

    workbook = get_workbook()

    if NEWS_SHEET not in workbook.sheetnames:
        return []

    sheet = workbook[
        NEWS_SHEET
    ]

    headers = [
        cell.value
        for cell in sheet[1]
    ]

    news = []

    for row in sheet.iter_rows(
        min_row=2,
        values_only=True,
    ):

        record = dict(
            zip(headers, row)
        )

        if (
            str(record.get("Project ID"))
            == str(project_id)
        ):

            news.append(
                record
            )

    return news


# ============================================================
# SAVE NEWS
# ============================================================

def save_news_items(
    project_id,
    project_name,
    news_items,
):

    workbook = get_workbook()

    sheet = ensure_news_sheet(
        workbook
    )

    new_items = []
    updated_items = []

    now = datetime.now().isoformat()

    headers = [
        cell.value
        for cell in sheet[1]
    ]

    project_id_index = headers.index(
        "Project ID"
    )

    url_index = headers.index(
        "URL"
    )

    for result in news_items:

        url = result.get(
            "url"
        )

        if not url:
            continue

        url = url.strip()

        title = (
            result.get("title")
            or "Untitled Update"
        )

        content = (
            result.get("content")
            or ""
        )

        published_date = (
            result.get(
                "published_date"
            )
        )

        source = result.get(
            "source"
        )

        if not source:

            try:

                source = (
                    url
                    .split("//", 1)[1]
                    .split("/", 1)[0]
                )

            except Exception:

                source = ""

        # ----------------------------------------------------
        # GENERATE AI SUMMARY
        # ----------------------------------------------------

        summary = generate_news_summary(
            project_name=project_name,
            title=title,
            content=content,
        )

        final_title = summary[
            "title"
        ]

        keypoints = summary[
            "keypoints"
        ]

        # ----------------------------------------------------
        # FIND EXISTING URL
        # ----------------------------------------------------

        existing_row = None

        for row_number in range(
            2,
            sheet.max_row + 1,
        ):

            row_project_id = sheet.cell(
                row=row_number,
                column=project_id_index + 1,
            ).value

            row_url = sheet.cell(
                row=row_number,
                column=url_index + 1,
            ).value

            if (
                str(row_project_id)
                == str(project_id)
                and row_url
                and str(row_url).strip()
                == url
            ):

                existing_row = row_number
                break

        # ----------------------------------------------------
        # UPDATE EXISTING NEWS
        # ----------------------------------------------------

        if existing_row:

            values = [
                project_id,
                project_name,
                published_date,
                final_title,
                keypoints,
                source,
                url,
                now,
            ]

            for column, value in enumerate(
                values,
                start=1,
            ):

                sheet.cell(
                    row=existing_row,
                    column=column,
                    value=value,
                )

            updated_items.append({
                "Project ID": project_id,
                "Project Name": project_name,
                "News Date": published_date,
                "News Title": final_title,
                "Keypoints": keypoints,
                "Source": source,
                "URL": url,
                "Last Updated": now,
            })

        # ----------------------------------------------------
        # INSERT NEW NEWS
        # ----------------------------------------------------

        else:

            values = [
                project_id,
                project_name,
                published_date,
                final_title,
                keypoints,
                source,
                url,
                now,
            ]

            sheet.append(
                values
            )

            new_items.append({
                "Project ID": project_id,
                "Project Name": project_name,
                "News Date": published_date,
                "News Title": final_title,
                "Keypoints": keypoints,
                "Source": source,
                "URL": url,
                "Last Updated": now,
            })

    workbook.save(
        EXCEL_FILE
    )

    return (
        new_items,
        updated_items,
    )


# ============================================================
# REFRESH PROJECT NEWS
# ============================================================

def refresh_project_news(
    project_id,
    project_name,
):

    print(
        f"\n[NEWS] Refreshing project: "
        f"{project_name}"
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search_results = search_project_news(
        project_name
    )

    if not search_results:

        existing_news = (
            get_news_for_project(
                project_id
            )
        )

        return {
            "project_id": project_id,
            "project_name": project_name,
            "new_items": [],
            "updated_items": [],
            "new_count": 0,
            "updated_count": 0,
            "total_items": len(
                existing_news
            ),
        }

    # --------------------------------------------------------
    # SAVE
    # --------------------------------------------------------

    new_items, updated_items = (
        save_news_items(
            project_id=project_id,
            project_name=project_name,
            news_items=search_results,
        )
    )

    # --------------------------------------------------------
    # GET FINAL DATA
    # --------------------------------------------------------

    all_news = get_news_for_project(
        project_id
    )

    return {
        "project_id": project_id,
        "project_name": project_name,
        "new_items": new_items,
        "updated_items": updated_items,
        "new_count": len(
            new_items
        ),
        "updated_count": len(
            updated_items
        ),
        "total_items": len(
            all_news
        ),
    }