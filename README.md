# Dutch Subsidy Finder

A comprehensive tool for finding Dutch research and innovation subsidies, specifically tailored for clinical chemistry and AI research opportunities.

## Overview

This application automatically scrapes major Dutch funding sources to identify relevant subsidies and grants for research and innovation projects. It focuses on opportunities in clinical chemistry, AI, healthcare technology, and related fields.

## Features

- **Multi-source scraping**: Covers NWO, ZonMw, RVO, Horizon Europe, and Health~Holland
- **Smart filtering**: Uses keyword matching and relevance scoring
- **Excel export**: Professional formatted output with summary statistics
- **Clinical chemistry & AI focus**: Optimized for your research area
- **Comprehensive data**: Includes deadlines, amounts, eligibility, and application processes

## Funding Sources Covered

1. **NWO** (Nederlandse Organisatie voor Wetenschappelijk Onderzoek)
2. **ZonMw** (Nederlandse organisatie voor gezondheidsonderzoek en zorginnovatie)
3. **RVO** (Rijksdienst voor Ondernemend Nederland)
4. **Horizon Europe** (EU funding with Dutch participation focus)
5. **Health~Holland** (Dutch health technology ecosystem)

## Installation

1. **Clone or download** this project to your computer

2. **Install Python dependencies**:
   ```bash
   cd dutch_subsidy_finder
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   python -c "import aiohttp, bs4, pandas, openpyxl; print('All dependencies installed successfully!')"
   ```

## Usage

### Basic Usage

Run the application from the project directory:

```bash
python main.py
```

The application will:
1. Scrape all configured funding sources
2. Filter and score subsidies based on relevance
3. Export results to Excel in the `output/` directory
4. Display a summary report

### Output

The application generates:
- **Excel file** with detailed subsidy information
- **Summary sheet** with statistics and keyword analysis
- **Log file** in the `logs/` directory for debugging

### Excel Output Columns

- Subsidy Name
- Funding Organization
- Amount/Budget
- Application Deadline
- Status (Open/Closed)
- Eligibility Criteria
- Research Areas
- Description
- Application Process
- Contact Information
- Website URL
- Relevance Score (1-10)
- Keywords Matched
- Date Scraped

## Configuration

### Research Keywords

The application is pre-configured with keywords relevant to clinical chemistry and AI research. You can modify these in `src/config.py`:

```python
RESEARCH_KEYWORDS = [
    'clinical chemistry', 'klinische chemie', 'laboratory medicine',
    'artificial intelligence', 'AI', 'machine learning',
    'healthcare', 'medical technology', 'diagnostics',
    # ... add your specific keywords
]
```

### Relevance Scoring

Subsidies are scored based on keyword matches in:
- Title (weight: 3.0)
- Description (weight: 2.0)
- Research areas (weight: 1.5)
- Eligibility criteria (weight: 1.0)

Minimum relevance score: 3.0 (configurable)

## Project Structure

```
dutch_subsidy_finder/
├── main.py                 # Main application entry point
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── src/
│   ├── config.py          # Configuration settings
│   ├── scraper_manager.py # Coordinates all scrapers
│   ├── data_processor.py  # Filters and scores data
│   ├── excel_exporter.py  # Creates Excel output
│   ├── utils.py           # Utility functions
│   └── scrapers/          # Individual source scrapers
│       ├── nwo_scraper.py
│       ├── zonmw_scraper.py
│       ├── rvo_scraper.py
│       ├── horizon_scraper.py
│       └── health_holland_scraper.py
├── output/                # Generated Excel files
└── logs/                  # Application logs
```

## Customization

### Adding New Funding Sources

1. Create a new scraper in `src/scrapers/`
2. Add the source configuration to `src/config.py`
3. Register the scraper in `src/scraper_manager.py`

### Modifying Relevance Scoring

Adjust scoring weights in `src/config.py`:

```python
SCORING_WEIGHTS = {
    'title_match': 3.0,
    'description_match': 2.0,
    'keywords_match': 1.5,
    'eligibility_match': 1.0,
    'deadline_bonus': 0.5
}
```

### Changing Output Format

Modify column configuration in `src/config.py`:

```python
EXCEL_COLUMNS = [
    'Subsidy Name',
    'Funding Organization',
    # ... customize as needed
]
```

## Technical Details

- **Language**: Python 3.8+
- **Async scraping**: Uses aiohttp for concurrent requests
- **Rate limiting**: Respects website policies with delays
- **Error handling**: Robust retry mechanisms
- **Data validation**: Cleans and standardizes extracted data

## Troubleshooting

### Common Issues

1. **Import errors**: Ensure all dependencies are installed
   ```bash
   pip install -r requirements.txt
   ```

2. **Network timeouts**: Check internet connection and firewall settings

3. **Empty results**: Some websites may block automated access - this is normal

4. **Permission errors**: Ensure write permissions for `output/` and `logs/` directories

### Logs

Check the log file in `logs/subsidy_finder.log` for detailed error information.

## Legal and Ethical Considerations

- This tool respects robots.txt and implements rate limiting
- Only publicly available information is collected
- No personal data is stored or transmitted
- Use responsibly and in accordance with website terms of service

## Support

For issues or questions:
1. Check the log files for error details
2. Verify all dependencies are installed correctly
3. Ensure stable internet connection
4. Review the configuration settings

## License

This tool is provided for research and educational purposes. Please respect the terms of service of the websites being scraped.

---

**Note**: This tool provides automated assistance in finding funding opportunities. Always verify information directly with funding organizations before applying.
