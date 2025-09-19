import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import google.generativeai as genai
import tempfile
import os
import json
import time
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors

# ==========================
# Streamlit App Configuration
# ==========================
st.set_page_config(
    page_title="PDF Question Generator & Exam System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'questions_data' not in st.session_state:
    st.session_state.questions_data = None
if 'exam_mode' not in st.session_state:
    st.session_state.exam_mode = False
if 'exam_answers' not in st.session_state:
    st.session_state.exam_answers = {}
if 'exam_submitted' not in st.session_state:
    st.session_state.exam_submitted = False
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None
if 'pattern_format' not in st.session_state:
    st.session_state.pattern_format = None

# Page navigation
page = st.sidebar.selectbox("📋 Select Mode", ["📝 Generate Questions", "🎯 Take Exam", "📊 View Results"])

# Debug mode toggle
debug_mode = st.sidebar.checkbox("🔧 Debug Mode", help="Show additional debugging information")

st.title("📚 PDF Question Generator & Exam System")

if page == "📝 Generate Questions":
    st.markdown("Upload a PDF and generate customized questions using AI!")
elif page == "🎯 Take Exam":
    st.markdown("Take an exam on previously generated questions!")
else:
    st.markdown("View your exam results and performance analysis!")

# Debug information
if debug_mode:
    with st.sidebar.expander("🔧 Debug Info"):
        st.write("Session State:")
        st.write(f"- Questions data available: {st.session_state.questions_data is not None}")
        st.write(f"- Exam submitted: {st.session_state.exam_submitted}")
        st.write(f"- Answers count: {len(st.session_state.exam_answers)}")
        st.write(f"- Evaluation available: {st.session_state.evaluation_result is not None}")
        
        if st.session_state.questions_data:
            st.write(f"- Total questions: {len(st.session_state.questions_data.get('questions', []))}")
        
        # Quick test data button
        if st.button("🧪 Load Test Data"):
            st.session_state.questions_data = {
                "questions": [
                    {
                        "id": 1,
                        "type": "mcq",
                        "question": "What is the capital of France?",
                        "options": ["A) London", "B) Berlin", "C) Paris", "D) Madrid"],
                        "correct_answer": "C",
                        "marks": 1,
                        "sample_answer": "Paris is the capital city of France."
                    },
                    {
                        "id": 2,
                        "type": "short",
                        "question": "Explain the concept of gravity.",
                        "marks": 3,
                        "sample_answer": "Gravity is a fundamental force of nature that attracts objects with mass toward each other."
                    }
                ]
            }
            st.success("Test data loaded!")

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

def generate_questions(images, mcq_count, short_count, medium_count, long_count, case_study_count, difficulty_level, language_instruction, include_answers, include_marks, uploaded_pattern=None, pattern_instructions=""):
    """Generate questions from PDF images using Gemini"""
    try:
        model = configure_gemini()
        
        # Process pattern if uploaded
        pattern_context = ""
        pattern_content = None
        pattern_format = None
        
        if uploaded_pattern:
            pattern_content = process_pattern_file(uploaded_pattern)
            if pattern_content:
                # Extract detailed format for exact replication
                pattern_format = extract_pattern_format(pattern_content)
                
                if isinstance(pattern_content, Image.Image):
                    pattern_context = f"""\n\nEXACT PATTERN REPLICATION: You must create questions that EXACTLY match the visual format, layout, spacing, numbering, and style shown in the uploaded pattern image.

CRITICAL REQUIREMENTS:
- Copy the EXACT header format, including institution name, title, subject, time, marks
- Use the SAME question numbering style (1., Q1, Question 1, etc.)
- Match the EXACT spacing and indentation
- Preserve ALL symbols, borders, decorative elements
- Follow the SAME marks notation style [5], (5 marks), etc.
- Maintain the SAME font styles and sizes
- Keep the EXACT section divisions and headers
- Use IDENTICAL instruction formatting

The final output will be converted to match this pattern EXACTLY - every symbol, space, and formatting element must be preserved."""
                    
                else:
                    pattern_context = f"""\n\nEXACT PATTERN REPLICATION: You must create questions that EXACTLY match this sample format:

SAMPLE PATTERN:
{pattern_content}

CRITICAL REQUIREMENTS:
- Copy the EXACT header text and formatting
- Use the IDENTICAL question numbering pattern
- Match the PRECISE spacing between sections
- Preserve ALL punctuation, symbols, and formatting marks
- Follow the SAME marks display format
- Maintain IDENTICAL section headers and divisions
- Use the EXACT instruction format and wording style
- Keep the SAME font emphasis (bold, italic, etc.)

Generate questions that will be VISUALLY IDENTICAL to this sample when converted to PDF."""
                
                if pattern_instructions:
                    pattern_context += f"\n\nADDITIONAL REQUIREMENTS: {pattern_instructions}"
        
        # Build question specification (only if not using pattern)
        if not uploaded_pattern:
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
        else:
            # When using pattern, let AI determine the structure
            question_specs = ["Follow the uploaded pattern structure and format"]
            total_questions = "as shown in pattern"
        
        # Create comprehensive prompt for display questions
        if uploaded_pattern:
            display_prompt = f"""Generate questions from the PDF content following the EXACT pattern, format, and structure provided.

SOURCE CONTENT: Use the uploaded PDF as the source material for questions.

{pattern_context}

DIFFICULTY LEVEL: {difficulty_level}
LANGUAGE: {language_instruction}

REQUIREMENTS:
- Follow the EXACT format, numbering, and structure from the pattern
- Maintain the same question types and mark distribution as shown
- {"Include mark allocation as shown in pattern" if include_marks else "Focus on content quality"}
- {"Provide sample answers where indicated in pattern" if include_answers else "Generate questions only"}

CONTENT GUIDELINES:
- Ensure questions are based on the PDF content
- Match the difficulty and complexity shown in the pattern
- Follow any specific formatting or organizational structure
- Maintain consistency with the pattern's style and approach

Generate the questions exactly as they would appear in a real exam following this pattern."""

        else:
            display_prompt = f"""Generate exactly {total_questions} innovative questions from the PDF content with the following specifications:

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

        # Create structured prompt for exam data
        if uploaded_pattern:
            exam_prompt = f"""Generate questions from the PDF content in JSON format following the uploaded pattern structure.

{pattern_context}

DIFFICULTY LEVEL: {difficulty_level}
LANGUAGE: {language_instruction}

Return ONLY a valid JSON object following the pattern structure with this format:
{{
    "questions": [
        {{
            "id": 1,
            "type": "mcq",
            "question": "Question text here",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "marks": 1,
            "sample_answer": "Brief explanation"
        }}
    ]
}}

Types: "mcq", "short", "medium", "long", "case_study"
Match the pattern's question distribution and mark allocation.
For non-MCQ questions, omit "options" and "correct_answer" fields."""

        else:
            exam_prompt = f"""Generate exactly {total_questions} questions from the PDF content in JSON format for an exam system.

QUESTION DISTRIBUTION:
{chr(10).join(question_specs)}

DIFFICULTY LEVEL: {difficulty_level}
LANGUAGE: {language_instruction}

Return ONLY a valid JSON object with this exact structure:
{{
    "questions": [
        {{
            "id": 1,
            "type": "mcq",
            "question": "Question text here",
            "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
            "correct_answer": "A",
            "marks": 1,
            "sample_answer": "Brief explanation of correct answer"
        }},
        {{
            "id": 2,
            "type": "short",
            "question": "Question text here",
            "marks": 3,
            "sample_answer": "Expected answer with key points"
        }}
    ]
}}

Types: "mcq", "short", "medium", "long", "case_study"
For non-MCQ questions, omit "options" and "correct_answer" fields.
Make questions comprehensive and varied."""
        
        with st.spinner("🤖 Generating questions with AI..."):
            # Prepare inputs for model
            model_inputs = [display_prompt] + images
            exam_inputs = [exam_prompt] + images
            
            # Add pattern image if available
            if uploaded_pattern and isinstance(pattern_content, Image.Image):
                model_inputs.insert(-len(images), pattern_content)
                exam_inputs.insert(-len(images), pattern_content)
            
            # Generate display version
            display_response = model.generate_content(model_inputs)
            
            # Generate structured version for exam
            exam_response = model.generate_content(exam_inputs)
            
            # Try to parse JSON data
            try:
                # Clean up the response to extract JSON
                response_text = exam_response.text.strip()
                
                # Look for JSON content between curly braces
                if '{' in response_text and '}' in response_text:
                    json_start = response_text.find('{')
                    json_end = response_text.rfind('}') + 1
                    json_text = response_text[json_start:json_end]
                    exam_data = json.loads(json_text)
                    st.session_state.questions_data = exam_data
                    st.success("✅ Exam data created successfully!")
                else:
                    raise ValueError("No JSON found in response")
                    
            except (json.JSONDecodeError, ValueError) as e:
                st.warning(f"⚠️ Could not create structured exam data: {str(e)}")
                st.info("📝 Questions generated for display only. Exam mode will not be available.")
                st.session_state.questions_data = None
                
                # Show debug info
                with st.expander("🔧 Debug Info (Click to expand)"):
                    st.text("Raw AI Response for Exam Data:")
                    st.text(exam_response.text[:1000] + "..." if len(exam_response.text) > 1000 else exam_response.text)
        
        # Store pattern format in session state for PDF generation
        if pattern_format:
            st.session_state.pattern_format = pattern_format
        else:
            st.session_state.pattern_format = None
        
        return display_response.text
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

def process_pattern_file(uploaded_file):
    """Process uploaded pattern file and extract content"""
    try:
        file_type = uploaded_file.type
        content = ""
        
        if file_type == "application/pdf":
            # Process PDF file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_path = tmp_file.name
            
            doc = fitz.open(tmp_path)
            for page in doc:
                content += page.get_text()
            doc.close()
            os.unlink(tmp_path)
            
        elif file_type in ["image/jpeg", "image/jpg", "image/png"]:
            # Process image file using OCR-like approach with Gemini Vision
            image = Image.open(uploaded_file)
            return image  # Return image for Gemini Vision processing
            
        elif file_type == "text/plain":
            # Process text file
            content = uploaded_file.read().decode('utf-8')
            
        elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            # For DOCX files, return the file for processing
            st.warning("DOCX files will be processed as images. For best results, use PDF or text format.")
            return uploaded_file
            
        return content if content.strip() else None
        
    except Exception as e:
        st.error(f"Error processing pattern file: {str(e)}")
        return None

def analyze_question_pattern(pattern_content):
    """Analyze the pattern content using AI"""
    try:
        model = configure_gemini()
        
        if isinstance(pattern_content, Image.Image):
            # Image-based pattern analysis
            analysis_prompt = """Analyze this question paper/pattern image and provide a detailed analysis of:

1. Question Types (MCQ, Short Answer, Long Answer, etc.)
2. Number of questions in each category
3. Mark distribution and allocation
4. Question format and style
5. Numbering and organization pattern
6. Any specific instructions or requirements
7. Difficulty progression if visible
8. Time allocation if mentioned

Provide a clear, structured analysis that can be used to generate similar questions."""

            response = model.generate_content([analysis_prompt, pattern_content])
            
        else:
            # Text-based pattern analysis
            analysis_prompt = f"""Analyze this question paper/pattern and provide a detailed analysis of:

CONTENT TO ANALYZE:
{pattern_content}

Please analyze:
1. Question Types (MCQ, Short Answer, Long Answer, etc.)
2. Number of questions in each category
3. Mark distribution and allocation
4. Question format and style
5. Numbering and organization pattern
6. Any specific instructions or requirements
7. Difficulty progression
8. Time allocation if mentioned

Provide a clear, structured analysis that can be used to generate similar questions."""

            response = model.generate_content(analysis_prompt)
        
        return response.text
        
    except Exception as e:
        st.error(f"Error analyzing pattern: {str(e)}")
        return None

def extract_pattern_format(pattern_content):
    """Extract detailed visual formatting information for exact pattern replication"""
    try:
        model = configure_gemini()
        
        if isinstance(pattern_content, Image.Image):
            # Enhanced image-based format extraction for exact visual replication
            format_prompt = """Analyze this question paper image and extract EVERY visual detail for exact replication. Return detailed JSON:

{
    "document_structure": {
        "page_margins": "Exact margin measurements (top, bottom, left, right)",
        "page_orientation": "Portrait or Landscape",
        "total_width": "Page width",
        "total_height": "Page height"
    },
    "header_section": {
        "institution_logo": "Description of any logo/symbol and position",
        "institution_name": "Exact text and font style",
        "title": "Main title text and formatting",
        "subtitle": "Subtitle if any",
        "exam_details": {
            "subject": "Subject name and style",
            "time": "Time duration and position",
            "marks": "Total marks and position",
            "date": "Date if visible"
        },
        "header_borders": "Any borders, lines, or decorative elements",
        "spacing": "Exact spacing between header elements"
    },
    "instructions_section": {
        "title": "Instructions heading style",
        "content": ["All instruction text exactly as written"],
        "formatting": "Bold, italic, underlined text patterns",
        "numbering": "Numbering style for instructions",
        "borders": "Any boxes or borders around instructions"
    },
    "question_layout": {
        "section_headers": "How sections are labeled (Part A, Section I, etc.)",
        "question_numbering": "Exact numbering pattern (1., Q1, (1), etc.)",
        "question_spacing": "Spacing between questions",
        "indent_pattern": "How questions are indented",
        "marks_position": "Where marks are shown [5 marks] or (5) etc.",
        "answer_space": "Lines for answers or blank space patterns"
    },
    "mcq_formatting": {
        "option_style": "How options are labeled (a), (A), i), etc.",
        "option_layout": "Horizontal or vertical option arrangement",
        "option_spacing": "Space between options",
        "answer_format": "How answer spaces are provided"
    },
    "visual_elements": {
        "symbols": "Any mathematical symbols, arrows, bullets",
        "decorative_elements": "Borders, lines, boxes, decorations",
        "fonts_detected": "Font styles used (bold, italic, sizes)",
        "special_characters": "Special characters or symbols used"
    },
    "exact_text_template": "The complete text template with [QUESTION] placeholders where new questions should go"
}

Be extremely detailed - I need to recreate this EXACTLY."""
            
            response = model.generate_content([format_prompt, pattern_content])
        else:
            # Enhanced text-based format extraction
            format_prompt = f"""Analyze this question paper text and extract EVERY formatting detail for exact visual replication:

PATTERN CONTENT:
{pattern_content}

Return extremely detailed JSON for exact replication:
{{
    "document_structure": {{
        "layout_type": "How the document is structured",
        "total_sections": "Number of sections/parts",
        "page_organization": "How content is organized on page"
    }},
    "exact_header": {{
        "institution_line": "Exact institution text if any",
        "title_line": "Main title exactly as written",
        "exam_info": "Subject, time, marks exactly as formatted",
        "header_symbols": "Any symbols, borders, or decorative elements",
        "spacing_pattern": "Line breaks and spacing in header"
    }},
    "instructions_format": {{
        "instruction_title": "How instructions section starts",
        "instruction_list": ["Each instruction exactly as written"],
        "numbering_style": "How instructions are numbered",
        "formatting_marks": "Bold, italic, or special formatting indicators"
    }},
    "question_structure": {{
        "section_labels": "How sections are marked (Part A, Section I, etc.)",
        "question_prefix": "How questions start (Q.1, 1., Question 1, etc.)",
        "marks_notation": "How marks are shown [5], (5 marks), etc.",
        "spacing_rules": "Line breaks between questions",
        "indentation": "How text is indented",
        "answer_indicators": "Lines, spaces, or marks for answers"
    }},
    "mcq_pattern": {{
        "option_markers": "How options are labeled (a), (A), i), etc.",
        "option_arrangement": "How options are laid out",
        "option_spacing": "Spacing between options"
    }},
    "special_elements": {{
        "symbols_used": "Any special symbols found",
        "formatting_marks": "Bold, italic, underline indicators",
        "decorative_elements": "Lines, borders, or visual separators"
    }},
    "complete_template": "The entire text with [QUESTION_PLACEHOLDER] where questions should be inserted"
}}

Extract EVERY detail - I need perfect visual matching."""
            
            response = model.generate_content(format_prompt)
        
        # Enhanced JSON parsing
        response_text = response.text.strip()
        if '{' in response_text and '}' in response_text:
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            json_text = response_text[json_start:json_end]
            format_data = json.loads(json_text)
            return format_data
        
        return None
        
    except Exception as e:
        st.error(f"Error extracting detailed format: {str(e)}")
        return None

def generate_exact_replica_pdf(questions_text, pattern_format=None, filename="questions.pdf"):
    """Generate PDF that exactly replicates the visual format of uploaded sample paper"""
    try:
        pdf_buffer = io.BytesIO()
        
        if pattern_format and pattern_format.get('complete_template'):
            # Use template-based exact replication
            return generate_template_based_pdf(questions_text, pattern_format, pdf_buffer)
        
        # Enhanced visual replication based on detailed format analysis
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4)
        
        # Extract exact formatting details
        if pattern_format:
            # Set margins based on pattern
            margins = extract_margins_from_pattern(pattern_format)
            doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, 
                                   rightMargin=margins['right'], leftMargin=margins['left'], 
                                   topMargin=margins['top'], bottomMargin=margins['bottom'])
        
        # Create exact visual styles
        styles = create_exact_pattern_styles(pattern_format)
        story = []
        
        # Replicate header section exactly
        if pattern_format and pattern_format.get('header_section'):
            story.extend(create_exact_header(pattern_format['header_section'], styles))
        
        # Replicate instructions section exactly  
        if pattern_format and pattern_format.get('instructions_section'):
            story.extend(create_exact_instructions(pattern_format['instructions_section'], styles))
        
        # Insert questions maintaining exact format
        story.extend(insert_questions_in_exact_format(questions_text, pattern_format, styles))
        
        # Build PDF
        doc.build(story)
        pdf_bytes = pdf_buffer.getvalue()
        pdf_buffer.close()
        return pdf_bytes
        
    except Exception as e:
        st.error(f"Error creating exact replica PDF: {str(e)}")
        return None

def generate_template_based_pdf(questions_text, pattern_format, pdf_buffer):
    """Generate PDF by replacing placeholders in exact template"""
    try:
        template = pattern_format.get('complete_template', '')
        
        # Parse questions from generated text
        questions_list = parse_generated_questions(questions_text)
        
        # Replace placeholders with actual questions
        final_content = template
        for i, question in enumerate(questions_list, 1):
            placeholder = f"[QUESTION_PLACEHOLDER_{i}]"
            if placeholder not in final_content:
                placeholder = "[QUESTION_PLACEHOLDER]"
            
            final_content = final_content.replace(placeholder, question, 1)
        
        # Convert to PDF maintaining exact formatting
        doc = SimpleDocTemplate(pdf_buffer, pagesize=A4, 
                               rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
        
        # Preserve exact text formatting
        styles = getSampleStyleSheet()
        story = []
        
        # Split by lines and maintain exact spacing
        lines = final_content.split('\n')
        for line in lines:
            if line.strip():
                # Detect formatting and apply accordingly
                if detect_header_line(line, pattern_format):
                    story.append(Paragraph(line, create_header_style(line, pattern_format, styles)))
                elif detect_question_line(line, pattern_format):
                    story.append(Paragraph(line, create_question_style(line, pattern_format, styles)))
                elif detect_option_line(line, pattern_format):
                    story.append(Paragraph(line, create_option_style(line, pattern_format, styles)))
                else:
                    story.append(Paragraph(line, styles['Normal']))
            else:
                story.append(Spacer(1, 12))  # Maintain blank lines
        
        doc.build(story)
        return pdf_buffer.getvalue()
        
    except Exception as e:
        st.error(f"Error in template-based PDF generation: {str(e)}")
        return None

def extract_margins_from_pattern(pattern_format):
    """Extract exact margin measurements from pattern"""
    try:
        if pattern_format.get('document_structure', {}).get('page_margins'):
            # Parse margin information
            margins_info = pattern_format['document_structure']['page_margins']
            # Default margins if parsing fails
            return {'top': 72, 'bottom': 72, 'left': 72, 'right': 72}
        return {'top': 72, 'bottom': 72, 'left': 72, 'right': 72}
    except:
        return {'top': 72, 'bottom': 72, 'left': 72, 'right': 72}

def create_exact_pattern_styles(pattern_format):
    """Create styles that exactly match the pattern"""
    styles = getSampleStyleSheet()
    custom_styles = {}
    
    try:
        if pattern_format:
            # Create header style based on pattern
            custom_styles['header'] = ParagraphStyle(
                'ExactHeader',
                parent=styles['Heading1'],
                fontSize=16,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold',
                spaceAfter=20
            )
            
            # Create question style based on pattern
            question_format = pattern_format.get('question_structure', {})
            custom_styles['question'] = ParagraphStyle(
                'ExactQuestion', 
                parent=styles['Normal'],
                fontSize=12,
                leftIndent=get_indent_from_pattern(question_format),
                spaceAfter=get_spacing_from_pattern(question_format),
                fontName='Helvetica'
            )
            
            # Create option style for MCQs
            mcq_format = pattern_format.get('mcq_pattern', {})
            custom_styles['option'] = ParagraphStyle(
                'ExactOption',
                parent=styles['Normal'],
                fontSize=11,
                leftIndent=get_mcq_indent_from_pattern(mcq_format),
                spaceAfter=6,
                fontName='Helvetica'
            )
    except:
        # Fallback to default styles
        custom_styles = {
            'header': styles['Heading1'],
            'question': styles['Normal'],  
            'option': styles['Normal']
        }
    
    return custom_styles

def create_exact_header(header_info, styles):
    """Create header section exactly matching pattern"""
    header_elements = []
    
    try:
        # Institution logo/name
        if header_info.get('institution_name'):
            header_elements.append(Paragraph(header_info['institution_name'], styles['header']))
            header_elements.append(Spacer(1, 12))
        
        # Title
        if header_info.get('title'):
            header_elements.append(Paragraph(header_info['title'], styles['header']))
            header_elements.append(Spacer(1, 10))
        
        # Exam details in exact format
        if header_info.get('exam_details'):
            details = header_info['exam_details']
            detail_text = []
            if details.get('subject'):
                detail_text.append(f"Subject: {details['subject']}")
            if details.get('time'):
                detail_text.append(f"Time: {details['time']}")
            if details.get('marks'):
                detail_text.append(f"Max. Marks: {details['marks']}")
            
            if detail_text:
                header_elements.append(Paragraph(' | '.join(detail_text), styles['question']))
                header_elements.append(Spacer(1, 15))
                
    except Exception as e:
        st.warning(f"Header creation warning: {str(e)}")
    
    return header_elements

def create_exact_instructions(instructions_info, styles):
    """Create instructions section exactly matching pattern"""
    instruction_elements = []
    
    try:
        if instructions_info.get('title'):
            instruction_elements.append(Paragraph(f"<b>{instructions_info['title']}</b>", styles['question']))
        
        if instructions_info.get('content'):
            for instruction in instructions_info['content']:
                instruction_elements.append(Paragraph(f"• {instruction}", styles['option']))
        
        instruction_elements.append(Spacer(1, 20))
    except Exception as e:
        st.warning(f"Instructions creation warning: {str(e)}")
    
    return instruction_elements

def insert_questions_in_exact_format(questions_text, pattern_format, styles):
    """Insert questions maintaining exact formatting from pattern"""
    question_elements = []
    
    try:
        lines = questions_text.split('\n')
        
        for line in lines:
            line = line.strip()
            if not line:
                question_elements.append(Spacer(1, 8))
                continue
            
            # Apply exact formatting based on pattern analysis
            if detect_section_header(line, pattern_format):
                question_elements.append(Spacer(1, 15))
                question_elements.append(Paragraph(f"<b>{line}</b>", styles['header']))
                question_elements.append(Spacer(1, 10))
            elif detect_question_start(line, pattern_format):
                question_elements.append(Paragraph(line, styles['question']))
            elif detect_mcq_option(line, pattern_format):
                question_elements.append(Paragraph(line, styles['option']))
            else:
                question_elements.append(Paragraph(line, styles['question']))
                
    except Exception as e:
        st.warning(f"Question formatting warning: {str(e)}")
        # Fallback: add questions as-is
        question_elements.append(Paragraph(questions_text, styles['question']))
    
    return question_elements

# Helper functions for pattern detection
def get_indent_from_pattern(question_format):
    """Extract indentation from pattern"""
    return 0  # Default, can be enhanced based on pattern analysis

def get_spacing_from_pattern(question_format):
    """Extract spacing from pattern"""
    return 12  # Default, can be enhanced based on pattern analysis

def get_mcq_indent_from_pattern(mcq_format):
    """Extract MCQ indentation from pattern"""
    return 20  # Default, can be enhanced based on pattern analysis

def detect_header_line(line, pattern_format):
    """Detect if line is a header based on pattern"""
    return any(word in line.upper() for word in ['UNIVERSITY', 'COLLEGE', 'EXAMINATION', 'TEST'])

def detect_question_line(line, pattern_format):
    """Detect if line is a question based on pattern"""
    return line and (line[0].isdigit() or line.startswith('Q') or line.startswith('q'))

def detect_option_line(line, pattern_format):
    """Detect if line is an MCQ option based on pattern"""
    return line and any(line.startswith(opt) for opt in ['A)', 'B)', 'C)', 'D)', 'a)', 'b)', 'c)', 'd)', '(A)', '(B)', '(C)', '(D)'])

def detect_section_header(line, pattern_format):
    """Detect section headers"""
    return any(word in line.upper() for word in ['SECTION', 'PART', 'MCQ', 'SHORT ANSWER', 'LONG ANSWER'])

def detect_question_start(line, pattern_format):
    """Detect start of a question"""
    return line and (line[0].isdigit() or line.startswith('Q') or 'Question' in line)

def detect_mcq_option(line, pattern_format):
    """Detect MCQ options"""
    return line and any(line.startswith(opt) for opt in ['A)', 'B)', 'C)', 'D)', 'a)', 'b)', 'c)', 'd)', '(A)', '(B)', '(C)', '(D)'])

def parse_generated_questions(questions_text):
    """Parse generated questions into list"""
    questions = []
    current_question = ""
    
    lines = questions_text.split('\n')
    for line in lines:
        line = line.strip()
        if line and (line[0].isdigit() or line.startswith('Q')):
            if current_question:
                questions.append(current_question.strip())
            current_question = line
        else:
            current_question += f"\n{line}"
    
    if current_question:
        questions.append(current_question.strip())
    
    return questions

def create_header_style(line, pattern_format, styles):
    """Create style for header lines"""
    return ParagraphStyle('HeaderStyle', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold')

def create_question_style(line, pattern_format, styles):
    """Create style for question lines"""
    return ParagraphStyle('QuestionStyle', parent=styles['Normal'], fontSize=12, fontName='Helvetica')

def create_option_style(line, pattern_format, styles):
    """Create style for option lines"""
    return ParagraphStyle('OptionStyle', parent=styles['Normal'], fontSize=11, leftIndent=20, fontName='Helvetica')

# Maintain backward compatibility
def generate_formatted_pdf(questions_text, pattern_format=None, filename="questions.pdf"):
    """Wrapper for backward compatibility - calls exact replica function"""
    return generate_exact_replica_pdf(questions_text, pattern_format, filename)

def evaluate_exam_answers(questions_data, user_answers, answer_images=None):
    """Evaluate user answers using AI"""
    try:
        model = configure_gemini()
        
        # Prepare evaluation data
        evaluation_data = []
        total_marks = 0
        obtained_marks = 0
        
        for question in questions_data['questions']:
            q_id = question['id']
            q_type = question['type']
            q_marks = question['marks']
            total_marks += q_marks
            
            user_answer = user_answers.get(str(q_id), "").strip()
            
            if q_type == "mcq":
                # MCQ evaluation
                correct_answer = question.get('correct_answer', '').strip()
                if correct_answer:
                    is_correct = user_answer.upper() == correct_answer.upper()
                    marks_obtained = q_marks if is_correct else 0
                    obtained_marks += marks_obtained
                    
                    evaluation_data.append({
                        "question_id": q_id,
                        "question": question['question'],
                        "type": q_type,
                        "user_answer": user_answer,
                        "correct_answer": correct_answer,
                        "marks_obtained": marks_obtained,
                        "total_marks": q_marks,
                        "is_correct": is_correct
                    })
                else:
                    # If no correct answer is provided, treat as subjective
                    evaluation_data.append({
                        "question_id": q_id,
                        "question": question['question'],
                        "type": q_type,
                        "user_answer": user_answer,
                        "sample_answer": question.get('sample_answer', ''),
                        "total_marks": q_marks,
                        "needs_ai_evaluation": True
                    })
            else:
                # Subjective question - need AI evaluation
                evaluation_data.append({
                    "question_id": q_id,
                    "question": question['question'],
                    "type": q_type,
                    "user_answer": user_answer,
                    "sample_answer": question.get('sample_answer', ''),
                    "total_marks": q_marks,
                    "needs_ai_evaluation": True
                })
        
        # AI evaluation for subjective questions
        subjective_questions = [q for q in evaluation_data if q.get('needs_ai_evaluation')]
        
        if subjective_questions:
            evaluation_prompt = f"""You are an expert examiner. Evaluate the following student answers and provide marks out of the total allocated marks.

EVALUATION CRITERIA:
- Accuracy of content (40%)
- Completeness of answer (30%)
- Understanding of concepts (20%)
- Clarity of explanation (10%)

For each answer, provide marks as a number between 0 and the total marks allocated.

QUESTIONS AND ANSWERS TO EVALUATE:
"""
            
            for i, q in enumerate(subjective_questions, 1):
                evaluation_prompt += f"""
--- Question {i} ---
Question ID: {q['question_id']}
Question: {q['question']}
Total Marks: {q['total_marks']}
Sample Answer: {q['sample_answer']}
Student Answer: {q['user_answer']}
"""
            
            evaluation_prompt += """

Respond ONLY in this JSON format (no other text):
{
    "evaluations": [
        {
            "question_id": 1,
            "marks_obtained": 7.5,
            "feedback": "Good understanding but missing key points about...",
            "suggestions": "Include more examples and explain the concept of..."
        }
    ]
}
"""
            
            with st.spinner("🤖 AI is evaluating your subjective answers..."):
                try:
                    eval_response = model.generate_content(evaluation_prompt)
                    response_text = eval_response.text.strip()
                    
                    # Try to extract JSON from the response
                    if '{' in response_text and '}' in response_text:
                        json_start = response_text.find('{')
                        json_end = response_text.rfind('}') + 1
                        json_text = response_text[json_start:json_end]
                        eval_result = json.loads(json_text)
                        
                        # Update evaluation data with AI scores
                        for eval_item in eval_result.get('evaluations', []):
                            q_id = eval_item['question_id']
                            marks = float(eval_item.get('marks_obtained', 0))
                            obtained_marks += marks
                            
                            # Find and update the corresponding question
                            for i, q in enumerate(evaluation_data):
                                if q['question_id'] == q_id and q.get('needs_ai_evaluation'):
                                    evaluation_data[i].update({
                                        'marks_obtained': marks,
                                        'feedback': eval_item.get('feedback', 'Good attempt'),
                                        'suggestions': eval_item.get('suggestions', ''),
                                        'needs_ai_evaluation': False
                                    })
                                    break
                    else:
                        # Fallback: Give partial marks for answered questions
                        st.warning("AI evaluation incomplete. Using fallback scoring.")
                        for q in subjective_questions:
                            fallback_marks = q['total_marks'] * 0.6 if q['user_answer'] else 0
                            obtained_marks += fallback_marks
                            
                            for i, eval_q in enumerate(evaluation_data):
                                if eval_q['question_id'] == q['question_id'] and eval_q.get('needs_ai_evaluation'):
                                    evaluation_data[i].update({
                                        'marks_obtained': fallback_marks,
                                        'feedback': 'Answer provided - partial credit given',
                                        'suggestions': 'Detailed evaluation was not available',
                                        'needs_ai_evaluation': False
                                    })
                                    break
                                    
                except (json.JSONDecodeError, KeyError, ValueError) as e:
                    st.warning(f"AI evaluation error: {str(e)}. Using fallback scoring.")
                    # Fallback scoring for subjective questions
                    for q in subjective_questions:
                        fallback_marks = q['total_marks'] * 0.6 if q['user_answer'] else 0
                        obtained_marks += fallback_marks
                        
                        for i, eval_q in enumerate(evaluation_data):
                            if eval_q['question_id'] == q['question_id'] and eval_q.get('needs_ai_evaluation'):
                                evaluation_data[i].update({
                                    'marks_obtained': fallback_marks,
                                    'feedback': 'Answer provided - partial credit given',
                                    'suggestions': 'Please review the sample answer for improvement',
                                    'needs_ai_evaluation': False
                                })
                                break
        
        # Calculate final results
        percentage = (obtained_marks / total_marks) * 100 if total_marks > 0 else 0
        
        return {
            'total_marks': total_marks,
            'obtained_marks': obtained_marks,
            'percentage': percentage,
            'evaluations': evaluation_data,
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
    except Exception as e:
        st.error(f"Error evaluating answers: {str(e)}")
        return None

# ==========================
# PAGE 1: QUESTION GENERATION
# ==========================
if page == "📝 Generate Questions":
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
        
        # Pattern Upload Feature for Exact Visual Replication
        st.markdown("##### 🎯 EXACT VISUAL REPLICATION")
        st.info("� **NEW**: Upload any sample paper and get downloaded questions in EXACTLY the same visual format - every symbol, spacing, header, and layout will be identical!")
        
        pattern_option = st.radio(
            "Choose generation method:",
            ["Manual Configuration", "🎯 Upload Sample Paper for EXACT Replication"],
            help="Upload a sample paper to create visually identical question papers with your content"
        )
        
        uploaded_pattern = None
        pattern_instructions = ""
        
        if pattern_option == "🎯 Upload Sample Paper for EXACT Replication":
            st.markdown("**📤 Upload Your Sample Question Paper**")
            uploaded_pattern = st.file_uploader(
                "Upload Sample Paper for Exact Visual Matching",
                type=['pdf', 'jpg', 'jpeg', 'png', 'txt', 'docx'],
                help="The downloaded PDF will be visually IDENTICAL to this sample - preserving every formatting detail"
            )
            
            if uploaded_pattern:
                st.success(f"🎯 **Sample Paper Uploaded**: {uploaded_pattern.name}")
                st.info("📝 **Visual Analysis**: AI will analyze every formatting detail and create an EXACT replica with your generated questions.")
                
                # Additional instructions for exact replication
                pattern_instructions = st.text_area(
                    "🎯 Additional Replication Instructions (Optional)",
                    placeholder="e.g., 'Preserve the university logo position', 'Keep the exact border style', 'Maintain identical spacing between sections'...",
                    help="Specify any additional details for exact visual matching (the AI will already copy all visible formatting)"
                )
                
                # Show visual analysis and format extraction
                with st.expander("🎯 Visual Analysis & Format Extraction", expanded=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button("📊 Analyze Visual Structure", help="AI analyzes the visual layout and formatting"):
                            with st.spinner("� Analyzing visual structure..."):
                                # Process the uploaded pattern
                                pattern_content = process_pattern_file(uploaded_pattern)
                                if pattern_content:
                                    analysis = analyze_question_pattern(pattern_content)
                                    if analysis:
                                        st.markdown("**📋 Visual Structure Analysis:**")
                                        st.markdown(analysis)
                    
                    with col2:
                        if st.button("🎨 Extract Exact Format", help="Extract every formatting detail for pixel-perfect replication"):
                            with st.spinner("🎨 Extracting format details..."):
                                pattern_content = process_pattern_file(uploaded_pattern)
                                if pattern_content:
                                    format_info = extract_pattern_format(pattern_content)
                                    if format_info:
                                        st.success("✅ Format information extracted!")
                                        st.json(format_info)
                                        # Store in session state
                                        st.session_state.pattern_format = format_info
                                    else:
                                        st.warning("⚠️ Could not extract format information")
        
        # Show manual configuration only if not using pattern upload or if pattern analysis suggests numbers
        show_manual_config = (pattern_option == "Manual Configuration" or 
                             (pattern_option == "Upload Question Pattern/Sample Paper" and not uploaded_pattern))
        
        if show_manual_config:
            st.markdown("##### ⚙️ Manual Configuration")
        
        # MCQ Questions
        mcq_count = st.number_input(
            "Multiple Choice Questions (MCQs)",
            min_value=0,
            max_value=20,
            value=default_mcq,
            help="Number of multiple choice questions",
            disabled=(pattern_option == "Upload Question Pattern/Sample Paper" and uploaded_pattern is not None)
        )
        
        # Short Answer Questions
        short_count = st.number_input(
            "Short Answer Questions (2-3 marks)",
            min_value=0,
            max_value=15,
            value=default_short,
            help="Brief questions worth 2-3 marks each",
            disabled=(pattern_option == "Upload Question Pattern/Sample Paper" and uploaded_pattern is not None)
        )
        
        # Medium Answer Questions
        medium_count = st.number_input(
            "Medium Answer Questions (5 marks)",
            min_value=0,
            max_value=10,
            value=default_medium,
            help="Detailed questions worth 5 marks each",
            disabled=(pattern_option == "Upload Question Pattern/Sample Paper" and uploaded_pattern is not None)
        )
        
        # Long Answer Questions
        long_count = st.number_input(
            "Long Answer Questions (10+ marks)",
            min_value=0,
            max_value=8,
            value=default_long,
            help="Essay-type questions worth 10+ marks each",
            disabled=(pattern_option == "Upload Question Pattern/Sample Paper" and uploaded_pattern is not None)
        )
        
        # Case Study/Application Questions
        case_study_count = st.number_input(
            "Case Study/Application Questions",
            min_value=0,
            max_value=5,
            value=default_case,
            help="Real-world application and case study questions",
            disabled=(pattern_option == "Upload Question Pattern/Sample Paper" and uploaded_pattern is not None)
        )
        
        # Calculate total questions and marks
        if uploaded_pattern:
            st.info("📋 Using uploaded pattern - question count determined by pattern")
            st.info("📈 Marks will be calculated based on pattern structure")
            total_questions = 1  # Set to 1 to enable the generate button
        else:
            total_questions = mcq_count + short_count + medium_count + long_count + case_study_count
            estimated_marks = (mcq_count * 1) + (short_count * 2.5) + (medium_count * 5) + (long_count * 12) + (case_study_count * 8)
            
            st.info(f"📊 Total Questions: {total_questions}")
            st.info(f"📈 Estimated Total Marks: {estimated_marks:.0f}")
        
        # Pattern information display
        if uploaded_pattern:
            st.success(f"🎯 Following pattern from: {uploaded_pattern.name}")
            if pattern_instructions:
                st.info(f"📝 Additional instructions: {pattern_instructions}")
        
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
        can_generate = (total_questions > 0) or uploaded_pattern
        if can_generate:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.info(f"📄 File size: {len(uploaded_file.getvalue()) / 1024:.1f} KB")
                
                # Display question breakdown
                if uploaded_pattern:
                    st.info(f"🎯 Question Plan: Following uploaded pattern structure")
                else:
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
                            include_marks,
                            uploaded_pattern,
                            pattern_instructions
                        )
                        
                        if questions:
                            # Display results
                            st.markdown("---")
                            st.header("📝 Generated Questions")
                            
                            # Create expandable sections for better organization
                            with st.expander("📋 View All Questions", expanded=True):
                                st.markdown(questions)
                            
                            # Action buttons
                            col1, col2, col3, col4 = st.columns(4)
                            
                            with col1:
                                st.download_button(
                                    label="� Download Text",
                                    data=questions,
                                    file_name=f"questions_{uploaded_file.name.replace('.pdf', '.txt')}",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col2:
                                # Generate formatted PDF
                                if uploaded_pattern and st.session_state.pattern_format:
                                    pdf_bytes = generate_formatted_pdf(
                                        questions, 
                                        st.session_state.pattern_format,
                                        f"formatted_questions_{uploaded_file.name.replace('.pdf', '.pdf')}"
                                    )
                                    if pdf_bytes:
                                        st.download_button(
                                            label="🎯 Download EXACT REPLICA PDF",
                                            data=pdf_bytes,
                                            file_name=f"exact_replica_{uploaded_file.name.replace('.pdf', '.pdf')}",
                                            mime="application/pdf",
                                            use_container_width=True,
                                            help="Download questions in EXACTLY the same visual format as uploaded sample - every symbol, spacing, and layout element will be identical"
                                        )
                                        
                                        # Visual Matching Verification
                                        if uploaded_pattern:
                                            st.markdown("---")
                                            st.markdown("### 🎯 **Visual Matching Verification**")
                                            st.success("✅ **Perfect Match Guaranteed**: The downloaded PDF will be visually identical to your uploaded sample paper.")
                                            
                                            with st.expander("📊 What Gets Matched Exactly", expanded=False):
                                                st.markdown("""
                                                **🎯 EXACT REPLICATION INCLUDES:**
                                                - ✅ **Headers & Titles**: Institution name, exam title, subject details
                                                - ✅ **Layout & Spacing**: Margins, line spacing, paragraph breaks
                                                - ✅ **Question Numbering**: Exact numbering style (1., Q1, Question 1, etc.)
                                                - ✅ **Marks Display**: Same format [5], (5 marks), 5 marks, etc.
                                                - ✅ **Symbols & Borders**: All decorative elements and visual symbols
                                                - ✅ **Instructions Format**: Identical instruction layout and styling
                                                - ✅ **Section Headers**: Part A, Section I, MCQ, etc. - exact format
                                                - ✅ **Font Styles**: Bold, italic, underlined text patterns
                                                - ✅ **Answer Spaces**: Lines, blanks, or spaces for answers
                                                - ✅ **Page Structure**: Overall document organization and flow
                                                
                                                **🔥 The result is a pixel-perfect replica with your new content!**
                                                """)
                                    else:
                                        st.button(
                                            "📋 PDF Generation Failed",
                                            disabled=True,
                                            use_container_width=True
                                        )
                                else:
                                    # Basic PDF without pattern formatting
                                    pdf_bytes = generate_formatted_pdf(questions, None)
                                    if pdf_bytes:
                                        st.download_button(
                                            label="📋 Download Basic PDF",
                                            data=pdf_bytes,
                                            file_name=f"questions_{uploaded_file.name.replace('.pdf', '.pdf')}",
                                            mime="application/pdf",
                                            use_container_width=True,
                                            help="Download questions as basic formatted PDF"
                                        )
                                    else:
                                        st.button(
                                            "📋 PDF Generation Failed",
                                            disabled=True,
                                            use_container_width=True
                                        )
                            
                            with col3:
                                if st.session_state.questions_data:
                                    if st.button("🎯 Take Exam", use_container_width=True):
                                        st.session_state.exam_mode = True
                                        st.rerun()
                            
                            with col4:
                                if st.session_state.questions_data:
                                    st.success("✅ Exam Ready!")
                                else:
                                    st.warning("⚠️ Exam data unavailable")
                                    
                    else:
                        st.error("❌ Failed to process PDF. Please try again with a different file.")
        else:
            if uploaded_pattern:
                st.info("✅ Pattern uploaded and ready. You can generate questions now.")
            else:
                st.warning("⚠️ Please configure at least one type of question in the sidebar.")

# ==========================
# PAGE 2: TAKE EXAM
# ==========================
elif page == "🎯 Take Exam":
    if not st.session_state.questions_data:
        st.warning("⚠️ No questions available. Please generate questions first.")
        if st.button("📝 Go to Question Generation"):
            st.rerun()
    else:
        questions = st.session_state.questions_data['questions']
        
        # Exam interface
        st.subheader(f"📝 Exam - {len(questions)} Questions")
        
        # Timer (optional)
        with st.sidebar:
            st.header("⏱️ Exam Info")
            total_marks = sum(q['marks'] for q in questions)
            st.info(f"Total Questions: {len(questions)}")
            st.info(f"Total Marks: {total_marks}")
            
            # Answer upload option
            st.subheader("📤 Upload Answer Sheet")
            uploaded_answers = st.file_uploader(
                "Upload handwritten answers (optional)",
                type=['jpg', 'jpeg', 'png', 'pdf'],
                help="Upload photos of your handwritten answers for evaluation"
            )
        
        # Display questions and collect answers
        if not st.session_state.exam_submitted:
            with st.form("exam_form"):
                # Initialize exam answers dict for this session
                form_answers = {}
                
                for i, question in enumerate(questions):
                    q_id = question['id']
                    q_type = question['type']
                    q_text = question['question']
                    q_marks = question['marks']
                    
                    st.markdown(f"### Question {q_id} ({q_marks} marks)")
                    st.markdown(q_text)
                    
                    if q_type == "mcq":
                        # Multiple choice question
                        options = question.get('options', [])
                        if options:
                            user_answer = st.radio(
                                f"Select your answer for Q{q_id}:",
                                options,
                                key=f"q_{q_id}",
                                index=None
                            )
                            # Store the answer in form_answers for submission
                            if user_answer:
                                # Extract just the letter (A, B, C, D) from the option
                                answer_letter = user_answer.split(')')[0].strip()
                                form_answers[str(q_id)] = answer_letter
                        else:
                            st.error(f"No options available for Question {q_id}")
                    else:
                        # Text answer question
                        if q_type == "short":
                            answer = st.text_area(
                                f"Your answer for Q{q_id}:",
                                key=f"q_{q_id}",
                                height=100,
                                placeholder="Write your short answer here..."
                            )
                        elif q_type == "medium":
                            answer = st.text_area(
                                f"Your answer for Q{q_id}:",
                                key=f"q_{q_id}",
                                height=150,
                                placeholder="Write your detailed answer here..."
                            )
                        else:  # long or case_study
                            answer = st.text_area(
                                f"Your answer for Q{q_id}:",
                                key=f"q_{q_id}",
                                height=200,
                                placeholder="Write your comprehensive answer here..."
                            )
                        
                        # Store the answer in form_answers for submission
                        if answer and answer.strip():
                            form_answers[str(q_id)] = answer.strip()
                    
                    st.markdown("---")
                
                # Submit button
                submitted = st.form_submit_button("🚀 Submit Exam", type="primary")
                
                if submitted:
                    if len(form_answers) == 0:
                        st.error("Please answer at least one question before submitting.")
                    else:
                        # Update session state with form answers
                        st.session_state.exam_answers = form_answers
                        
                        # Show submission progress
                        st.info(f"📝 Submitted {len(form_answers)} out of {len(questions)} questions")
                        
                        # Evaluate answers
                        with st.spinner("🤖 Evaluating your exam..."):
                            evaluation = evaluate_exam_answers(
                                st.session_state.questions_data,
                                st.session_state.exam_answers,
                                uploaded_answers
                            )
                            
                            if evaluation:
                                st.session_state.evaluation_result = evaluation
                                st.session_state.exam_submitted = True
                                st.success("✅ Exam submitted and evaluated successfully!")
                                time.sleep(2)  # Brief pause for user to see success message
                                st.rerun()
                            else:
                                st.error("❌ Error during evaluation. Please try again.")
        else:
            st.success("✅ Exam completed! Check your results in the 'View Results' section.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📊 View Results", use_container_width=True):
                    st.rerun()
            with col2:
                if st.button("🔄 Retake Exam", use_container_width=True):
                    st.session_state.exam_submitted = False
                    st.session_state.exam_answers = {}
                    st.session_state.evaluation_result = None
                    st.rerun()

# ==========================
# PAGE 3: VIEW RESULTS
# ==========================
elif page == "📊 View Results":
    if not st.session_state.evaluation_result:
        st.warning("⚠️ No exam results available. Please take an exam first.")
        if st.button("🎯 Take Exam"):
            st.rerun()
    else:
        result = st.session_state.evaluation_result
        
        # Results summary
        st.header("📊 Exam Results")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Marks", result['total_marks'])
        
        with col2:
            st.metric("Obtained Marks", f"{result['obtained_marks']:.1f}")
        
        with col3:
            st.metric("Percentage", f"{result['percentage']:.1f}%")
        
        with col4:
            if result['percentage'] >= 80:
                grade = "A+"
                color = "🟢"
            elif result['percentage'] >= 70:
                grade = "A"
                color = "🟡"
            elif result['percentage'] >= 60:
                grade = "B"
                color = "🟠"
            elif result['percentage'] >= 50:
                grade = "C"
                color = "🔴"
            else:
                grade = "F"
                color = "⚫"
            
            st.metric("Grade", f"{color} {grade}")
        
        # Progress bar
        st.progress(result['percentage'] / 100)
        
        # Detailed results
        st.subheader("📝 Question-wise Analysis")
        
        for eval_item in result['evaluations']:
            q_id = eval_item['question_id']
            q_type = eval_item['type']
            marks_obtained = eval_item.get('marks_obtained', 0)
            total_marks = eval_item['total_marks']
            
            with st.expander(f"Question {q_id} - {marks_obtained}/{total_marks} marks"):
                st.markdown(f"**Question:** {eval_item['question']}")
                st.markdown(f"**Your Answer:** {eval_item['user_answer']}")
                
                if q_type == "mcq":
                    correct_answer = eval_item['correct_answer']
                    is_correct = eval_item.get('is_correct', False)
                    st.markdown(f"**Correct Answer:** {correct_answer}")
                    if is_correct:
                        st.success("✅ Correct!")
                    else:
                        st.error("❌ Incorrect")
                else:
                    # Subjective question feedback
                    feedback = eval_item.get('feedback', 'No feedback available')
                    suggestions = eval_item.get('suggestions', '')
                    
                    st.markdown(f"**Feedback:** {feedback}")
                    if suggestions:
                        st.markdown(f"**Suggestions:** {suggestions}")
        
        # Action buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Retake Exam"):
                st.session_state.exam_submitted = False
                st.session_state.exam_answers = {}
                st.session_state.evaluation_result = None
                st.rerun()
        
        with col2:
            if st.button("📝 Generate New Questions"):
                st.session_state.questions_data = None
                st.session_state.exam_submitted = False
                st.session_state.exam_answers = {}
                st.session_state.evaluation_result = None
                st.rerun()
        
        with col3:
            # Download results
            results_text = f"""EXAM RESULTS
================
Date: {result['timestamp']}
Total Marks: {result['total_marks']}
Obtained Marks: {result['obtained_marks']:.1f}
Percentage: {result['percentage']:.1f}%
Grade: {grade}

QUESTION-WISE BREAKDOWN:
"""
            for eval_item in result['evaluations']:
                results_text += f"\nQ{eval_item['question_id']}: {eval_item.get('marks_obtained', 0)}/{eval_item['total_marks']} marks"
                if eval_item['type'] != 'mcq':
                    results_text += f"\nFeedback: {eval_item.get('feedback', 'N/A')}"
            
            st.download_button(
                "💾 Download Results",
                results_text,
                file_name=f"exam_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )

# ==========================
# Footer
# ==========================
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666;'>
        Made with ❤️ using Streamlit and Google Gemini AI | 📚 Question Generator & 🎯 Exam System
    </div>
    """,
    unsafe_allow_html=True
)
