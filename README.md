# PDF Question Generator & Exam System

# 📚 AI-Powered PDF Question Generator

A sophisticated Streamlit application that generates customizable questions from PDF documents using Google's Gemini AI, complete with an interactive exam system and AI-powered evaluation.

## 🌐 Live Demo
**Deploy your own:** [![Deploy to Streamlit Cloud](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io/)

📖 **[Deployment Guide](DEPLOYMENT.md)** - Step-by-step instructions for deploying to Streamlit Cloud

## 🌟 Features

### 📚 Question Generation
- Upload PDF documents (up to 200MB)
- 🤖 AI-powered question generation using Google Gemini
- 📝 **Multiple Question Types:**
  - Multiple Choice Questions (MCQs) - 1 mark each
  - Short Answer Questions - 2-3 marks each
  - Medium Answer Questions - 5 marks each
  - Long Answer Questions - 10+ marks each
  - Case Study/Application Questions - Variable marks
- 🎯 **EXACT VISUAL REPLICATION:**
  - Upload ANY sample question paper for pixel-perfect matching
  - AI creates visually IDENTICAL PDFs with your content
  - Preserves every formatting detail: fonts, spacing, symbols, borders
  - Maintains exact headers, numbering, marks display, instructions
  - Supports PDF, images (JPG, PNG), and text files
  - **Perfect Match Guarantee:** Downloaded PDF looks exactly like your sample

### 🎯 Interactive Exam System
- **Take Exams** on generated questions
- **Multiple Answer Formats:**
  - Type answers directly in the app
  - Upload handwritten answer sheets (photos/PDFs)
- **AI-Powered Evaluation:**
  - Automatic MCQ scoring
  - Intelligent evaluation of subjective answers
  - Detailed feedback and suggestions
  - Marks allocation with explanations

### 📊 Comprehensive Results
- **Detailed Performance Analysis:**
  - Total marks and percentage
  - Question-wise breakdown
  - Grade assignment (A+, A, B, C, F)
  - Progress visualization
- **Feedback System:**
  - Individual question feedback
  - Areas for improvement
  - Sample answer comparisons
- **Export Options:**
  - Download exam results
  - Performance reports

### 🎯 **UNIQUE FEATURE: EXACT VISUAL REPLICATION**
**🔥 World's First AI-Powered Pixel-Perfect Question Paper Replication!**

Upload any sample question paper and get your generated questions in **EXACTLY** the same visual format:
- ✅ **Perfect Headers**: Institution names, logos, titles, exam details
- ✅ **Exact Numbering**: 1., Q1, Question 1 - whatever format you use
- ✅ **Identical Spacing**: Line breaks, margins, indentation preserved
- ✅ **Same Symbols**: Borders, decorative elements, special characters
- ✅ **Matching Instructions**: Format, numbering, styling maintained
- ✅ **Original Layout**: Sections, parts, organization exactly replicated

**Result**: A professionally formatted PDF that looks like it came from your institution!

### ⚙️ Customization Options
- 🎯 **Quick Presets:**
  - Exam Paper (Mixed questions)
  - Practice Set (MCQ focused)
  - Assignment (Long answer focused)
  - Quiz (Short & MCQ)
  - Custom configuration
- **Advanced Settings:**
  - Difficulty level distribution
  - Question count for each type
  - Mark allocation display
  - Sample answers/hints option
- 🌍 **Multi-language Support:**
  - Maintain original document language
  - English only
  - Hindi only
  - Bilingual (English + Hindi)

### 💾 Export & Download
- Download generated questions as text files
- Download exam results and performance reports
- Save question sets for later use

## 🚀 How to Use

### 1. Generate Questions
1. Upload a PDF document
2. **Choose generation method:**
   - **Manual Configuration:** Set question types and counts manually
   - **Pattern Upload:** Upload a sample question paper/pattern for AI to follow
3. Configure difficulty and language settings
4. Click "Generate Questions"
5. **Download Options:**
   - **Basic PDF:** Standard formatted questions
   - **🎯 EXACT REPLICA PDF:** Visually identical to your uploaded sample paper (pixel-perfect matching)

**🎯 EXACT VISUAL REPLICATION Features:**
- Upload ANY sample question paper (PDF, images, text)
- AI creates pixel-perfect visual replicas
- Preserves every formatting detail: headers, spacing, symbols, borders
- Maintains exact numbering, marks display, instructions format
- Perfect match guarantee - downloaded PDF looks identical to your sample
- Perfect for recreating specific exam formats

### 2. Take Exam
1. After generating questions, navigate to "Take Exam"
2. Answer questions in the provided interface
3. For subjective questions, type your answers
4. Optionally upload handwritten answer sheets
5. Submit the exam for evaluation

### 3. View Results
1. Get instant AI-powered evaluation
2. Review detailed feedback for each question
3. Check your overall performance and grade
4. Download results or retake the exam

## 🎯 Use Cases

- **Students:** Practice with custom question sets from study materials
- **Teachers:** Create exams following specific institutional formats
- **Educational Institutions:** Generate questions matching their exam patterns
- **Researchers:** Create assessment tools from academic papers
- **Corporate Training:** Build assessments following company formats
- **Self-Learning:** Test comprehension with personalized question formats
- **Exam Preparation:** Practice with questions following real exam patterns

## How to Deploy to Streamlit Cloud

### Prerequisites
1. A Google Gemini API key (get it from [Google AI Studio](https://makersuite.google.com/app/apikey))
2. A GitHub account
3. A Streamlit Cloud account (free at [share.streamlit.io](https://share.streamlit.io))

### Step-by-Step Deployment

1. **Push code to GitHub:**
   - Create a new repository on GitHub
   - Push this code to your repository

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file path to: `app.py`

3. **Configure Secrets:**
   - In your Streamlit Cloud app settings, go to "Secrets"
   - Add your Gemini API key:
   ```toml
   GEMINI_API_KEY = "your_api_key_here"
   ```

4. **Deploy:**
   - Click "Deploy" and wait for the app to build
   - Your app will be live at: `https://[your-app-name].streamlit.app`

## Local Development

To run locally:

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Configuration

The app supports the following configurations:
- **Difficulty Level**: Easy, Medium, Hard, or Mixed
- **Number of Questions**: 5-50 questions
- **Language Instructions**: Customize how the AI handles language

## API Key Setup

Make sure to add your Gemini API key to Streamlit secrets:
1. Go to your app dashboard on Streamlit Cloud
2. Click on "Settings" → "Secrets"
3. Add: `GEMINI_API_KEY = "your_actual_api_key"`

## Security Note

Never commit your API key to version control. Always use Streamlit secrets or environment variables for sensitive information.
