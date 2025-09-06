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
        
        # Create comprehensive prompt for display questions
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
            # Generate display version
            display_response = model.generate_content([display_prompt] + images)
            
            # Generate structured version for exam
            exam_response = model.generate_content([exam_prompt] + images)
            
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
        
        return display_response.text
    except Exception as e:
        st.error(f"Error generating questions: {str(e)}")
        return None

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
                            
                            # Action buttons
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.download_button(
                                    label="💾 Download Questions",
                                    data=questions,
                                    file_name=f"questions_{uploaded_file.name.replace('.pdf', '.txt')}",
                                    mime="text/plain",
                                    use_container_width=True
                                )
                            
                            with col2:
                                if st.session_state.questions_data:
                                    if st.button("🎯 Take Exam", use_container_width=True):
                                        st.session_state.exam_mode = True
                                        st.rerun()
                            
                            with col3:
                                if st.session_state.questions_data:
                                    st.success("✅ Exam Ready!")
                                else:
                                    st.warning("⚠️ Exam data unavailable")
                                    
                    else:
                        st.error("❌ Failed to process PDF. Please try again with a different file.")
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
