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

def generate_questions(images, difficulty_level, num_questions, language_instruction):
    """Generate questions from PDF images using Gemini"""
    try:
        model = configure_gemini()
        
        # Create dynamic prompt based on user inputs
        prompt = f"""Generate {num_questions} innovative questions from the PDF content with the following specifications:
        
        Difficulty Level: {difficulty_level}
        Language: {language_instruction}
        
        Please structure the questions clearly and maintain the original language of the document when possible.
        Make sure the questions are diverse and cover different aspects of the content."""
        
        with st.spinner("🤖 Generating questions with AI..."):
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
    
    # Question settings
    difficulty_level = st.selectbox(
        "Difficulty Level",
        ["Mixed (Easy, Medium, Hard)", "Easy only", "Medium only", "Hard only"],
        index=0
    )
    
    num_questions = st.slider(
        "Number of Questions",
        min_value=5,
        max_value=50,
        value=30,
        step=5
    )
    
    language_instruction = st.text_input(
        "Language Instruction",
        value="Maintain the language in which the document is given",
        help="Specify how to handle the language of questions"
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
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.info(f"📄 File size: {len(uploaded_file.getvalue()) / 1024:.1f} KB")
    
    with col2:
        if st.button("🚀 Generate Questions", type="primary"):
            # Convert PDF to images
            with st.spinner("📖 Processing PDF..."):
                pdf_images = pdf_to_images(uploaded_file)
            
            if pdf_images:
                st.success(f"✅ Converted {len(pdf_images)} pages to images")
                
                # Generate questions
                questions = generate_questions(
                    pdf_images, 
                    difficulty_level, 
                    num_questions, 
                    language_instruction
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
                        mime="text/plain"
                    )
            else:
                st.error("❌ Failed to process PDF. Please try again with a different file.")

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
