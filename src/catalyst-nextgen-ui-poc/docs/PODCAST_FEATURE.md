# 🎙️ Podcast Generation Feature

## Overview
InK Studio now includes a powerful podcast generation feature that converts your Word documents into engaging audio podcasts using OpenAI's Text-to-Speech (TTS) API, integrated with LangChain and LangGraph workflows.

## How It Works

### Architecture

```
Word Document → LangChain/LangGraph Workflow → OpenAI Models → Audio Podcast
                ↓                              ↓
        1. Script Generation            2. Audio Generation
        (GPT-4o-mini)                  (TTS-1 API)
```

### Technology Stack

1. **LangChain & LangGraph**: Orchestrates the multi-step workflow
2. **OpenAI GPT-4o-mini**: Generates the podcast script
3. **OpenAI TTS-1 API**: Converts script to speech
4. **FastAPI Backend**: Serves audio files
5. **HTML5 Audio Player**: Plays podcasts in browser

### Workflow Steps

The "Generate Podcast" direction consists of two steps:

#### Step 1: Create Podcast Script
- **Tool**: `llm_prompt` (GPT-4o-mini)
- **Purpose**: Transform document into conversational podcast script
- **Features**:
  - Engaging introduction
  - Clear sections with smooth transitions
  - Storytelling style
  - Strong conclusion
  - Limited to 4000 characters (TTS API limit)

#### Step 2: Generate Audio
- **Tool**: `podcast_generator` (custom agentic tool)
- **Purpose**: Convert script to audio using OpenAI TTS
- **Features**:
  - High-quality audio generation
  - Multiple voice options (default: alloy)
  - MP3 format output
  - Auto-saved to `generated_audio/` directory

## Implementation Details

### New Agentic Tool: PodcastGeneratorTool

**File**: `agentic_tools.py`

```python
class PodcastGeneratorTool(AgenticTool):
    """Generate audio podcast from text using OpenAI TTS"""
    
    def execute(self, context, streaming_callback):
        # 1. Get podcast script from previous step
        # 2. Configure voice (alloy, echo, fable, onyx, nova, shimmer)
        # 3. Call OpenAI TTS API
        # 4. Save MP3 file
        # 5. Return file reference
```

**Key Features**:
- Streaming progress updates
- Timestamp-based filenames
- Character limit handling (4096 chars)
- Error handling and reporting

### API Endpoint

**File**: `app_fastapi.py`

```python
@app.get("/api/audio/{filename}")
async def serve_audio(filename: str):
    """Serve generated audio files securely"""
```

- Serves MP3 files from `generated_audio/` directory
- Security: prevents directory traversal attacks
- Content type: `audio/mpeg`

### Frontend Audio Player

**File**: `templates/index.html`

The UI automatically detects audio content and displays:
- 🎙️ Podcast player with controls
- Visual gradient background
- File information
- Download tip

**Rendering Logic**:
```javascript
// Detect AUDIO_FILE: prefix in output
if (text.startsWith('AUDIO_FILE:')) {
    return renderAudioPlayer(filename);
}
```

## Usage Instructions

### For Users

1. **Upload Document**
   - Click "Choose File" in Sources panel
   - Select your .docx file

2. **Select Direction**
   - Choose "Generate Podcast" from Direction dropdown

3. **Generate**
   - Click "✨ Draft" button
   - Watch as the system:
     - Creates podcast script (Step 1)
     - Generates audio (Step 2)

4. **Listen**
   - Click "Generate Audio" step in the workflow panel
   - Audio player appears in Canvas
   - Click play to listen!

5. **Download** (optional)
   - Right-click audio player
   - Select "Download" to save MP3

### Available Voice Options

You can customize the voice by editing the workflow in the Manager:

- **alloy** (default): Neutral, balanced
- **echo**: Clear, expressive
- **fable**: Warm, engaging
- **onyx**: Deep, authoritative
- **nova**: Friendly, energetic
- **shimmer**: Soft, calm

Edit `prompts.json` → `generate_podcast` → Step 2 → `parameters.voice`

## Technical Specifications

### Audio Format
- **Format**: MP3
- **Model**: OpenAI TTS-1
- **Quality**: Standard (16 kHz, 32 kbps)
- **Upgrade**: Can use TTS-1-HD for higher quality

### Limitations
- **Max Input**: 4096 characters per API call
- **Cost**: ~$0.015 per 1,000 characters (TTS-1)
- **Languages**: Supports multiple languages (same as GPT models)

### File Management
- **Storage**: `generated_audio/` directory
- **Naming**: `podcast_YYYYMMDD_HHMMSS.mp3`
- **Cleanup**: Manual (files persist until deleted)

## Customization Options

### 1. Change Voice
Edit `prompts.json`:
```json
"parameters": {
  "voice": "nova"  // Choose: alloy, echo, fable, onyx, nova, shimmer
}
```

### 2. Use HD Quality
Edit `agentic_tools.py` → `PodcastGeneratorTool`:
```python
model="tts-1-hd"  // Instead of "tts-1"
```

### 3. Extend Character Limit
For longer podcasts, split script into chunks:
```python
# In PodcastGeneratorTool.execute()
chunks = [script[i:i+4096] for i in range(0, len(script), 4096)]
# Generate and concatenate audio files
```

### 4. Custom Script Template
Edit the podcast script prompt in `prompts.json` to change the style:
- Formal vs casual tone
- Interview format
- News-style delivery
- Educational narration

## Troubleshooting

### Audio Not Playing
- Check browser console for errors
- Verify `/api/audio/{filename}` endpoint is accessible
- Ensure `generated_audio/` directory exists

### Generation Failed
- Check OpenAI API key is valid
- Verify internet connection
- Check script length (must be < 4096 chars)
- Review server logs for errors

### Poor Audio Quality
- Switch to `tts-1-hd` model
- Try different voices
- Improve script quality (better punctuation, formatting)

## Future Enhancements

Potential improvements:
1. **Multi-voice podcasts**: Different voices for different sections
2. **Background music**: Add intro/outro music
3. **Chapters**: Generate chapter markers
4. **Transcripts**: Include text transcript with audio
5. **Batch generation**: Process multiple documents
6. **Custom voices**: Fine-tune voices for brand consistency

## Cost Estimation

OpenAI TTS Pricing (as of 2024):
- **TTS-1**: $0.015 per 1,000 characters
- **TTS-1-HD**: $0.030 per 1,000 characters

**Examples**:
- 1-page document (~500 words = ~3,000 chars): ~$0.045
- 5-page document (~2,500 words = ~15,000 chars): ~$0.225
- 10-page document (~5,000 words = ~30,000 chars): ~$0.45

## Security Considerations

1. **File Access**: Audio endpoint prevents directory traversal
2. **API Keys**: Stored securely in environment/config
3. **File Cleanup**: Consider periodic cleanup of old audio files
4. **Rate Limiting**: Consider adding rate limits for production

## Summary

The podcast generation feature seamlessly integrates OpenAI's TTS capabilities into the InK Studio workflow system, providing users with a one-click solution to convert documents into professional audio podcasts. The implementation leverages LangChain/LangGraph for workflow orchestration, custom agentic tools for extensibility, and a polished UI for playback.

**Key Benefits**:
- ✅ Fully automated script generation and audio creation
- ✅ Professional-quality audio output
- ✅ In-browser playback with HTML5 audio
- ✅ Seamless integration with existing workflow system
- ✅ Customizable voices and styles
- ✅ Downloadable MP3 files

