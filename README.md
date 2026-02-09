# Stat370-PlanB

STAT 370 Plan B Project - Major Recommender System

A collaborative project with Dr. Catherine Putonti at Loyola University Chicago to help students discover alternative major paths based on their completed coursework.

## Project Overview

This system analyzes student enrollment data and bachelor's degree requirements to recommend alternative majors that students may be well-positioned to pursue based on credits they've already earned.

**This project is still a work in progress. Next implementations will be:**

* Student will have an option to only view majors that they will be able to complete in four years of enrollment.
* Changes made to web scraping script to remove errors from data collection process.

### Project Demo

A small demo for the first version of this project can be found here:




https://github.com/user-attachments/assets/9c73c339-51de-4c86-a435-e9e02cb55dff



### Key Features

- **Data Collection**: Web scraping of Loyola University course catalog for major requirements
- **Student Analysis**: Processing of de-identified enrollment data
- **Smart Recommendations**: Algorithm to match student coursework with major requirements
- **Web Interface**: Flask-based application for students to view recommendations

## Project Structure

```
Stat370-PlanB/
├── data_gathering_scripts/    # Scripts to collect and prepare data
├── dev_scripts/                # Major recommender system and web app
├── test_scripts/               # Testing and validation scripts
├── utils/                      # Shared utilities and path management
├── original_data/              # Original enrollment data files
├── filtered_data/              # Processed data and scraped requirements
├── data_analysis/              # Analysis notebooks and outputs
└── test_output/                # Test script outputs
```

See individual folder README files for detailed documentation.

## Quick Start

### Prerequisites

```bash
pip install pandas flask beautifulsoup4 requests PyPDF2
```

### Running the Major Recommender

1. **Prepare Data** (if needed):

```bash
python data_gathering_scripts/dataprep.py
python data_gathering_scripts/scrape_majors_from_web.py
python data_gathering_scripts/scrape_course_details.py
```

2. **Run Web Application**:

```bash
python dev_scripts/planb.py
```

3. **Access Application**:

- Open browser to `http://localhost:5001`
- Login with student ID (password: `1234` for demo)

## Data Sources

- **Student Enrollment**: De-identified enrollment data (Fall 2016 - Spring 2021)
- **Major Requirements**: Scraped from Loyola University Chicago course catalog
- **Course Details**: Scraped course information including prerequisites and descriptions

## Documentation

- [data_gathering_scripts/README.md](data_gathering_scripts/README.md) - Data collection and preparation
- [dev_scripts/README.md](dev_scripts/README.md) - Major recommender system
- [test_scripts/README.md](test_scripts/README.md) - Testing utilities
- [utils/README.md](utils/README.md) - Shared utilities

## Contributors

- Oscar Sanchez Huezca
- Dr. Catherine Putonti (Project Advisor)
- Loyola University Chicago

## License

This project is developed for educational purposes at Loyola University Chicago.

## Privacy Note

All student enrollment data has been de-identified to protect student privacy. No personally identifiable information is included in this repository.
