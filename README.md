
# 📈 Google Trend Intelligence
### Cross-Platform Search Demand & Content Supply Analytics

A Python-based data analytics project that combines **Google Trends** and **YouTube Data API v3** to analyze emerging technology trends, search interest, content supply, and audience engagement.

The project transforms data from two different platforms into structured, analysis-ready datasets to help identify trending topics, measure momentum, and explore potential content opportunities.

**Project Status:** Local data ingestion and exploratory analytics implemented | Cloud deployment planned

---

## 🎯 Project Overview

### The Problem

Identifying emerging trends requires more than looking at search popularity alone.

A topic may receive significant attention on Google, but that does not necessarily indicate how much content exists on YouTube or how audiences interact with that content.

Analyzing these platforms independently makes it difficult to understand the relationship between **audience search demand, content availability, and engagement**.

### The Solution

Google Trend Intelligence brings together two complementary data sources:

- **Google Trends:** Measures relative search interest and changes in topic popularity.
- **YouTube:** Provides information about recently published videos, content availability, views, likes, comments, and engagement.

The project builds a cross-source analytical dataset to compare topics and identify patterns that would be difficult to observe from either platform individually.

### Key Questions

1. Which emerging technology topics are attracting the most search interest?
2. Which topics are gaining or losing momentum?
3. How much YouTube content is available for each topic?
4. Which topics demonstrate stronger audience engagement?
5. Are there topics showing high search interest but relatively lower content supply?

---

## 🛠️ Technology Stack

| Category | Technologies |
|---|---|
| Programming | Python 3.11+ |
| Data Analysis | Pandas |
| Search Trend Data | Google Trends |
| Google Trends Client | pytrends-modern |
| Video Data | YouTube Data API v3 |
| API Integration | Google API Python Client |
| Configuration | python-dotenv |
| Data Storage | CSV, JSON |
| Package Management | pip, setuptools |
| Logging | Python logging |
| Development | Git, GitHub |

---

## 🏗️ Data Architecture

The project follows a layered approach that separates data collection, transformation, and analytics.

```text
               EXTERNAL DATA SOURCES
               ─────────────────────
                  Google Trends
                        |
                  YouTube Data API
                        |
                        v
                 DATA INGESTION
                 ──────────────
              Google Trends Client
              YouTube Search API
              YouTube Video Details API
                        |
                        v
                  RAW DATA LAYER
                  ──────────────
                   JSON / CSV
                Collection Metadata
                 Run Identifiers
                        |
                        v
                TRANSFORMATION LAYER
                ────────────────────
                Data Type Validation
                Missing Value Checks
                Wide-to-Long Reshaping
                Video-Topic Mapping
                Feature Engineering
                        |
                        v
                  ANALYTICS LAYER
                  ───────────────
                  Search Momentum
                  Topic-Level KPIs
                  Video Engagement
                  Content Supply
                        |
                        v
                CROSS-SOURCE ANALYSIS
                ─────────────────────
                 Search Demand
                       vs.
                 Content Supply
                       vs.
                 Video Engagement
                        |
                        v
                 ANALYTICAL INSIGHTS
```

**Implementation note:** The reusable package under `src/trend_intel/` currently handles raw ingestion and persistence. Data transformations and analytical outputs are implemented through separate standalone scripts in the repository.

---

## 📊 Topics Analyzed

The default topic basket focuses on five emerging technology concepts:

| Topic | Focus |
|---|---|
| AI Agents | Autonomous AI systems and task execution |
| Agentic AI | AI-driven decision-making and workflows |
| Vibe Coding | AI-assisted software development |
| Model Context Protocol | Connecting AI applications to external tools and data |
| Multimodal AI | AI systems processing multiple information formats |

### Geographic Scope

- **Region:** Canada (CA)
- **Google Trends Window:** Previous 3 months
- **YouTube Window:** Previous 7 complete UTC days
- **Google Trends Comparison:** Shared 0–100 relative interest scale

The topics, geographic region, and analysis windows can be customized through environment variables in the reusable pipeline.

---

## ⚙️ Implemented Features

