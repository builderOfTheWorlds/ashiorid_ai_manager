#!/usr/bin/env python3
"""
Ashiorid AI Manager - Streamlit Web Frontend

Interactive web interface for querying the AI Manager system and managing data preparation.
"""

import os
import json
import time
from datetime import datetime
from typing import Dict, List, Optional
from io import BytesIO

import httpx
import streamlit as st
import yaml
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd


# ============================================================================
# Configuration
# ============================================================================

def load_config() -> Dict:
    """Load configuration from yaml file."""
    config_path = os.path.join(os.path.dirname(__file__), "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            return yaml.safe_load(f)
    return {}


CONFIG = load_config()

# Get service URLs from environment or config
AI_MANAGER_URL = os.getenv(
    "AI_MANAGER_URL",
    CONFIG.get("ai_manager", {}).get("base_url", "http://localhost:8005")
)

DATA_PREP_URL = os.getenv(
    "DATA_PREP_URL",
    CONFIG.get("data_prep", {}).get("base_url", "http://localhost:8006")
)


# ============================================================================
# Configuration Presets for Data Prep
# ============================================================================

DATA_PREP_PRESETS = {
    "Fast Processing": {
        "description": "Quick processing without LLM enhancement",
        "config": {
            "processing": {
                "llm_enhancement": {"enabled": False},
                "chunking": {
                    "strategy": "token_count",
                    "chunk_size_tokens": 1024,
                    "chunk_overlap_tokens": 100
                }
            }
        }
    },
    "Balanced": {
        "description": "Moderate settings with selective LLM enhancement",
        "config": {
            "processing": {
                "llm_enhancement": {
                    "enabled": True,
                    "features": {
                        "generate_summaries": True,
                        "extract_characters": True,
                        "tag_themes": False,
                        "detect_narrative_arc": False,
                        "identify_pov": False
                    }
                },
                "chunking": {
                    "strategy": "token_count",
                    "chunk_size_tokens": 2048,
                    "chunk_overlap_tokens": 200
                }
            }
        }
    },
    "High Quality": {
        "description": "Full LLM enhancement for maximum metadata",
        "config": {
            "processing": {
                "llm_enhancement": {
                    "enabled": True,
                    "features": {
                        "generate_summaries": True,
                        "extract_characters": True,
                        "tag_themes": True,
                        "detect_narrative_arc": True,
                        "identify_pov": True
                    }
                },
                "chunking": {
                    "strategy": "chapter",
                    "chunk_size_tokens": 2048,
                    "chunk_overlap_tokens": 200
                }
            }
        }
    },
    "Chapter-based": {
        "description": "Chunk by chapter boundaries",
        "config": {
            "processing": {
                "llm_enhancement": {"enabled": True},
                "chunking": {
                    "strategy": "chapter"
                }
            }
        }
    }
}


# ============================================================================
# API Clients
# ============================================================================

class AIManagerClient:
    """Client for AI Manager API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0)

    def query(
        self,
        query: str,
        locale: str = "en-US",
        include_simulation: bool = True,
        include_lore: bool = True
    ) -> Dict:
        """Process a general query."""
        response = self.client.post(
            f"{self.base_url}/api/v1/query",
            json={
                "query": query,
                "locale": locale,
                "include_simulation": include_simulation,
                "include_lore": include_lore,
            }
        )
        response.raise_for_status()
        return response.json()

    def query_character(
        self,
        character_name: str,
        message: str,
        locale: str = "en-US",
        include_simulation: bool = True
    ) -> Dict:
        """Query a specific character."""
        response = self.client.post(
            f"{self.base_url}/api/v1/character/query",
            json={
                "character_name": character_name,
                "message": message,
                "locale": locale,
                "include_simulation": include_simulation,
            }
        )
        response.raise_for_status()
        return response.json()

    def get_status(self) -> Dict:
        """Get system status."""
        response = self.client.get(f"{self.base_url}/api/v1/status")
        response.raise_for_status()
        return response.json()

    def get_recent_events(self, limit: int = 20) -> Dict:
        """Get recent world events."""
        response = self.client.get(
            f"{self.base_url}/api/v1/events/recent",
            params={"limit": limit}
        )
        response.raise_for_status()
        return response.json()

    def trigger_event(
        self,
        event_type: str,
        description: Optional[str] = None,
        agent_ids: Optional[List[str]] = None,
        location: Optional[tuple] = None
    ) -> Dict:
        """Trigger a world event."""
        payload = {"event_type": event_type}
        if description:
            payload["description"] = description
        if agent_ids:
            payload["agent_ids"] = agent_ids
        if location:
            payload["location"] = list(location)

        response = self.client.post(
            f"{self.base_url}/api/v1/events/trigger",
            json=payload
        )
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the client."""
        self.client.close()


class DataPrepClient:
    """Client for Data Preparation Service API."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=60.0)

    def process_batch(
        self,
        source_dir: Optional[str] = None,
        output_dir: Optional[str] = None,
        config_override: Optional[Dict] = None
    ) -> Dict:
        """Start batch processing."""
        response = self.client.post(
            f"{self.base_url}/process/batch",
            json={
                "source_dir": source_dir,
                "output_dir": output_dir,
                "config_override": config_override
            }
        )
        response.raise_for_status()
        return response.json()

    def upload_file(self, file_content: bytes, filename: str) -> Dict:
        """Upload and process a single file."""
        files = {"file": (filename, file_content, "text/plain")}
        response = self.client.post(
            f"{self.base_url}/process/file",
            files=files
        )
        response.raise_for_status()
        return response.json()

    def get_job_status(self, job_id: str) -> Dict:
        """Get job status."""
        response = self.client.get(f"{self.base_url}/jobs/{job_id}")
        response.raise_for_status()
        return response.json()

    def list_files(self) -> Dict:
        """List all processed files."""
        response = self.client.get(f"{self.base_url}/files")
        response.raise_for_status()
        return response.json()

    def get_file_metadata(self, filename: str) -> Dict:
        """Get file metadata."""
        response = self.client.get(f"{self.base_url}/files/{filename}/metadata")
        response.raise_for_status()
        return response.json()

    def download_file(self, filename: str) -> bytes:
        """Download processed file."""
        response = self.client.get(f"{self.base_url}/files/{filename}")
        response.raise_for_status()
        return response.content

    def delete_file(self, filename: str) -> Dict:
        """Delete processed file."""
        response = self.client.delete(f"{self.base_url}/files/{filename}")
        response.raise_for_status()
        return response.json()

    def reprocess_file(self, filename: str, config_override: Optional[Dict] = None) -> Dict:
        """Reprocess a file with new settings."""
        response = self.client.post(
            f"{self.base_url}/reprocess/{filename}",
            json={"config_override": config_override}
        )
        response.raise_for_status()
        return response.json()

    def get_stats(self) -> Dict:
        """Get service statistics."""
        response = self.client.get(f"{self.base_url}/stats")
        response.raise_for_status()
        return response.json()

    def get_health(self) -> Dict:
        """Get health status."""
        response = self.client.get(f"{self.base_url}/health/detailed")
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the client."""
        self.client.close()


# ============================================================================
# Session State Initialization
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "ai_client" not in st.session_state:
        st.session_state.ai_client = AIManagerClient(AI_MANAGER_URL)
    if "data_prep_client" not in st.session_state:
        st.session_state.data_prep_client = DataPrepClient(DATA_PREP_URL)
    if "active_jobs" not in st.session_state:
        st.session_state.active_jobs = []
    if "selected_preset" not in st.session_state:
        st.session_state.selected_preset = "Balanced"


# ============================================================================
# Sidebar
# ============================================================================

def render_sidebar():
    """Render sidebar with settings."""
    with st.sidebar:
        st.title("Settings")

        # Locale selector
        locales = CONFIG.get("locales", ["en-US"])
        locale = st.selectbox("Language/Locale", locales, index=0)

        # Feature toggles
        st.subheader("Query Options")
        include_simulation = st.checkbox("Include Simulation Data", value=True)
        include_lore = st.checkbox("Include Lore Context", value=True)

        # Connection status
        st.divider()
        st.subheader("Services")
        st.text(f"AI Manager: {AI_MANAGER_URL}")
        st.text(f"Data Prep: {DATA_PREP_URL}")

        return locale, include_simulation, include_lore


# ============================================================================
# Data Prep Tab Components
# ============================================================================

def render_data_prep_upload():
    """Render file upload interface."""
    st.subheader("📤 Upload Files")

    uploaded_files = st.file_uploader(
        "Choose text files to process",
        type=["txt"],
        accept_multiple_files=True,
        help="Upload one or more .txt files (books or scripts)"
    )

    if uploaded_files:
        st.write(f"Selected {len(uploaded_files)} file(s)")

        # Configuration preset selector
        preset = st.selectbox(
            "Processing Preset",
            list(DATA_PREP_PRESETS.keys()),
            help="Choose processing quality vs speed"
        )

        st.info(DATA_PREP_PRESETS[preset]["description"])

        if st.button("Process Uploaded Files", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()

            jobs_created = []

            for i, uploaded_file in enumerate(uploaded_files):
                try:
                    status_text.text(f"Uploading {uploaded_file.name}...")

                    # Read file content
                    file_content = uploaded_file.read()

                    # Upload and process
                    result = st.session_state.data_prep_client.upload_file(
                        file_content,
                        uploaded_file.name
                    )

                    jobs_created.append({
                        "job_id": result["job_id"],
                        "filename": uploaded_file.name
                    })

                    progress_bar.progress((i + 1) / len(uploaded_files))

                except Exception as e:
                    st.error(f"Error processing {uploaded_file.name}: {str(e)}")

            if jobs_created:
                st.success(f"Started processing {len(jobs_created)} file(s)!")
                st.session_state.active_jobs.extend(jobs_created)
                status_text.text("✓ All files uploaded")


def render_data_prep_batch():
    """Render batch processing interface."""
    st.subheader("📁 Batch Processing")

    col1, col2 = st.columns(2)

    with col1:
        source_dir = st.text_input(
            "Source Directory",
            value="/PycharmProjects/ashiorid/sourceWorks",
            help="Directory containing .txt files to process"
        )

    with col2:
        output_dir = st.text_input(
            "Output Directory",
            value="./processed_output",
            help="Where to save processed JSONL files"
        )

    # Configuration preset
    preset = st.selectbox(
        "Processing Preset",
        list(DATA_PREP_PRESETS.keys()),
        key="batch_preset"
    )

    st.info(DATA_PREP_PRESETS[preset]["description"])

    if st.button("Start Batch Processing", type="primary", use_container_width=True):
        try:
            with st.spinner("Starting batch job..."):
                result = st.session_state.data_prep_client.process_batch(
                    source_dir=source_dir,
                    output_dir=output_dir,
                    config_override=DATA_PREP_PRESETS[preset]["config"]
                )

                st.success(f"Batch job started! Job ID: {result['job_id']}")
                st.info(f"Found {result.get('files_found', 0)} files to process")

                st.session_state.active_jobs.append({
                    "job_id": result["job_id"],
                    "type": "batch",
                    "source_dir": source_dir
                })

        except Exception as e:
            st.error(f"Error starting batch job: {str(e)}")


def render_data_prep_jobs():
    """Render job monitoring interface."""
    st.subheader("📊 Job Monitoring")

    if not st.session_state.active_jobs:
        st.info("No active jobs. Upload files or start batch processing to see jobs here.")
        return

    # Refresh button
    if st.button("🔄 Refresh Status", use_container_width=True):
        st.rerun()

    # Display each job
    for job_info in st.session_state.active_jobs:
        job_id = job_info["job_id"]

        try:
            status = st.session_state.data_prep_client.get_job_status(job_id)

            with st.container():
                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**Job:** {job_id[:8]}... ({job_info.get('filename', 'batch')})")

                with col2:
                    status_emoji = {
                        "pending": "⏳",
                        "processing": "⚙️",
                        "completed": "✅",
                        "failed": "❌"
                    }
                    st.write(f"{status_emoji.get(status['status'], '❓')} {status['status']}")

                with col3:
                    progress = status.get("progress_percent", 0)
                    st.write(f"{progress:.1f}%")

                # Progress bar
                st.progress(progress / 100.0)

                # Details
                if status["status"] == "processing":
                    st.text(f"Files: {status['files_processed']}/{status['files_total']} | Chunks: {status['chunks_created']}")
                elif status["status"] == "completed":
                    st.success(f"✓ Completed: {status['chunks_created']} chunks created from {status['files_processed']} files")
                elif status["status"] == "failed":
                    st.error(f"Error: {status.get('error', 'Unknown error')}")

                st.divider()

        except Exception as e:
            st.error(f"Error fetching status for job {job_id}: {str(e)}")


def render_data_prep_files():
    """Render file browser interface."""
    st.subheader("📚 Processed Files")

    try:
        files_data = st.session_state.data_prep_client.list_files()
        files = files_data.get("files", [])

        if not files:
            st.info("No processed files yet. Upload and process files to see them here.")
            return

        st.write(f"Total files: {len(files)}")

        # Create DataFrame for display
        df = pd.DataFrame(files)

        # Display as table
        for idx, file_info in enumerate(files):
            with st.expander(f"📄 {file_info['filename']} ({file_info['chunks']} chunks, {file_info['size_mb']} MB)"):
                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("Chunks", file_info['chunks'])

                with col2:
                    st.metric("Size (MB)", file_info['size_mb'])

                with col3:
                    st.metric("Quality Issues", len(file_info.get('quality_issues', [])))

                # Actions
                action_col1, action_col2, action_col3 = st.columns(3)

                with action_col1:
                    if st.button("📥 Download", key=f"download_{idx}"):
                        try:
                            content = st.session_state.data_prep_client.download_file(file_info['filename'])
                            st.download_button(
                                label="Save File",
                                data=content,
                                file_name=file_info['filename'],
                                mime="application/jsonlines"
                            )
                        except Exception as e:
                            st.error(f"Download error: {str(e)}")

                with action_col2:
                    if st.button("🔍 View Metadata", key=f"meta_{idx}"):
                        try:
                            metadata = st.session_state.data_prep_client.get_file_metadata(file_info['filename'])
                            st.json(metadata)
                        except Exception as e:
                            st.error(f"Metadata error: {str(e)}")

                with action_col3:
                    if st.button("🗑️ Delete", key=f"delete_{idx}"):
                        try:
                            st.session_state.data_prep_client.delete_file(file_info['filename'])
                            st.success(f"Deleted {file_info['filename']}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Delete error: {str(e)}")

                # Show quality issues if any
                if file_info.get('quality_issues'):
                    st.warning("Quality Issues:")
                    for issue in file_info['quality_issues']:
                        st.text(f"  • {issue}")

    except Exception as e:
        st.error(f"Error loading files: {str(e)}")


def render_data_prep_stats():
    """Render statistics dashboard."""
    st.subheader("📈 Statistics Dashboard")

    try:
        stats = st.session_state.data_prep_client.get_stats()

        # Top metrics
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Total Files", stats.get("total_files", 0))

        with col2:
            st.metric("Total Chunks", stats.get("total_chunks", 0))

        with col3:
            st.metric("Total Size (GB)", f"{stats.get('total_size_gb', 0):.2f}")

        # Try to get files for visualization
        try:
            files_data = st.session_state.data_prep_client.list_files()
            files = files_data.get("files", [])

            if files and len(files) > 0:
                st.divider()
                st.subheader("📊 Visualizations")

                df = pd.DataFrame(files)

                # Chart 1: Chunks per file
                fig1 = px.bar(
                    df,
                    x='filename',
                    y='chunks',
                    title='Chunks per File',
                    labels={'filename': 'File', 'chunks': 'Number of Chunks'}
                )
                fig1.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig1, use_container_width=True)

                # Chart 2: File sizes
                fig2 = px.pie(
                    df,
                    values='size_mb',
                    names='filename',
                    title='Storage Distribution by File'
                )
                st.plotly_chart(fig2, use_container_width=True)

        except Exception as e:
            st.warning(f"Could not generate visualizations: {str(e)}")

    except Exception as e:
        st.error(f"Error loading statistics: {str(e)}")


def render_data_prep_health():
    """Render service health status."""
    st.subheader("🏥 Service Health")

    try:
        health = st.session_state.data_prep_client.get_health()

        # Overall status
        status = health.get("status", "unknown")
        if status == "healthy":
            st.success(f"✓ Service Status: {status.upper()}")
        elif status == "degraded":
            st.warning(f"⚠ Service Status: {status.upper()}")
        else:
            st.error(f"✗ Service Status: {status.upper()}")

        # Component health
        st.divider()
        st.subheader("Components")

        components = health.get("components", {})
        cols = st.columns(len(components) if components else 1)

        for i, (component, comp_status) in enumerate(components.items()):
            with cols[i]:
                if comp_status == "healthy":
                    st.success(f"✓ {component}")
                else:
                    st.error(f"✗ {component}")

        # Uptime
        uptime_seconds = health.get("uptime_seconds", 0)
        uptime_hours = uptime_seconds / 3600
        st.metric("Uptime", f"{uptime_hours:.1f} hours")

    except Exception as e:
        st.error(f"Error checking health: {str(e)}")


def render_data_prep_tab():
    """Render the main Data Prep tab with sub-tabs."""
    st.header("📊 Data Preparation Service")

    # Sub-tabs
    subtab1, subtab2, subtab3, subtab4, subtab5, subtab6 = st.tabs([
        "📤 Upload",
        "📁 Batch",
        "⚙️ Jobs",
        "📚 Files",
        "📈 Stats",
        "🏥 Health"
    ])

    with subtab1:
        render_data_prep_upload()

    with subtab2:
        render_data_prep_batch()

    with subtab3:
        render_data_prep_jobs()

    with subtab4:
        render_data_prep_files()

    with subtab5:
        render_data_prep_stats()

    with subtab6:
        render_data_prep_health()


# ============================================================================
# Existing Tab Functions (from original app.py)
# ============================================================================

def render_world_query_tab(locale: str, include_simulation: bool, include_lore: bool):
    """Render the world query chat interface."""
    st.header("Ask About the World")

    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            # Show metadata if available
            if "metadata" in message:
                with st.expander("Details"):
                    metadata = message["metadata"]
                    if "sources" in metadata and metadata["sources"]:
                        st.subheader("Lore Sources")
                        for i, source in enumerate(metadata["sources"], 1):
                            st.text(f"{i}. {source[:200]}...")

                    if "simulation_snapshot" in metadata:
                        st.subheader("Simulation State")
                        sim = metadata["simulation_snapshot"]
                        col1, col2, col3 = st.columns(3)
                        col1.metric("Tick", sim.get("tick", "N/A"))
                        col2.metric("Active Agents", sim.get("active_agents", "N/A"))
                        col3.metric("Total Agents", sim.get("total_agents", "N/A"))

    # Chat input
    st.divider()
    col1, col2 = st.columns([4, 1])

    with col1:
        prompt = st.text_area(
            "Your Question",
            placeholder="Ask about the world...",
            height=100,
            key="world_query_input"
        )

    with col2:
        st.write("")
        st.write("")
        send_button = st.button("Send", type="primary", use_container_width=True)

    if send_button and prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.spinner("Thinking..."):
            try:
                response = st.session_state.ai_client.query(
                    query=prompt,
                    locale=locale,
                    include_simulation=include_simulation,
                    include_lore=include_lore
                )

                answer = response.get("response", "No response received")

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metadata": {
                        "sources": response.get("sources", []),
                        "simulation_snapshot": response.get("simulation_snapshot"),
                        "metadata": response.get("metadata", {})
                    }
                })

                st.rerun()

            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.error(error_msg)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": error_msg
                })
                st.rerun()


