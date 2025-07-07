import streamlit as st
import google.generativeai as genai
import json
import io
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
    with open("inputs/Industries.txt", "r", encoding="utf-8") as f:
        industries = sorted(list(set([line.strip() for line in f if line.strip()])))
    with open("inputs/Headquarters_Location.txt", "r", encoding="utf-8") as f:
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
    return f"""Analyze the competitive landscape for the product/idea '{data['product']}' in the context of the industry '{data['industry']}' and region '{data['region']}', using keywords '{data['keywords']}'.
Company Size: {data['companySize']}
Funding Stage: {data['fundingStage']}
Business Model: {data['businessModel']}
Timeframe: {data['timeframe']}
Focus: {data['focusAreas']}
Return a JSON object named 'competitors' with this format:
[{{companyName, logoPlaceholder, products, targetMarket, foundedYear, funding, location, usp}}]"""

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
                        "logoPlaceholder": {"type": "string"},
                        "products": {"type": "string"},
                        "targetMarket": {"type": "string"},
                        "foundedYear": {"type": "string"},
                        "funding": {"type": "string"},
                        "location": {"type": "string"},
                        "usp": {"type": "string"}
                    },
                    "required": ["companyName", "logoPlaceholder", "products", "targetMarket", "foundedYear", "funding", "location", "usp"]
                }
            }
        },
        "required": ["competitors"]
    }

# --- GENERATE COMPETITOR REPORT ---
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

# --- GENERATE SWOT ---
def generate_swot(competitor):
    prompt = (
        f"Generate a SWOT analysis for '{competitor['companyName']}' based on:\n"
        f"- USP: {competitor['usp']}\n"
        f"- Products: {competitor['products']}\n"
        f"- Target Market: {competitor['targetMarket']}\n"
        f"- Funding: {competitor['funding']}\n"
        f"- Founded: {competitor['foundedYear']}\n"
        f"- Location: {competitor['location']}\n\n"
        "Return JSON with four lists: strengths, weaknesses, opportunities, threats."
    )

    schema = {
        "type": "object",
        "properties": {
            "strengths": {"type": "array", "items": {"type": "string"}},
            "weaknesses": {"type": "array", "items": {"type": "string"}},
            "opportunities": {"type": "array", "items": {"type": "string"}},
            "threats": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["strengths", "weaknesses", "opportunities", "threats"]
    }

    try:
        model = genai.GenerativeModel(
            model_name="gemini-2.5-pro",
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": schema
            }
        )
        response = model.generate_content(prompt)
        return json.loads(response.text)
    except Exception as e:
        return {"error": f"SWOT generation failed: {str(e)}"}

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
                st.session_state.result = result
                st.session_state.product = product
                st.session_state.industry = industry
                st.session_state.keywords = keywords
                st.session_state.region = region
                st.session_state.swot_results = {}
            else:
                st.error(result.get("error", "No results returned."))

# --- DISPLAY RESULTS ---
if st.session_state.result:
    result = st.session_state.result
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    st.subheader("📊 Competitor List")
    for idx, c in enumerate(result["competitors"]):
        with st.expander(c["companyName"]):
            st.markdown(f"**📍 Location:** {c['location']}")
            st.markdown(f"**💼 Founded:** {c['foundedYear']} | **Funding:** {c['funding']}")
            st.markdown(f"**🎯 Target Market:** {c['targetMarket']}")
            st.markdown(f"**🧩 Products:** {c['products']}")
            st.markdown(f"**⭐ USP:** {c['usp']}")

            if st.button(f"📊 Generate SWOT: {c['companyName']}", key=f"swot_{idx}"):
                with st.spinner("Generating SWOT..."):
                    swot = generate_swot(c)
                    if "error" in swot:
                        st.error(swot["error"])
                    else:
                        st.session_state.swot_results[c["companyName"]] = {"company": c, "swot": swot}

    # --- DISPLAY SWOTs + ADD TO PDF ---
    if st.session_state.swot_results:
        st.subheader("📄 Generated SWOTs")

        for company_name, data in st.session_state.swot_results.items():
            c = data["company"]
            swot = data["swot"]

            st.markdown(f"## 🔍 {company_name}")
            st.markdown(f"📍 **Location:** {c['location']}")
            st.markdown(f"💼 **Founded:** {c['foundedYear']} | 💰 **Funding:** {c['funding']}")
            st.markdown(f"🎯 **Target Market:** {c['targetMarket']}")
            st.markdown(f"🧩 **Products:** {c['products']}")
            st.markdown(f"⭐ **USP:** {c['usp']}")
            st.markdown("### 🧠 SWOT Analysis")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**✅ Strengths**")
                for s in swot["strengths"]:
                    st.markdown(f"- {s}")
                st.markdown("**⚠️ Weaknesses**")
                for w in swot["weaknesses"]:
                    st.markdown(f"- {w}")
            with col2:
                st.markdown("**📈 Opportunities**")
                for o in swot["opportunities"]:
                    st.markdown(f"- {o}")
                st.markdown("**🚨 Threats**")
                for t in swot["threats"]:
                    st.markdown(f"- {t}")

            # --- ADD TO PDF ---
            pdf.add_page()
            pdf.set_font("Arial", "B", 14)
            pdf.cell(0, 10, f"Company: {company_name}", ln=True)

            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Company Overview", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, f"Location: {c['location']}")
            pdf.multi_cell(0, 8, f"Founded: {c['foundedYear']}")
            pdf.multi_cell(0, 8, f"Funding: {c['funding']}")
            pdf.multi_cell(0, 8, f"Target Market: {c['targetMarket']}")

            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Product / Service Offered", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, f"{c['products']}")

            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "Unique Selling Proposition (USP)", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, f"{c['usp']}")

            pdf.set_font("Arial", "B", 12)
            pdf.cell(0, 10, "SWOT Analysis", ln=True)
            pdf.set_font("Arial", "", 11)
            pdf.multi_cell(0, 8, f"Strengths:\n- " + "\n- ".join(swot["strengths"]))
            pdf.multi_cell(0, 8, f"Weaknesses:\n- " + "\n- ".join(swot["weaknesses"]))
            pdf.multi_cell(0, 8, f"Opportunities:\n- " + "\n- ".join(swot["opportunities"]))
            pdf.multi_cell(0, 8, f"Threats:\n- " + "\n- ".join(swot["threats"]))

        # --- DOWNLOAD BUTTON ---
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        buffer = io.BytesIO(pdf_bytes)
        st.download_button("📥 Download Full Report as PDF", buffer, file_name="Full_Competitor_Report.pdf", mime="application/pdf")
