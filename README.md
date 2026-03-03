# Spotify-Listening-Analytics-API

## Overview

The Spotify Listening Analytics API is a RESTful data analytics system designed to process, store, and analyze extended Spotify streaming history data at the event level. The system ingests raw streaming history JSON exports, normalizes them into a structured SQLite database, and exposes aggregated behavioral listening metrics through well-defined API endpoints.

The architecture mirrors a professional data engineering workflow, emphasizing data integrity, reproducibility, modular design, and scalable aggregation logic. The system transforms raw event logs into structured analytical features such as listening duration, artist-level aggregation, track-level metrics, and temporal usage patterns (hour-of-day and day-of-week distributions). It reflects production-style API design combined with database-backed analytics.

## Architecture
### Data Ingestion Layer:

Extended Spotify streaming history JSON files (Streaming_History_Audio_*.json) are programmatically parsed and normalized. Each streaming event is processed at the record level and inserted into a relational SQLite database using idempotent insertion logic (INSERT OR IGNORE) to prevent duplicate entries.

### Data Modeling Layer:

A normalized relational schema stores streaming events in a structured plays table. Key attributes include:
• played_at (timestamp)
• ms_played (listening duration)
• content_type (track or episode)
• track metadata (track_name, artist, album)
• episode metadata (episode_name, episode_show_name)
• playback context (platform, country, shuffle, skipped, offline)
• start/end reasons

A composite UNIQUE constraint ensures event-level deduplication.

### Aggregation Layer:

SQL-based aggregation queries compute listening metrics such as:
• Total listening time by artist
• Total listening time by track
• Listening distribution by hour of day
• Listening distribution by day of week
• Time-normalized engagement metrics (milliseconds → minutes)

All aggregations are executed directly in SQL to leverage database-level performance optimization.

### API Layer:

A Flask-based REST interface exposes analytical endpoints including:
• /api/recently-played
• /api/stats/top-artists
• /api/stats/top-tracks
• /api/stats/listening-by-hour
• /api/stats/listening-by-dow

Endpoints return structured JSON responses suitable for frontend dashboards or external analytics systems.

### Data Integrity & Validation Layer:

• Strict filtering of incomplete records (missing timestamps or duration)
• Explicit classification of content type (track vs episode)
• Boolean normalization for skipped, shuffle, and offline states
• Deduplication through composite key constraints

## Key Technologies

### Python Ecosystem:
• Flask for REST API development
• sqlite3 for relational storage
• json and glob for file parsing
• os for environment-aware path management

### SQLite:
• Structured relational schema design
• Aggregate SQL queries for behavioral analytics
• Unique constraints for idempotent ingestion

### Data Engineering Patterns:
• Event-level log normalization
• Deduplicated batch ingestion
• SQL-first aggregation logic
• Reproducible database initialization

## Features
### Event-Level Streaming Analytics:

Processes raw Spotify streaming logs into structured relational data for analytical querying.

### Idempotent Data Import:

Implements INSERT OR IGNORE with composite uniqueness constraints to prevent duplicate event insertion during repeated imports.

### Artist-Level Aggregation:

Computes total listening duration by artist, ranked by cumulative engagement time.

### Track-Level Aggregation:

Aggregates track-level listening duration across albums and playback contexts.

### Temporal Listening Analysis:

Extracts and aggregates:
• Hour-of-day listening distribution
• Day-of-week listening distribution

These metrics enable behavioral pattern analysis and time-series engagement profiling.

### Duration Normalization:

Converts raw millisecond playback values into human-readable minute-based metrics using SQL transformations.

### RESTful Interface:

Exposes structured analytics via JSON endpoints suitable for:
• Frontend dashboards
• Data visualization tools
• External consumption
• Future ML feature pipelines

## Engineering Highlights

Implements a relational data model from semi-structured JSON event logs.

Applies database-level aggregation rather than in-memory processing for performance scalability.

Uses composite uniqueness constraints to enforce event integrity.

Separates ingestion logic from analytics endpoints for modularity.

Demonstrates understanding of:
• Event-driven data pipelines
• Log normalization
• REST API architecture
• Time-based behavioral aggregation
• Backend system reproducibility

Designed with extensibility for future additions such as:
• Listening streak detection
• Session-level segmentation
• User engagement scoring
• Machine learning-based music preference modeling

## Summary

This project replicates a production-style data engineering and analytics workflow for event-level streaming data. It transforms raw semi-structured Spotify exports into a structured relational database and exposes meaningful behavioral analytics through a RESTful API.

The system demonstrates database schema design, idempotent ingestion logic, SQL-based aggregation, and clean API architecture. It reflects backend engineering rigor combined with analytical reasoning, aligning closely with standards in data engineering, analytics infrastructure, and applied machine learning pipelines.
