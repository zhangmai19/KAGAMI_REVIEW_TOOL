"""Streamlit web UI for AutoLitReview-Agent.

Run with: streamlit run ui/streamlit_app.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

import streamlit as st

from agents.literature_review_agent import LiteratureReviewAgent


def main():
    st.set_page_config(
        page_title="AutoLitReview-Agent",
        page_icon="📚",
        layout="wide",
    )

    st.title("📚 AutoLitReview-Agent")
    st.subheader("Citation-Grounded Academic Literature Review")

    st.markdown(
        "An automated literature review agent that generates "
        "evidence-grounded, abstract-based systematic reviews. "
        "Every claim is backed by citation IDs (e.g., #1, #2)."
    )

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        model = st.selectbox(
            "LLM Model",
            ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
            index=0,
        )

        max_tokens = st.slider(
            "Max tokens per chunk",
            min_value=4000,
            max_value=20000,
            value=12000,
            step=1000,
        )

        max_papers_per_chunk = st.slider(
            "Max papers per chunk",
            min_value=10,
            max_value=50,
            value=25,
        )

        dedup_threshold = st.slider(
            "Deduplication threshold",
            min_value=0.80,
            max_value=1.00,
            value=0.95,
            step=0.01,
        )

        st.divider()

        st.header("🔑 API Keys")
        st.text_input("OpenAI API Key", type="password", key="openai_key")
        st.text_input("OpenAlex Email", key="openalex_email")

        if st.button("Save Keys"):
            if st.session_state.openai_key:
                os.environ["OPENAI_API_KEY"] = st.session_state.openai_key
            if st.session_state.openalex_email:
                os.environ["OPENALEX_EMAIL"] = st.session_state.openalex_email
            st.success("Keys saved for this session!")

    # Main content tabs
    tab1, tab2 = st.tabs(["📁 Upload & Review", "🔍 Search & Review"])

    # Tab 1: Upload file
    with tab1:
        st.header("Upload Literature File")

        topic = st.text_input(
            "Research Topic",
            placeholder="e.g., AI agents for academic literature review",
            key="upload_topic",
        )

        uploaded_file = st.file_uploader(
            "Upload RIS / BibTeX / CSV file",
            type=["ris", "bib", "csv"],
            key="file_upload",
        )

        if st.button("Run Review from File", type="primary", disabled=not uploaded_file):
            if not topic:
                st.error("Please enter a research topic.")
            elif not os.getenv("OPENAI_API_KEY"):
                st.error("Please set your OpenAI API key in the sidebar.")
            else:
                _run_review_from_file(topic, uploaded_file, model, max_tokens, max_papers_per_chunk, dedup_threshold)

    # Tab 2: Search databases
    with tab2:
        st.header("Search Academic Databases")

        search_topic = st.text_input(
            "Research Topic",
            placeholder="e.g., AI agents for academic literature review",
            key="search_topic",
        )

        keywords_input = st.text_area(
            "Keywords (one per line)",
            placeholder="large language model\nliterature review\nresearch automation",
            key="search_keywords",
        )

        col1, col2 = st.columns(2)
        with col1:
            databases = st.multiselect(
                "Databases",
                ["openalex", "semantic_scholar", "crossref"],
                default=["openalex", "semantic_scholar"],
            )
            max_papers = st.number_input(
                "Max papers",
                min_value=10,
                max_value=500,
                value=150,
            )

        with col2:
            from_year = st.number_input(
                "From year",
                min_value=1900,
                max_value=2030,
                value=2018,
            )
            to_year = st.number_input(
                "To year",
                min_value=1900,
                max_value=2030,
                value=2026,
            )

        if st.button("Run Review from Search", type="primary"):
            if not search_topic:
                st.error("Please enter a research topic.")
            elif not os.getenv("OPENAI_API_KEY"):
                st.error("Please set your OpenAI API key in the sidebar.")
            else:
                keywords = [k.strip() for k in keywords_input.split("\n") if k.strip()]
                if not keywords:
                    keywords = [search_topic]

                _run_review_from_search(
                    search_topic, keywords, databases, max_papers,
                    from_year, to_year, model, max_tokens,
                    max_papers_per_chunk, dedup_threshold,
                )


def _run_review_from_file(topic, uploaded_file, model, max_tokens, max_papers_per_chunk, dedup_threshold):
    """Execute a file-based review and display results."""
    with st.spinner("Running literature review..."):
        # Save uploaded file to temp location
        suffix = Path(uploaded_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(uploaded_file.getvalue())
            tmp_path = tmp.name

        try:
            with tempfile.TemporaryDirectory() as output_dir:
                agent = LiteratureReviewAgent(
                    model=model,
                    output_dir=output_dir,
                    max_tokens_per_chunk=max_tokens,
                    max_papers_per_chunk=max_papers_per_chunk,
                    dedup_threshold=dedup_threshold,
                )

                result = agent.review_from_file(topic=topic, file_path=tmp_path)
                _display_result(result, output_dir)
        finally:
            Path(tmp_path).unlink(missing_ok=True)


def _run_review_from_search(topic, keywords, databases, max_papers, from_year, to_year, model, max_tokens, max_papers_per_chunk, dedup_threshold):
    """Execute a search-based review and display results."""
    with st.spinner("Running literature review..."):
        with tempfile.TemporaryDirectory() as output_dir:
            agent = LiteratureReviewAgent(
                model=model,
                output_dir=output_dir,
                max_tokens_per_chunk=max_tokens,
                max_papers_per_chunk=max_papers_per_chunk,
                dedup_threshold=dedup_threshold,
            )

            result = agent.review_from_search(
                topic=topic,
                keywords=keywords,
                databases=databases,
                max_papers=max_papers,
                from_year=from_year,
                to_year=to_year,
            )
            _display_result(result, output_dir)


def _display_result(result: dict, output_dir: str):
    """Display review results in the Streamlit UI."""
    st.success("Literature review complete!")

    # Corpus summary
    corpus = result.get("corpus_summary", {})
    col1, col2, col3 = st.columns(3)
    col1.metric("Papers Analyzed", corpus.get("with_abstract", 0))
    col2.metric("Duplicates Removed", corpus.get("duplicates_removed", 0))
    col3.metric("Coverage", f"{result.get('coverage', {}).get('coverage_ratio', 0):.1%}")

    # Download buttons
    output_files = result.get("output_files", {})
    st.subheader("📥 Download Reports")

    cols = st.columns(len(output_files)) if output_files else [st]
    for i, (fmt, path_str) in enumerate(output_files.items()):
        path = Path(path_str)
        if path.exists():
            with cols[i]:
                with open(path, "rb") as f:
                    st.download_button(
                        label=f"Download {fmt.upper()}",
                        data=f.read(),
                        file_name=path.name,
                        mime=_get_mime(fmt),
                    )

    # Display markdown report
    md_path = output_files.get("markdown")
    if md_path and Path(md_path).exists():
        st.subheader("📋 Review Report")
        with open(md_path, "r", encoding="utf-8") as f:
            st.markdown(f.read(), unsafe_allow_html=True)


def _get_mime(fmt: str) -> str:
    """Get MIME type for download."""
    mime_map = {
        "markdown": "text/markdown",
        "json": "application/json",
        "ris": "application/x-research-info-systems",
    }
    return mime_map.get(fmt, "application/octet-stream")


if __name__ == "__main__":
    main()
