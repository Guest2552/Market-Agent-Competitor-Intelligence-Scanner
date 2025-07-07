import streamlit as st
import google.generativeai as genai
import json
import io
import pandas as pd
from fpdf import FPDF

# --- CONFIGURE GEMINI ---
genai.configure(api_key="AIzaSyAL0yuyhQZBuCxEsTL5lg8VXr567w4kKwg")  # Replace with your Gemini API key

# --- PAGE SETTINGS ---
st.set_page_config(page_title="AI Competitor Scanner", layout="centered")
st.title("🤖 Market Agent – Competitor Intelligence Scanner")

# --- SESSION STATE INIT ---
if "result" not in st.session_state:
    st.session_state.result = None
if "swot_results" not in st.session_state:
    st.session_state.swot_results = {}

# --- READ INDUSTRY AND LOCATION OPTIONS ---
@st.cache_data
def load_options():
    with open("Industries.txt", "r", encoding="utf-8") as f:
        industries = sorted(list(set([line.strip() for line in f if line.strip()])))
    with open("Headquarters_Location.txt", "r", encoding="utf-8") as f:
        locations = sorted(list(set([line.strip() for line in f if line.strip()])))
    return industries, locations

industry_options, location_options = load_options()

# --- INPUT FORM ---
with st.form("input_form"):
    product = st.text_input("Product / Idea*", value=st.session_state.get("product", ""), placeholder="e.g., AI-powered learning assistant")
    industry = st.selectbox("Industry*", industry_options, index=industry_options.index(st.session_state.get("industry", industry_options[0])) if "industry" in st.session_state else 0)
    keywords = st.text_input("Keywords*", value=st.session_state.get("keywords", ""), placeholder="e.g., EdTech, Learning Tools")
    region = st.selectbox("Region*", location_options, index=location_options.index(st.session_state.get("region", location_options[0])) if "region" in st.session_state else 0)

    company_size = st.selectbox("Company Size", ["Any", "Startup (1–50 employees)", "Mid-size (51–500 employees)", "Enterprise (500+ employees)"])
    funding_stage = st.selectbox("Funding Stage", ["Any", "Seed Stage", "Growth Stage (Series A, B, C)", "Late Stage (Series D+)"])
    business_model = st.selectbox("Business Model", ["Any", "B2B", "B2C", "SaaS", "Marketplace"])
    timeframe = st.selectbox("Analysis Timeframe", ["Any", "Last 6 months", "Last 12 months", "Last 2 years"])
    focus = st.text_input("Focus Areas (optional)", placeholder="e.g., Pricing, Product Features")

    submitted = st.form_submit_button("🔍 Generate Competitor Report")

# --- PROMPT CREATION ---
def build_prompt(data):
    return f"""
You are a market research analyst. Your job is to provide a **list of real, existing companies**, both regional (from {data['region']}) and global, that are **actively operating in the '{data['industry']}' industry** and offer products/services related to '{data['product']}' and the keywords: {data['keywords']}.

**Only include real, verifiable companies. Do not make up company names.** If you are unsure about a company, exclude it.

If no such company is found in that industry and region, return:
{{"competitors": []}}

Return a list of 8-10 companies in **tabular JSON** format like:
[{{"companyName", "location", "foundedYear", "funding", "products", "targetMarket", "usp"}}]

The companies must be:
- Active and real (no hypothetical startups)
- From both regional ({data['region']}) and global markets
- Competitors in the same product/service segment

Be concise and factual.
"""

# --- OUTPUT SCHEMA ---
def get_schema():
    return {
        "type": "object",
        "properties": {
            "competitors": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "companyName": {"type": "string"},
                        "products": {"type": "string"},
                        "targetMarket": {"type": "string"},
                        "foundedYear": {"type": "string"},
                        "funding": {"type": "string"},
                        "location": {"type": "string"},
                        "usp": {"type": "string"}
                    },
                    "required": ["companyName", "products", "targetMarket", "foundedYear", "funding", "location", "usp"]
                }
            }
        },
        "required": ["competitors"]
    }

# --- GENERATE REPORT ---
def generate_report(prompt):
    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": get_schema()
            }
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"AI generation failed: {str(e)}"}

# --- HANDLE FORM SUBMISSION ---
if submitted:
    if not product or not industry or not keywords or not region:
        st.warning("Please fill in all required fields.")
    else:
        with st.spinner("Generating competitor report..."):
            user_data = {
                "product": product,
                "industry": industry,
                "keywords": keywords,
                "region": region,
                "companySize": company_size,
                "fundingStage": funding_stage,
                "businessModel": business_model,
                "timeframe": timeframe,
                "focusAreas": focus
            }

            prompt = build_prompt(user_data)
            result = generate_report(prompt)
            if "competitors" in result:
                if not result["competitors"]:
                    st.info(f"No real companies found in the '{industry}' industry located in '{region}' for the product '{product}'.")
                else:
                    st.session_state.result = result
                    st.session_state.product = product
                    st.session_state.industry = industry
                    st.session_state.keywords = keywords
                    st.session_state.region = region
            else:
                st.error(result.get("error", "No results returned."))

# --- DISPLAY RESULTS AS TABLE ---
if st.session_state.result:
    competitors = st.session_state.result["competitors"]
    if competitors:
        st.subheader("📊 Verified Competitor Landscape (Regional + Global)")
        df = pd.DataFrame(competitors)
        st.dataframe(df, use_container_width=True)

        # --- PDF DOWNLOAD ---
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        pdf.add_page()
        pdf.set_font("Arial", "B", 14)
        pdf.cell(0, 10, "Competitor Intelligence Report", ln=True)
        pdf.set_font("Arial", size=12)

        for idx, c in enumerate(competitors):
            pdf.ln(10)
            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, f"{idx + 1}. {c['companyName']}", ln=True)
            pdf.set_font("Arial", size=11)
            pdf.multi_cell(0, 8, f"Location: {c['location']}\nFounded: {c['foundedYear']}\nFunding: {c['funding']}\nTarget Market: {c['targetMarket']}\nProducts: {c['products']}\nUSP: {c['usp']}")

        pdf_bytes = pdf.output(dest='S').encode('latin-1', 'ignore')
        buffer = io.BytesIO(pdf_bytes)
        st.download_button("📅 Download Report as PDF", buffer, file_name="Competitor_Report.pdf", mime="application/pdf")