def render_character_query_tab(locale: str, include_simulation: bool):
    """Render the character query interface."""
    st.header("Talk to a Character")

    col1, col2 = st.columns([2, 1])

    with col1:
        character_name = st.text_input(
            "Character Name",
            placeholder="e.g., gandalf, frodo, aragorn"
        )

    with col2:
        st.write("")
        st.write("")
        query_button = st.button("Send Message", type="primary", use_container_width=True)

    message = st.text_area(
        "Your Message",
        placeholder="What would you like to ask this character?",
        height=100
    )

    if query_button and character_name and message:
        with st.spinner(f"Asking {character_name}..."):
            try:
                response = st.session_state.ai_client.query_character(
                    character_name=character_name,
                    message=message,
                    locale=locale,
                    include_simulation=include_simulation
                )

                st.success(f"Response from {character_name}:")
                st.markdown(response.get("response", "No response received"))

                with st.expander("Details"):
                    if response.get("simulation_snapshot"):
                        st.subheader("Simulation Context")
                        st.json(response["simulation_snapshot"])

            except Exception as e:
                st.error(f"Error: {str(e)}")


def render_events_tab():
    """Render the world events interface."""
    st.header("World Events")

    event_tab1, event_tab2 = st.tabs(["Recent Events", "Trigger Event"])

    with event_tab1:
        st.subheader("Recent World Events")

        limit = st.slider("Number of events to show", 5, 50, 20)

        if st.button("Refresh Events", use_container_width=True):
            try:
                events_data = st.session_state.ai_client.get_recent_events(limit=limit)
                events = events_data.get("events", [])

                if events:
                    for event in events:
                        with st.container():
                            st.markdown(f"**{event.get('type', 'Unknown')}**")
                            st.text(event.get("description", "No description"))
                            st.caption(f"Time: {event.get('timestamp', 'N/A')}")
                            st.divider()
                else:
                    st.info("No recent events found")

            except Exception as e:
                st.error(f"Error fetching events: {str(e)}")

    with event_tab2:
        st.subheader("Trigger a New Event")

        event_type = st.selectbox(
            "Event Type",
            [
                "natural_disaster",
                "resource_discovery",
                "faction_conflict",
                "mysterious_phenomenon",
                "technological_breakthrough"
            ]
        )

        description = st.text_area(
            "Event Description (optional)",
            placeholder="Leave empty to auto-generate with LLM",
            height=100
        )

        col1, col2 = st.columns(2)

        with col1:
            agent_ids = st.text_input(
                "Agent IDs (comma-separated, optional)",
                placeholder="agent-1, agent-2"
            )

        with col2:
            location_str = st.text_input(
                "Location (x,y optional)",
                placeholder="42, 73"
            )

        if st.button("Trigger Event", type="primary", use_container_width=True):
            try:
                agent_list = [a.strip() for a in agent_ids.split(",")] if agent_ids else None
                location = None
                if location_str:
                    parts = location_str.split(",")
                    if len(parts) == 2:
                        location = (int(parts[0].strip()), int(parts[1].strip()))

                result = st.session_state.ai_client.trigger_event(
                    event_type=event_type,
                    description=description if description else None,
                    agent_ids=agent_list,
                    location=location
                )

                st.success("Event triggered successfully!")
                st.json(result)

            except Exception as e:
                st.error(f"Error triggering event: {str(e)}")