### 1. Google Trends Data Collection

The project retrieves Google Trends interest-over-time data for multiple topics.

Capabilities include:

- Comparing up to five topics within a single request.
- Retrieving time-series search interest data.
- Preserving partial-observation indicators.
- Capturing collection timestamps and request metadata.
- Storing raw data in CSV and JSON formats.
- Retrying failed requests in the reusable ingestion pipeline.

**Why it matters:** Comparing topics within the same Google Trends request preserves a shared relative interest scale.

### 2. YouTube Data Collection

The YouTube Data API v3 is used to retrieve recent video information for each topic.

The collection process includes:

- Searching for recently published videos.
- Retrieving video identifiers and metadata.
- Fetching video statistics in batches.
- Capturing views, likes, comments, publication dates, and duration.
- Deduplicating video identifiers across topic searches.
- Preserving relationships when a video matches multiple topics.
- Capturing API request metadata and collection timestamps.

### 3. Data Cleaning and Transformation

Standalone transformation scripts convert raw API responses into structured analytical datasets.

Processing includes:

- Data type standardization.
- Timestamp parsing.
- Missing-value inspection.
- Duplicate checks.
- Wide-to-long transformations.
- Video-to-topic relationship modeling.
- Feature engineering.

### 4. Search Trend Momentum Analysis

Google Trends data is used to evaluate topic-level changes in search interest.

Metrics include:

- Latest complete interest score.
- Recent seven-day average interest.
- Previous seven-day average interest.
- Change in interest points.
- Topic momentum classification.

Topics are classified into categories such as:

- Rising
- Declining
- Stable
- Low signal

### 5. YouTube Engagement Analytics

The project derives video-level and topic-level engagement measures.

Metrics include:

- View counts.
- Median views.
- Views per hour since publication.
- Visible interactions per 100 views.
- Engagement metric coverage.
- Video age and duration.
- Content language classification.

The analytical scripts also evaluate minimum-view thresholds to reduce the influence of very small video samples on interaction metrics.

### 6. Cross-Source Topic Analysis

The project joins Google Trends topic KPIs with YouTube topic KPIs and supply-related indicators.

This creates a unified dataset containing:

| Dimension | Example Metrics |
|---|---|
| Search Demand | Latest interest, 7-day average |
| Momentum | Interest change, trend direction |
| Content Supply | Estimated indexed results, relative supply index |
| Audience Attention | Median views, views per hour |
| Engagement | Visible interactions per 100 views |
| Data Quality | Interaction coverage, missing values |
| Context | Collection timestamps, analysis windows |

The resulting dataset supports exploratory comparisons between search popularity, content availability, and audience engagement.

---

## 📁 Repository Structure

```text
google-trend-intelligence/
│
├── src/
│   └── trend_intel/
│       ├── __init__.py
│       ├── config.py
│       ├── pipeline.py
│       ├── run_context.py
│       ├── logging_setup.py
│       ├── storage.py
│       │
│       └── sources/
│           ├── __init__.py
│           ├── trends.py
│           └── youtube.py
│
├── google_trends_topic_basket.py
├── google_trends_transform.py
├── google_trends_topic_kpis.py
├── google_trends_eda.py
├── google_trends_compare.py
│
├── youtube_topic_basket_search.py
├── youtube_topic_basket_details.py
├── youtube_topic_basket_transform.py
├── youtube_engagement_features.py
├── youtube_topic_kpis.py
├── youtube_quality_audit.py
├── youtube_supply_diagnostic.py
│
├── cross_source_topic_analysis.py
│
├── .env.example
├── .gitignore
├── requirements.txt
└── pyproject.toml
```

Additional exploratory scripts are included in the repository.

Generated datasets are stored locally under `data/raw/` and `data/processed/`.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11 or newer
- Git
- YouTube Data API v3 key
- Internet connection

### Step 1: Clone the Repository

```bash
git clone https://github.com/jaswanthk20/google-trend-intelligence.git
cd google-trend-intelligence
```

### Step 2: Create a Virtual Environment

