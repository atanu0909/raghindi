import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import google.generativeai as genai
import tempfile
import os

# ==========================
# Streamlit App Configuration
# ==========================
st.set_page_config(
    page_title="PDF Question Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📚 PDF Question Generator")
st.markdown("Upload a PDF and generate innovative questions using AI!")

# ==========================
# Configure Gemini API
# ==========================
@st.cache_resource
def configure_gemini():
    # Get API key from Streamlit secrets
    api_key = st.secrets.get("GEMINI_API_KEY", "")
    if not api_key:
        st.error("⚠️ Gemini API key not found. Please add it to your Streamlit secrets.")
        st.stop()
    
    genai.configure(api_key=api_key)
    return genai.GenerativeModel("gemini-2.0-flash-exp")

# ==========================
# PDF Processing Functions
# ==========================
def pdf_to_images(pdf_file):
    """Convert uploaded PDF to images"""
    try:
        # Save uploaded file to temporary location
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(pdf_file.read())
            tmp_path = tmp_file.name
        
        # Convert PDF to images
        doc = fitz.open(tmp_path)
        images = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=200)  # Good resolution
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            images.append(img)
        
        doc.close()
        os.unlink(tmp_path)  # Clean up temp file
        
        return images
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return []

def generate_questions(images, mcq_count, short_count, medium_count, long_count, case_study_count, difficulty_level, language_instruction, include_answers, include_marks):
    """Generate questions from PDF images using Gemini"""
    try:
        model = configure_gemini()
        
        # Build question specification
        question_specs = []
        total_questions = mcq_count + short_count + medium_count + long_count + case_study_count
        
        if mcq_count > 0:
            question_specs.append(f"- {mcq_count} Multiple Choice Questions (4 options each, 1 mark each)")
        if short_count > 0:
            question_specs.append(f"- {short_count} Short Answer Questions (2-3 marks each)")
        if medium_count > 0:
            question_specs.append(f"- {medium_count} Medium Answer Questions (5 marks each)")
        if long_count > 0:
            question_specs.append(f"- {long_count} Long Answer Questions (10+ marks each)")
        if case_study_count > 0:
            question_specs.append(f"- {case_study_count} Case Study/Application Questions (variable marks)")
        
        # Create comprehensive prompt
        prompt = f"""Generate exactly {total_questions} innovative questions from the PDF content with the following specifications:

QUESTION DISTRIBUTION:
{chr(10).join(question_specs)}

DIFFICULTY LEVEL: {difficulty_level}
LANGUAGE: {language_instruction}

FORMATTING REQUIREMENTS:
- Clearly separate each question type with headings
- Number all questions sequentially
- {"Include mark allocation for each question" if include_marks else "Focus on content quality"}
- {"Provide sample answers, hints, or marking schemes" if include_answers else "Questions only"}

CONTENT GUIDELINES:
- Ensure questions cover different aspects of the document
- Make questions thought-provoking and comprehensive
- For MCQs: Provide 4 clear options with one correct answer
- For short answers: Focus on key concepts and definitions
- For medium answers: Require explanations and analysis
- For long answers: Demand critical thinking and detailed responses
- For case studies: Create practical application scenarios

Please structure the output clearly with proper headings and numbering."""
        
        with st.spinner("🤖 Generating customized questions with AI..."):
            response = model.generate_content([prompt] + images)
        
        return response.text
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