def render_status_tab():
    """Render the system status interface."""
    st.header("System Status")

    if st.button("Refresh Status", use_container_width=True):
        try:
            status = st.session_state.ai_client.get_status()

            overall_status = status.get("status", "unknown")
            if overall_status == "healthy":
                st.success(f"System Status: {overall_status.upper()}")
            else:
                st.warning(f"System Status: {overall_status.upper()}")

            st.subheader("Services")
            services = status.get("services", {})

            cols = st.columns(len(services))
            for i, (service_name, service_data) in enumerate(services.items()):
                with cols[i]:
                    is_healthy = service_data.get("healthy", False)
                    st.metric(
                        label=service_name,
                        value="Healthy" if is_healthy else "Unhealthy",
                        delta=f"{service_data.get('latency_ms', 0):.0f}ms"
                    )

            st.subheader("Simulation State")
            sim = status.get("simulation", {})
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Tick", sim.get("tick", "N/A"))
            col2.metric("Active Agents", sim.get("active_agents", "N/A"))
            col3.metric("Total Agents", sim.get("total_agents", "N/A"))

            st.subheader("Recent World Events")
            events = status.get("world_events", [])
            if events:
                for event in events[:5]:
                    st.text(f"[{event.get('type')}] {event.get('description', 'N/A')}")
            else:
                st.info("No recent world events")

        except Exception as e:
            st.error(f"Error fetching status: {str(e)}")


# ============================================================================
# Main Application
# ============================================================================

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Ashiorid AI Manager",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    init_session_state()

    st.title("🌍 Ashiorid AI Manager")
    st.caption("Interactive World-Building AI System with Data Preparation")

    locale, include_simulation, include_lore = render_sidebar()

    # Main tabs - added Data Prep tab
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🗨️ World Query",
        "👤 Character Query",
        "⚡ Events",
        "📊 System Status",
        "📊 Data Prep"
    ])

    with tab1:
        render_world_query_tab(locale, include_simulation, include_lore)

    with tab2:
        render_character_query_tab(locale, include_simulation)

    with tab3:
        render_events_tab()

    with tab4:
        render_status_tab()

    with tab5:
        render_data_prep_tab()


if __name__ == "__main__":
    main()