```bash
python -m venv .venv
```

Activate the environment.

**Windows PowerShell:**

```powershell
.venv\Scripts\Activate.ps1
```

**macOS / Linux:**

```bash
source .venv/bin/activate
```

### Step 3: Install Dependencies

Install the project package:

```bash
pip install -e .
```

Alternatively, install the listed dependencies:

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Credentials

Copy the example environment file:

```bash
cp .env.example .env
```

Add your YouTube API key:

```env
YOUTUBE_API_KEY=your_youtube_api_key
```

You can obtain a key through [Google Cloud Console](https://console.cloud.google.com/).

Enable **YouTube Data API v3** for your Google Cloud project before making API requests.

Never commit real API keys or your `.env` file to GitHub.

### Step 5: Run the Reusable Ingestion Pipeline

Collect data from both sources:

```bash
python -m trend_intel.pipeline --source all
```

Collect only Google Trends data:

```bash
python -m trend_intel.pipeline --source trends
```

Collect only YouTube data:

```bash
python -m trend_intel.pipeline --source youtube
```

The pipeline records a unique run ID, collection timestamp, source status, and generated artifact paths.

**Note:** This command currently handles raw data ingestion. The standalone analytics scripts described below implement the transformation and KPI stages separately.

---

## 🔄 Running the Standalone Analytics Workflow

The repository also contains an exploratory workflow for producing processed datasets and cross-source KPIs.

Run these commands from the repository root.

### Google Trends

```bash
python google_trends_topic_basket.py
python google_trends_transform.py
python google_trends_topic_kpis.py
```

### YouTube

```bash
python youtube_topic_basket_search.py
python youtube_topic_basket_details.py
python youtube_topic_basket_transform.py
python youtube_engagement_features.py
python youtube_topic_kpis.py
```

### Cross-Source Analysis

After both sources have generated their topic-level KPI files:

```bash
python cross_source_topic_analysis.py
```

This produces a combined analytical dataset in:

```text
data/processed/combined/
```

**Important:** The standalone scripts have their own output filename conventions and input expectations. They should be run as the standalone workflow rather than assuming every output from the newer packaged pipeline is directly compatible.

---

## 📐 Analytical Methodology

### Search Momentum

Search momentum is evaluated by comparing recent search interest with the preceding period.

```text
Search Interest Change =
Recent 7-Day Average - Previous 7-Day Average
```

A positive change indicates increasing relative search interest; a negative change indicates declining interest.

### Views per Hour

```text
Views per Hour =
Total Video Views / Hours Since Publication
```

This metric provides a simple lifetime-average measure of attention adjusted for video age.

It is not a direct measure of current view growth.

### Visible Interaction Rate

```text
Visible Interactions per 100 Views =
((Likes + Comments) / Views) × 100
```

The metric uses visible interaction statistics available from the YouTube API.

### Relative Content Supply

```text
Relative Supply Index =
(Estimated Indexed Results for Topic /
 Maximum Estimated Indexed Results Across Topics) × 100
```

This metric provides a relative comparison across the tracked topic basket.

YouTube search result estimates are approximate and should not be interpreted as exact counts of all published videos.

---

## 🔍 Data Quality and Reliability

The project incorporates several reliability-focused design decisions.

| Design Decision | Purpose |
|---|---|
| Raw Data Preservation | Supports reproducibility and reprocessing |
| Collection Timestamps | Tracks data freshness |
| Unique Run Identifiers | Supports ingestion traceability |
| Duplicate Validation | Helps protect analytical accuracy |
| Shared Trends Comparison | Preserves comparable interest scores |
| Complete UTC-Day Windows | Reduces partial-day reporting bias |
| YouTube Request Batching | Reduces unnecessary API calls |
| Retry and Backoff Logic | Handles intermittent Trends failures |
| Source-Level Failure Tracking | Makes partial ingestion failures visible |
| Structured Logging | Supports troubleshooting and future cloud operations |

### API Quota Awareness

YouTube Data API v3 applies quota costs to API operations.

Typical costs include:

- `search.list`: 100 units per request.
- `videos.list`: 1 unit per request.

With five topics and approximately 250 unique videos, a collection run requires approximately **505 quota units**.

Actual usage depends on the returned video count and number of requests.

---

## ⚠️ Analytical Limitations

Several important limitations should be considered when interpreting results.

**1. Google Trends uses relative interest.**

Values are normalized rather than representing absolute search volumes.

**2. YouTube search results are sampled.**

The current ingestion approach retrieves a limited number of results per topic. It does not capture every video published on the platform.

**3. Engagement statistics change over time.**

Video views and interaction counts are snapshots taken at collection time.

**4. Topic popularity does not establish causation.**

High Google search interest does not necessarily cause higher YouTube engagement.

**5. Search and video analysis windows differ.**

Google Trends and YouTube capture different observation periods and measurement units. Comparisons are therefore exploratory.

**6. Google Trends availability can vary.**

The unofficial Trends client may encounter rate limiting or temporary failures.

These considerations are important for producing reliable and responsible insights.

---

## 🗺️ Development Roadmap

### Phase 1 — Data Ingestion and Exploratory Analytics

- [x] Google Trends data collection
- [x] YouTube API integration
- [x] Raw JSON and CSV storage
- [x] Data cleaning and transformation scripts
- [x] Search momentum analysis
- [x] YouTube engagement analysis
- [x] Topic-level KPI generation
- [x] Cross-source analytical dataset
- [x] Reusable ingestion package
- [x] Run metadata and logging

### Phase 2 — Pipeline Integration and Automation

- [ ] Integrate transformations into the reusable pipeline
- [ ] Expand automated testing
- [ ] Schedule recurring ingestion
- [ ] Deploy ingestion using Google Cloud services
- [ ] Implement cloud-based monitoring and error reporting

### Phase 3 — Cloud Data Engineering

- [ ] Load historical observations into BigQuery
- [ ] Implement incremental data loading
- [ ] Design analytical data models
- [ ] Add data freshness and validation checks
- [ ] Preserve historical trend snapshots

### Phase 4 — Visualization and Decision Support

- [ ] Build an interactive analytical dashboard
- [ ] Visualize topic momentum over time
- [ ] Compare demand, supply, and engagement
- [ ] Explore topic opportunity scoring
- [ ] Add historical trend comparisons

### Phase 5 — Advanced Analytics

- [ ] Evaluate statistical relationships between sources
- [ ] Explore anomaly detection
- [ ] Experiment with forecasting models
- [ ] Assess the reliability of predictive indicators

---

## 💼 Business Applications

The analytical framework can support several business use cases.

**Content Strategy**

Identify topics attracting search interest and assess the competitive content environment.

**Market Research**

Track emerging technology conversations and changes in audience attention.

**Marketing Analytics**

Compare search interest with observable engagement indicators.

**Competitive Intelligence**

Explore which topics have greater content availability and stronger audience response.

**Trend Monitoring**

Track the evolution of selected topics through repeated data collection.

---

## 🧠 Key Engineering Concepts Demonstrated

This project provides hands-on experience in:

- REST API integration and external data collection.
- Data ingestion and raw data preservation.
- ETL and data transformation.
- Feature engineering and KPI development.
- Data validation and quality checks.
- Relational data modeling using video-topic mappings.
- Cross-source data integration.
- API quota management.
- Configuration-driven development.
- Logging, traceability, and pipeline orchestration.

The longer-term objective is to evolve the exploratory workflow into a continuously updating analytics system.

---

## 👨‍💻 Author

**Jaswanth Kumar**

Industrial Engineering | Data Analytics | Data Engineering | Business Intelligence

GitHub: [@jaswanthk20](https://github.com/jaswanthk20)

---

## ⭐ Project Motivation

This project was developed to explore how information from different digital platforms can be integrated into a meaningful analytical system.

Rather than relying on a single trend metric, the goal is to build an evidence-based framework that combines search behavior, content availability, and audience engagement.

It is an evolving portfolio project focused on developing practical skills in **data analytics, data engineering, API integration, and analytical decision-making**.
