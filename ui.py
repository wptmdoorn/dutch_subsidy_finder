from nicegui import ui
import asyncio
import logging
from pathlib import Path

from src.config import Config
from src.scraper_manager import ScraperManager
from src.data_processor import DataProcessor
from src.excel_exporter import ExcelExporter
from src.utils import setup_logging

# Setup logging for the web app
setup_logging()
logger = logging.getLogger(__name__)

# State
class AppState:
    def __init__(self):
        self.subsidies = []
        self.excel_path = None
        self.loading = False
        self.error = None
        self.info = None

state = AppState()

# UI elements (to be assigned later)
table = None
search_input = None
download_btn = None
spinner = None
info_message = None

# Async function to run the full pipeline
async def run_pipeline(search_keywords=None):
    state.loading = True
    state.error = None
    state.info = None
    state.subsidies = []
    state.excel_path = None
    if spinner:
        spinner.visible = True
    if info_message:
        info_message.text = ''
    try:
        scraper_manager = ScraperManager()
        data_processor = DataProcessor()
        excel_exporter = ExcelExporter()

        # Step 1: Scrape all funding sources
        raw_subsidies = await scraper_manager.scrape_all_sources()

        # Step 2: Optionally filter by search keywords
        if search_keywords:
            keywords = [k.strip().lower() for k in search_keywords.split(',') if k.strip()]
            filtered = []
            for s in raw_subsidies:
                text = ' '.join(str(s.get(f, '')) for f in ['name','description','research_areas','eligibility']).lower()
                if any(k in text for k in keywords):
                    filtered.append(s)
            raw_subsidies = filtered

        # Step 3: Process and filter data
        processed_subsidies = data_processor.process_subsidies(raw_subsidies)
        state.subsidies = processed_subsidies

        # Step 4: Export to Excel
        if processed_subsidies:
            excel_path = excel_exporter.export_subsidies(processed_subsidies)
            state.excel_path = excel_path
            state.info = f"Found {len(processed_subsidies)} subsidies."
        else:
            state.excel_path = None
            state.info = "No subsidies found for your search."
    except Exception as e:
        logger.error(f"Web UI pipeline failed: {e}")
        state.error = str(e)
    finally:
        state.loading = False
        if spinner:
            spinner.visible = False
        refresh_table()
        update_download_btn()
        update_info_message()

# UI Layout

def refresh_table():
    if not table:
        return
    # Clear and repopulate table
    table.rows.clear()
    if not state.subsidies:
        return
    for s in state.subsidies:
        table.add_row([
            s.get('name',''),
            s.get('funding_organization',''),
            s.get('amount',''),
            s.get('deadline',''),
            s.get('status',''),
            s.get('eligibility',''),
            s.get('research_areas',''),
            s.get('description',''),
            s.get('researcher_level',''),
            s.get('url',''),
            s.get('relevance_score',''),
        ])

def update_download_btn():
    if not download_btn:
        return
    if state.excel_path and Path(state.excel_path).exists():
        download_btn.enable()
    else:
        download_btn.disable()

def update_info_message():
    if not info_message:
        return
    if state.error:
        info_message.text = f"[b][red]Error: {state.error}[/red][/b]"
    elif state.info:
        if 'No subsidies found' in state.info:
            info_message.text = f"[b][red]{state.info}[/red][/b]"
        else:
            info_message.text = f"[b][green]{state.info}[/green][/b]"
    else:
        info_message.text = ''

async def on_search():
    if spinner:
        spinner.visible = True
    await run_pipeline(search_input.value)
    # All UI updates are handled in run_pipeline's finally block

async def on_download():
    if not (state.excel_path and Path(state.excel_path).exists()):
        ui.notify("No Excel file available to download.", type='warning')
        return
    await ui.download(state.excel_path)

# --- UI Construction ---

ui.add_head_html("""
<style>
body { background: #f6f8fa; min-height: 100vh; }
.nicegui-outer-center {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    justify-content: center;
    align-items: center;
}
.nicegui-centered-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    padding: 32px 32px 24px 32px;
    min-width: 350px;
    max-width: 900px;
    width: 90vw;
    margin: 0 auto;
}
.nicegui-title {
    font-size: 2.2rem;
    font-weight: 700;
    color: #1a237e;
    margin-bottom: 0.5em;
    text-align: center;
}
.nicegui-subtitle {
    font-size: 1.1rem;
    color: #333;
    margin-bottom: 1.5em;
    text-align: center;
}
</style>
""")

with ui.element('div').classes('nicegui-outer-center'):
    with ui.column().classes('items-center'):
        with ui.card().classes('nicegui-centered-card'):
            ui.markdown("# Dutch Subsidy Finder Web UI").classes('nicegui-title')
            ui.markdown("Search for Dutch research & innovation subsidies and download results as Excel.").classes('nicegui-subtitle')
            with ui.row().classes('w-full justify-center'):
                search_input = ui.input("Search keywords (comma-separated)", placeholder="e.g. AI, clinical chemistry, diagnostics").classes('w-80')
                ui.button("Search", on_click=on_search, color='primary').props('unelevated')
                download_btn = ui.button("Download Excel", on_click=on_download, color='secondary').props('unelevated')
            spinner = ui.spinner(size='lg', color='primary')
            spinner.visible = False
            ui.separator()
            info_message = ui.markdown("").classes('w-full mb-2')
            columns = [
                "Subsidy Name", "Funding Organization", "Amount/Budget", "Application Deadline", "Status",
                "Eligibility Criteria", "Research Areas", "Description", "Researcher Level", "Website URL", "Relevance Score"
            ]
            table = ui.table(columns=columns, rows=[], row_key="Subsidy Name", pagination=10).classes('w-full')

ui.run(title="Dutch Subsidy Finder", reload=False) 