# ==========================
# Sidebar Configuration
# ==========================
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # Quick Presets
    st.subheader("🎯 Quick Presets")
    preset = st.selectbox(
        "Choose a preset or customize below:",
        ["Custom", "Exam Paper (Mixed)", "Practice Set (MCQ Focus)", "Assignment (Long Answer Focus)", "Quiz (Short & MCQ)"],
        index=0
    )
    
    # Set default values based on preset
    if preset == "Exam Paper (Mixed)":
        default_mcq, default_short, default_medium, default_long, default_case = 10, 8, 5, 3, 2
    elif preset == "Practice Set (MCQ Focus)":
        default_mcq, default_short, default_medium, default_long, default_case = 15, 5, 3, 0, 0
    elif preset == "Assignment (Long Answer Focus)":
        default_mcq, default_short, default_medium, default_long, default_case = 2, 3, 5, 8, 3
    elif preset == "Quiz (Short & MCQ)":
        default_mcq, default_short, default_medium, default_long, default_case = 12, 10, 0, 0, 0
    else:  # Custom
        default_mcq, default_short, default_medium, default_long, default_case = 5, 8, 5, 3, 2
    
    # Question Type Configuration
    st.subheader("📝 Question Types & Distribution")
    
    # MCQ Questions
    mcq_count = st.number_input(
        "Multiple Choice Questions (MCQs)",
        min_value=0,
        max_value=20,
        value=default_mcq,
        help="Number of multiple choice questions"
    )
    
    # Short Answer Questions
    short_count = st.number_input(
        "Short Answer Questions (2-3 marks)",
        min_value=0,
        max_value=15,
        value=default_short,
        help="Brief questions worth 2-3 marks each"
    )
    
    # Medium Answer Questions
    medium_count = st.number_input(
        "Medium Answer Questions (5 marks)",
        min_value=0,
        max_value=10,
        value=default_medium,
        help="Detailed questions worth 5 marks each"
    )
    
    # Long Answer Questions
    long_count = st.number_input(
        "Long Answer Questions (10+ marks)",
        min_value=0,
        max_value=8,
        value=default_long,
        help="Essay-type questions worth 10+ marks each"
    )
    
    # Case Study/Application Questions
    case_study_count = st.number_input(
        "Case Study/Application Questions",
        min_value=0,
        max_value=5,
        value=default_case,
        help="Real-world application and case study questions"
    )
    
    # Calculate total questions
    total_questions = mcq_count + short_count + medium_count + long_count + case_study_count
    
    # Calculate estimated marks
    estimated_marks = (mcq_count * 1) + (short_count * 2.5) + (medium_count * 5) + (long_count * 12) + (case_study_count * 8)
    
    st.info(f"📊 Total Questions: {total_questions}")
    st.info(f"📈 Estimated Total Marks: {estimated_marks:.0f}")
    
    # Difficulty Distribution
    st.subheader("🎯 Difficulty Distribution")
    difficulty_level = st.selectbox(
        "Overall Difficulty Mix",
        ["Balanced (Easy:Medium:Hard = 4:4:2)", "Easy Focus (6:3:1)", "Medium Focus (3:5:2)", "Hard Focus (2:3:5)", "Custom"],
        index=0
    )
    
    # Language and Format Settings
    st.subheader("🌍 Language & Format")
    language_instruction = st.selectbox(
        "Language Preference",
        ["Maintain original document language", "English only", "Hindi only", "Bilingual (English + Hindi)"],
        index=0,
        help="Choose the language for generated questions"
    )
    
    # Additional formatting options
    include_answers = st.checkbox(
        "Include Sample Answers/Hints",
        value=False,
        help="Generate sample answers or hints for questions"
    )
    
    include_marks = st.checkbox(
        "Show Mark Distribution",
        value=True,
        help="Display marks for each question"
    )

# ==========================
# Main App Interface
# ==========================
# File uploader
uploaded_file = st.file_uploader(
    "Choose a PDF file",
    type="pdf",
    help="Upload a PDF document to generate questions from"
)

if uploaded_file is not None:
    # Display file info
    st.success(f"✅ Uploaded: {uploaded_file.name}")
    
    # Show question configuration summary
    if total_questions > 0:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info(f"📄 File size: {len(uploaded_file.getvalue()) / 1024:.1f} KB")
            
            # Display question breakdown
            question_breakdown = []
            if mcq_count > 0:
                question_breakdown.append(f"📝 {mcq_count} MCQs")
            if short_count > 0:
                question_breakdown.append(f"✏️ {short_count} Short (2-3 marks)")
            if medium_count > 0:
                question_breakdown.append(f"📋 {medium_count} Medium (5 marks)")
            if long_count > 0:
                question_breakdown.append(f"📃 {long_count} Long (10+ marks)")
            if case_study_count > 0:
                question_breakdown.append(f"🎯 {case_study_count} Case Studies")
            
            st.info(f"🎯 Question Plan: {' | '.join(question_breakdown)}")
        
        with col2:
            if st.button("🚀 Generate Questions", type="primary", use_container_width=True):
                # Convert PDF to images
                with st.spinner("📖 Processing PDF..."):
                    pdf_images = pdf_to_images(uploaded_file)
                
                if pdf_images:
                    st.success(f"✅ Converted {len(pdf_images)} pages to images")
                    
                    # Generate questions
                    questions = generate_questions(
                        pdf_images, 
                        mcq_count,
                        short_count,
                        medium_count,
                        long_count,
                        case_study_count,
                        difficulty_level, 
                        language_instruction,
                        include_answers,
                        include_marks
                    )
                    
                    if questions:
                        # Display results
                        st.markdown("---")
                        st.header("📝 Generated Questions")
                        
                        # Create expandable sections for better organization
                        with st.expander("📋 View All Questions", expanded=True):
                            st.markdown(questions)
                        
                        # Download option
                        st.download_button(
                            label="💾 Download Questions as Text",
                            data=questions,
                            file_name=f"questions_{uploaded_file.name.replace('.pdf', '.txt')}",
                            mime="text/plain",
                            use_container_width=True
                        )
                else:
                    st.error("❌ Failed to process PDF. Please try again with a different file.")
    else:
        st.warning("⚠️ Please configure at least one type of question in the sidebar.")

# ==========================
# Footer
# ==========================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Made with ❤️ using Streamlit and Google Gemini AI
    </div>
    """,
    unsafe_allow_html=True
)
