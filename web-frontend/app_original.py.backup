#!/usr/bin/env python3
"""
Ashiorid AI Manager - Streamlit Web Frontend

Interactive web interface for querying the AI Manager system.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional

import httpx
import streamlit as st
import yaml


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

# Get AI Manager URL from environment or config
AI_MANAGER_URL = os.getenv(
    "AI_MANAGER_URL",
    CONFIG.get("ai_manager", {}).get("base_url", "http://localhost:8005")
)


# ============================================================================
# API Client
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


# ============================================================================
# Streamlit UI
# ============================================================================

def init_session_state():
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "client" not in st.session_state:
        st.session_state.client = AIManagerClient(AI_MANAGER_URL)


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
        st.subheader("Connection")
        st.text(f"AI Manager: {AI_MANAGER_URL}")

        return locale, include_simulation, include_lore


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

    # Chat input (using text area and button instead of st.chat_input due to tab constraints)
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
        st.write("")  # Spacer
        st.write("")  # Spacer
        send_button = st.button("Send", type="primary", use_container_width=True)

    if send_button and prompt:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Get response from AI Manager
        with st.spinner("Thinking..."):
            try:
                response = st.session_state.client.query(
                    query=prompt,
                    locale=locale,
                    include_simulation=include_simulation,
                    include_lore=include_lore
                )

                answer = response.get("response", "No response received")

                # Store assistant message with metadata
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": answer,
                    "metadata": {
                        "sources": response.get("sources", []),
                        "simulation_snapshot": response.get("simulation_snapshot"),
                        "metadata": response.get("metadata", {})
                    }
                })

                # Rerun to display new messages
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
        st.write("")  # Spacer
        st.write("")  # Spacer
        query_button = st.button("Send Message", type="primary", use_container_width=True)

    message = st.text_area(
        "Your Message",
        placeholder="What would you like to ask this character?",
        height=100
    )

    if query_button and character_name and message:
        with st.spinner(f"Asking {character_name}..."):
            try:
                response = st.session_state.client.query_character(
                    character_name=character_name,
                    message=message,
                    locale=locale,
                    include_simulation=include_simulation
                )

                st.success(f"Response from {character_name}:")
                st.markdown(response.get("response", "No response received"))

                # Show metadata
                with st.expander("Details"):
                    if response.get("simulation_snapshot"):
                        st.subheader("Simulation Context")
                        st.json(response["simulation_snapshot"])

            except Exception as e:
                st.error(f"Error: {str(e)}")


def render_events_tab():
    """Render the world events interface."""
    st.header("World Events")

    # Tabs for recent events and trigger new event
    event_tab1, event_tab2 = st.tabs(["Recent Events", "Trigger Event"])

    with event_tab1:
        st.subheader("Recent World Events")

        limit = st.slider("Number of events to show", 5, 50, 20)

        if st.button("Refresh Events", use_container_width=True):
            try:
                events_data = st.session_state.client.get_recent_events(limit=limit)
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
                # Parse inputs
                agent_list = [a.strip() for a in agent_ids.split(",")] if agent_ids else None
                location = None
                if location_str:
                    parts = location_str.split(",")
                    if len(parts) == 2:
                        location = (int(parts[0].strip()), int(parts[1].strip()))

                result = st.session_state.client.trigger_event(
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
            status = st.session_state.client.get_status()

            # Overall status
            overall_status = status.get("status", "unknown")
            if overall_status == "healthy":
                st.success(f"System Status: {overall_status.upper()}")
            else:
                st.warning(f"System Status: {overall_status.upper()}")

            # Services health
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

            # Simulation state
            st.subheader("Simulation State")
            sim = status.get("simulation", {})
            col1, col2, col3 = st.columns(3)
            col1.metric("Current Tick", sim.get("tick", "N/A"))
            col2.metric("Active Agents", sim.get("active_agents", "N/A"))
            col3.metric("Total Agents", sim.get("total_agents", "N/A"))

            # Recent world events
            st.subheader("Recent World Events")
            events = status.get("world_events", [])
            if events:
                for event in events[:5]:  # Show last 5
                    st.text(f"[{event.get('type')}] {event.get('description', 'N/A')}")
            else:
                st.info("No recent world events")

        except Exception as e:
            st.error(f"Error fetching status: {str(e)}")


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Ashiorid AI Manager",
        page_icon="🌍",
        layout="wide",
        initial_sidebar_state="expanded"
    )

    # Initialize
    init_session_state()

    # Title
    st.title("🌍 Ashiorid AI Manager")
    st.caption("Interactive World-Building AI System")

    # Sidebar
    locale, include_simulation, include_lore = render_sidebar()

    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "🗨️ World Query",
        "👤 Character Query",
        "⚡ Events",
        "📊 System Status"
    ])

    with tab1:
        render_world_query_tab(locale, include_simulation, include_lore)

    with tab2:
        render_character_query_tab(locale, include_simulation)

    with tab3:
        render_events_tab()

    with tab4:
        render_status_tab()


if __name__ == "__main__":
    main()
